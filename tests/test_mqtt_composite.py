import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from e_hdl_buspro_mqtt.app.mqtt_manager import MqttCatalog, MqttManager, install_routes
from e_hdl_buspro_mqtt.app.smart_home import build_smart_home


def fixture(tmp_path):
    m = MqttManager(str(tmp_path/'mqtt.json'), '', lambda *a, **kw: {})
    m.devices = [{'id':'motion', 'name':'Motion cantina'}, {'id':'other','name':'Motion cantina'}]
    registry = [{'id':name, 'platform':'mqtt', 'entity_id':domain+'.'+name, 'device_id':physical,
                 'entity_category':category, 'name':name}
                for name, domain, physical, category in [('motion','binary_sensor','motion',None),
                ('battery','sensor','motion','diagnostic'),('interval','number','motion','config'),
                ('sensitivity','select','motion','config'),('indicator','switch','motion','config'),
                ('other','sensor','other',None)]]
    m.states = {r['entity_id']:{'state':'off', 'attributes':{}} for r in registry}
    m.states['number.interval'] = {'state':'30','attributes':{'min':1,'max':600,'step':1,'unit_of_measurement':'s'}}
    m.states['select.sensitivity'] = {'state':'medium','attributes':{'options':['low','medium','high']}}
    m.store.sync_mqtt(registry, m.states)
    m.last_sync = 1
    return m, registry


def selection(m):
    rows = m.device_detail('motion')['entities']
    return {'name':'Motion cantina','grouped':True,'primary_id':rows[0]['device_id'],
            'entities':{row['device_id']:{'enabled':True,'commands':row['domain']=='number'} for row in rows}}


def test_persistent_composite_keeps_entity_ids_and_registry_scope(tmp_path):
    m, registry = fixture(tmp_path)
    assert m.store.catalog(m.states) == []
    choice = selection(m)
    m.store.configure_device('motion', choice)
    rows = m.store.catalog(m.states)
    assert len(rows) == 5
    assert len({r['presentation_group']['id'] for r in rows}) == 1
    assert len({r['device_id'] for r in rows}) == 5
    assert all(r['read_only'] for r in rows if r['domain'] != 'number')
    restarted = MqttCatalog(m.store.path)
    registry[0]['entity_id'] = 'binary_sensor.renamed'
    registry[0]['name'] = 'Nuovo nome'
    restarted.sync_mqtt(registry, m.states)
    assert restarted.load()['presentations']['motion']['primary_id'] == choice['primary_id']
    assert restarted.catalog(m.states)[0]['presentation_group'] == rows[0]['presentation_group']
    assert restarted.catalog(m.states)[0]['device_id'] == rows[0]['device_id']
    assert not restarted.load()['devices'][restarted.rows(m.states, physical_id='other')[0]['device_id']]['enabled']
    payload = build_smart_home(hdl_devices=[],ksenia_snapshot={},states={},hdl_available=False,
                              organization={'devices':{}},additional_sources={'mqtt':rows})
    assert len(payload['devices']) == 5
    assert all(row['presentation_group']['primary_id'] == 'mqtt:'+choice['primary_id'] for row in payload['devices'])
    number = next(row for row in payload['devices'] if row['native_type']=='number')
    assert number['commands'][0]['maximum'] == 600


def test_selection_is_atomic_stale_registry_and_cross_device_rejected(tmp_path):
    m, _ = fixture(tmp_path)
    before = m.store.load()
    choice = selection(m)
    choice['entities'][m.store.rows(m.states,physical_id='other')[0]['device_id']] = {'enabled':True,'commands':False}
    with pytest.raises(ValueError): m.store.configure_device('motion', choice)
    assert m.store.load() == before
    choice = selection(m);choice['primary_id']='wrong'
    with pytest.raises(ValueError): m.store.configure_device('motion',choice)
    assert m.store.load() == before
    choice = selection(m)
    for value in choice['entities'].values():value.update(enabled=False,commands=True)
    m.store.configure_device('motion',choice)
    assert m.store.catalog(m.states)==[]
    assert all(row['read_only'] for row in m.store.rows(m.states))


@pytest.mark.parametrize('entity,action,value,service',[
    ('number.interval','level',40,'number/set_value'),('select.sensitivity','mode','high','select/select_option'),
    ('switch.indicator','on',None,'switch/turn_on')])
def test_admin_commands_do_not_require_eface_exposure(tmp_path,entity,action,value,service):
    m,_=fixture(tmp_path)
    row=next(row for row in m.store.rows(m.states) if row['entity_id']==entity)
    m.rest=AsyncMock(side_effect=[m.states[entity],{}])
    result=asyncio.run(m.command_entity(row['device_id'],{'action':action,'value':value},administrative=True))
    assert result['accepted'] and not result['confirmed']
    assert m.rest.call_args.args[1]=='/api/services/'+service
    assert m.rest.call_args.args[2]['entity_id']==entity
    assert not m.store.catalog(m.states)
    with pytest.raises(ValueError):asyncio.run(m.command_entity(row['device_id'],{'action':action,'value':value}))


@pytest.mark.parametrize('entity,action,value',[
    ('number.interval','level',0),('number.interval','level',601),('number.interval','level',1.5),
    ('number.interval','level',float('nan')),('number.interval','level',True),
    ('select.sensitivity','mode','invented'),('binary_sensor.motion','on',None)])
def test_admin_commands_reject_invalid_values(tmp_path,entity,action,value):
    m,_=fixture(tmp_path);m.rest=AsyncMock(return_value=m.states[entity])
    key=next(row['device_id'] for row in m.store.rows(m.states) if row['entity_id']==entity)
    with pytest.raises(ValueError):asyncio.run(m.command_entity(key,{'action':action,'value':value},administrative=True))
    assert all(call.args[0]=='GET' for call in m.rest.call_args_list)


def test_admin_routes_preserve_sections_and_callback_policies(tmp_path):
    m,_=fixture(tmp_path); saved=[]
    app=FastAPI();install_routes(app,m,lambda:None,lambda:[],saved.append)
    client=TestClient(app)
    response=client.get('/api/integrations/mqtt/devices/motion')
    assert response.status_code==200
    assert {r['entity_category'] for r in response.json()['entities']}=={None,'config','diagnostic'}
    choice=selection(m)
    response=client.put('/api/integrations/mqtt/devices/motion/presentation',json=choice)
    assert response.status_code==200
    assert saved==[choice['entities']]
    assert client.get('/api/integrations/mqtt/devices/fake').status_code==404


def test_member_order_persists_after_restart_and_failed_save_is_atomic(tmp_path):
    m, _ = fixture(tmp_path)
    choice = selection(m)
    choice['member_order'] = list(reversed(choice['entities']))
    m.store.configure_device('motion', choice)
    restarted = MqttCatalog(m.store.path)
    assert restarted.load()['presentations']['motion']['member_order'] == choice['member_order']
    rows = restarted.catalog(m.states)
    assert all(r['presentation_group']['member_ids'] == ['mqtt:'+key for key in choice['member_order']] for r in rows)
    before = restarted.load()
    for wrong in [[], ['foreign'], [choice['primary_id']]*5, [None], 'bad']:
        choice['member_order'] = wrong
        with pytest.raises(ValueError): restarted.configure_device('motion', choice)
        assert restarted.load() == before


def test_real_hub_group_policy_reaches_snapshot_and_backup(tmp_path,monkeypatch):
    from e_hdl_buspro_mqtt.app.main import create_app
    monkeypatch.setenv('BUSPRO_STATE',str(tmp_path/'state.json'))
    monkeypatch.setenv('ECONTROL_ORGANIZATION',str(tmp_path/'organization.json'))
    app=create_app();m=app.state.mqtt_manager
    prepared,registry=fixture(tmp_path)
    m.devices=prepared.devices;m.states=prepared.states;m.last_sync=1
    m.store.sync_mqtt(registry,m.states)
    client=TestClient(app,base_url='http://testserver:8125')
    client.get('/api/organization')
    choice=selection(m)
    assert client.put('/api/integrations/mqtt/devices/motion/presentation',json=choice).status_code==200
    rows=client.get('/api/user/snapshot').json()['smart_home']['devices']
    mqtt=[row for row in rows if row['source']=='mqtt']
    assert len(mqtt)==5 and all(row.get('presentation_group') for row in mqtt)
    import json
    backup=json.loads(client.get('/api/backup').json()['text'])
    assert backup['_econtrol_mqtt']['presentations']['motion']['grouped']
    for value in choice['entities'].values():value['enabled']=False
    assert client.put('/api/integrations/mqtt/devices/motion/presentation',json=choice).status_code==200
    assert not [row for row in client.get('/api/user/snapshot').json()['smart_home']['devices'] if row['source']=='mqtt']
    number_row=next(row for row in m.store.rows(m.states) if row['entity_id']=='number.interval')
    m.rest=AsyncMock(side_effect=[m.states['number.interval'],{}])
    result=client.post('/api/integrations/mqtt/entities/'+number_row['device_id']+'/command',json={'action':'level','value':40})
    assert result.status_code==200 and result.json()['audit_id']
    assert result.json()['accepted'] and not result.json()['confirmed']
    user=TestClient(app,base_url='http://testserver:8124')
    assert user.post('/api/integrations/mqtt/entities/fake/command',json={'action':'on'}).status_code==404
