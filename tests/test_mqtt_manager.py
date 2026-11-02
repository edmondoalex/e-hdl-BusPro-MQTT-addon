import asyncio
from collections import deque
from contextlib import asynccontextmanager
import json
import time
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from e_hdl_buspro_mqtt.app.mqtt_manager import MqttCatalog, MqttManager, install_routes, topic, qos


def registry(eid='switch.example', **extra):
    return [{'entity_id': eid, 'id': 'stable-registry-id', 'platform': 'mqtt', 'name': 'Example', 'device_id': 'ha-device', **extra}]


def test_default_off_persistent_rename_and_no_repeated_writes(tmp_path):
    path=tmp_path/'mqtt.json'; store=MqttCatalog(str(path))
    states={'switch.example': {'state':'off', 'attributes':{}}}
    store.sync_mqtt(registry(), states)
    key=next(iter(store.load()['devices']))
    assert store.catalog(states)==[]
    assert store.rows(states)[0]['read_only'] is True
    before=path.stat().st_mtime_ns
    store.sync_mqtt(registry(), states)
    assert path.stat().st_mtime_ns==before
    store.update(key, enabled=True, read_only=False)
    again=MqttCatalog(str(path));again.sync_mqtt(registry('switch.renamed'), {})
    row=again.rows({})[0]
    assert row['device_id']==key and row['enabled'] and not row['read_only']
    assert not row['available']
    again.sync_mqtt([], {})
    assert again.rows({})[0]['orphaned']


def test_disabled_and_other_integrations(tmp_path):
    store=MqttCatalog(str(tmp_path/'mqtt.json'))
    store.sync_mqtt(registry(disabled_by='user')+[{'platform':'esphome','entity_id':'switch.other'}], {'switch.example':{'state':'on'}})
    assert len(store.rows({}))==1 and not store.rows({'switch.example':{'state':'on'}})[0]['available']


def test_commands_follow_bus_policy_and_hidden_orphans_stay_hidden(tmp_path):
    from e_hdl_buspro_mqtt.app.smart_home import build_smart_home
    store=MqttCatalog(str(tmp_path/'mqtt.json'));store.sync_mqtt(registry(),{})
    key=store.rows({})[0]['device_id']
    assert store.update(key,read_only=False)['read_only']
    assert not store.update(key,enabled=True,read_only=False)['read_only']
    assert store.update(key,enabled=False)['read_only']
    data=build_smart_home(hdl_devices=[],ksenia_snapshot={},states={},hdl_available=False,
        organization={'devices':{'mqtt:'+key:{'orphaned':True,'eface':False}}})
    assert not data['devices']
    store.sync_mqtt(registry('sensor.example'),{})
    assert store.update(key,enabled=True,read_only=False)['read_only']


@pytest.mark.parametrize('value', ['', 'bad/#/suffix', 'bad+level', '\x00', 'a'*1025])
def test_invalid_subscription(value):
    with pytest.raises(ValueError):topic(value, subscribe=True)


@pytest.mark.parametrize('value', ['nuki/#','+/state','#','a/+/state'])
def test_valid_subscription(value):
    assert topic(value, subscribe=True)==value


def test_publish_wildcards_and_qos():
    with pytest.raises(ValueError):topic('nuki/#')
    for value in (True, -1, 3, '1'):
        with pytest.raises(ValueError):qos(value)


def manager(tmp_path):
    result=MqttManager(str(tmp_path/'mqtt.json'), 'not-a-real-token', lambda *a, **kw: {})
    result.ws.command=AsyncMock(return_value={})
    result.rest=AsyncMock(return_value={})
    return result


def test_publish_confirm_template_and_actual_ha_service(tmp_path):
    async def check():
        m=manager(tmp_path)
        with pytest.raises(ValueError):await m.publish({'topic':'example/config','payload':'','retain':True})
        m.ws.command.assert_not_called()
        await m.publish({'topic':'example/config','payload':'','retain':True,'confirm_delete':True})
        assert m.ws.command.call_args.kwargs['service_data']['retain']
        m.render_template=AsyncMock(return_value='OFF')
        await m.publish({'topic':'example/command','payload':'{{ value }}','template':True})
        assert m.ws.command.call_args.kwargs['service_data']['payload']=='OFF'
        assert m.ws.command.call_args.kwargs['domain']=='mqtt'
    asyncio.run(check())


def test_flow_scope_secrets_nested_and_cancel(tmp_path):
    async def check():
        m=manager(tmp_path);m.entries=[{'entry_id':'mqtt-entry'}]
        m.rest.return_value={'type':'form','flow_id':'flow-a','data_schema':[
            {'name':'password','default':'SECRET'},
            {'name':'other_settings','schema':[{'name':'client_key_password','description':{'suggested_value':'NESTED'}}]}]}
        response=await m.start_flow('connection','mqtt-entry')
        assert 'SECRET' not in json.dumps(response) and 'NESTED' not in json.dumps(response)
        with pytest.raises(ValueError):await m.step_flow('foreign-flow',{})
        with pytest.raises(ValueError):await m.start_flow('options','foreign-entry')
        with pytest.raises(ValueError):await m.step_flow('flow-a',{'next_step_id':'addon'})
        await m.step_flow('flow-a',{'password':'','other_settings':{'client_key_password':''}})
        submitted=m.rest.call_args.args[2]
        assert submitted['password']=='SECRET' and submitted['other_settings']['client_key_password']=='NESTED'
        await m.cancel_flow('flow-a')
        assert not m.flows
    asyncio.run(check())


def test_completion_does_not_return_secrets_and_verification_failure_is_explicit(tmp_path):
    async def check():
        m=manager(tmp_path);m.flows['f']={'group':'options/','time':time.monotonic(),'secrets':{}}
        m.rest.return_value={'type':'create_entry','data':{'password':'SECRET'},'result':{'token':'SECRET'}}
        m.sync=AsyncMock(side_effect=OSError())
        result=await m.step_flow('f',{})
        assert result['applied'] and result['verification_pending']
        assert 'SECRET' not in json.dumps(result) and not m.flows
    asyncio.run(check())


def test_subentry_checks_membership(tmp_path):
    async def check():
        m=manager(tmp_path);m.entries=[{'entry_id':'mqtt-entry','subentries':[{'subentry_id':'owned'}]}]
        with pytest.raises(ValueError):await m.start_flow('device','mqtt-entry','foreign')
        m.rest.return_value={'type':'form','flow_id':'f'}
        await m.start_flow('device','mqtt-entry','owned')
        assert m.rest.call_args.args[2]=={'handler':['mqtt-entry','device'],'subentry_id':'owned'}
    asyncio.run(check())


def test_upload_requires_a_real_file_selector(tmp_path):
    async def check():
        m=manager(tmp_path);m.flows['f']={'time':time.monotonic(),'file_fields':{'other_settings.client_cert'},'uploads':[]}
        with pytest.raises(ValueError):await m.upload('f',{'field':'arbitrary','content':'QQ=='})
        with pytest.raises(ValueError):await m.upload('foreign',{'field':'other_settings.client_cert','content':'QQ=='})
    asyncio.run(check())


def test_listening_is_bounded_and_cancellation_unsubscribes(tmp_path):
    async def check():
        m=manager(tmp_path)
        class Socket:
            def __init__(self):self.n=0;self.closed=False
            async def send(self, message):self.sent=json.loads(message)
            async def recv(self):
                self.n+=1
                if self.n==1:return json.dumps({'type':'result','success':True})
                if self.n>252:await asyncio.sleep(60)
                return json.dumps({'type':'event','event':{'topic':'example/state','payload':'x'*5000,'qos':0,'retain':False}})
        sock=Socket()
        @asynccontextmanager
        async def socket():
            try:yield sock
            finally:sock.closed=True
        m.socket=socket
        key=(await m.listen({'topic':'example/#','qos':1}))['id']
        for _ in range(1000):
            if m.listeners[key]['sequence']>=251:break
            await asyncio.sleep(.001)
        result=m.messages(key)
        assert len(result['messages'])==200 and result['dropped']==51
        assert result['messages'][0]['truncated'] and len(result['messages'][0]['payload'])==4096
        assert sock.sent['type']=='mqtt/subscribe'
        await m.stop_listener(key)
        assert sock.closed and key not in m.listeners
        assert list(tmp_path.iterdir())==[]
    asyncio.run(check())


def test_updates_are_only_real_mqtt_update_entities_and_no_broker(tmp_path):
    async def check():
        m=manager(tmp_path)
        m.states={'update.example':{'state':'on','attributes':{'supported_features':9,'installed_version':'1','latest_version':'2'}}}
        m.store.sync_mqtt(registry('update.example'),m.states)
        key=m.store.rows(m.states)[0]['device_id']
        m.rest.return_value={'version':'2026.9.3'}
        result=await m.updates()
        assert result['items'][0]['can_install'] and result['items'][0]['can_backup']
        m.rest.return_value=m.states['update.example']
        with pytest.raises(ValueError):await m.install_update(key,{})
        await m.install_update(key,{'confirm':True,'backup':True})
        assert m.ws.command.call_args.kwargs=={'domain':'update','service':'install','service_data':{'entity_id':'update.example','backup':True}}
    asyncio.run(check())


def test_api_warnings_do_not_block_and_csrf(tmp_path):
    m=manager(tmp_path);m.store.sync_mqtt(registry(),{});m.last_sync=time.time()
    app=FastAPI();install_routes(app,m,lambda:None,lambda:[{'source':'ha','home_assistant_entity_id':'switch.example'}])
    client=TestClient(app)
    result=client.get('/api/integrations/mqtt')
    assert result.json()['entities'][0]['also_in']==['ha']
    assert not result.json()['entities'][0]['enabled']
    assert result.headers['cache-control']=='no-store'
    assert client.post('/api/integrations/mqtt/publish',json={},headers={'Origin':'https://foreign.test'}).status_code==403
    assert client.post('/api/integrations/mqtt/publish',content='{}',headers={'Content-Type':'text/plain'}).status_code==415
    assert client.post('/api/integrations/mqtt/publish',json={'payload':'x'*200001}).status_code==413
    m.ws.command.assert_not_called()


def test_user_port_and_bus_policy_integration(tmp_path, monkeypatch):
    from e_hdl_buspro_mqtt.app.main import create_app
    monkeypatch.setenv('BUSPRO_STATE',str(tmp_path/'state.json'))
    monkeypatch.setenv('ECONTROL_ORGANIZATION',str(tmp_path/'organization.json'))
    app=create_app();m=app.state.mqtt_manager;m.store.sync_mqtt(registry(),{})
    key=m.store.rows({})[0]['device_id']
    user=TestClient(app,base_url='http://testserver:8124')
    assert user.get('/api/integrations/mqtt').status_code==404
    assert user.post('/api/integrations/mqtt/publish',json={'topic':'x'}).status_code==404
    admin=TestClient(app,base_url='http://testserver:8125')
    org=admin.get('/api/organization').json()
    assert not org['devices']['mqtt:'+key]['eface']
    assert app.state.smart_home_sources['mqtt']()==[]
    result=admin.put('/api/integrations/mqtt/devices/'+key+'/policy',json={'eface':True,'commands':False})
    assert result.status_code==200
    assert app.state.smart_home_sources['mqtt']()[0]['read_only']
    backup=json.loads(admin.get('/api/backup').json()['text'])
    assert backup['_econtrol_mqtt']['devices'][key]['enabled']


def test_full_registry_does_not_revalidate_unchanged_organization(tmp_path, monkeypatch):
    from unittest.mock import patch
    from e_hdl_buspro_mqtt.app.main import create_app
    monkeypatch.setenv('BUSPRO_STATE',str(tmp_path/'state.json'))
    monkeypatch.setenv('ECONTROL_ORGANIZATION',str(tmp_path/'organization.json'))
    app=create_app();m=app.state.mqtt_manager;org=app.state.organization
    entries=[{'platform':'mqtt','id':str(i),'entity_id':f'sensor.test_{i}'} for i in range(2000)]
    m.store.sync_mqtt(entries,{})
    client=TestClient(app,base_url='http://testserver:8125')
    client.get('/api/organization')
    with patch.object(org,'validate',wraps=org.validate) as validate:
        client.get('/api/organization');client.get('/api/organization')
        assert validate.call_count==0
    key=m.store.rows({})[0]['device_id']
    org.assign({'source':'mqtt','device_id':key,'name_override':'Changed'})
    assert client.get('/api/organization').json()['devices']['mqtt:'+key]['name_override']=='Changed'
    m.store.sync_mqtt(entries+[{'platform':'mqtt','id':'new','entity_id':'sensor.new'}],{})
    data=client.get('/api/organization').json()
    assert len([k for k in data['devices'] if k.startswith('mqtt:')])==2001
