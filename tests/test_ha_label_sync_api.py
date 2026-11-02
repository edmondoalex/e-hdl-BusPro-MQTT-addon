import json
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def harness(tmp_path, monkeypatch):
    import e_hdl_buspro_mqtt.app.main as module
    monkeypatch.setenv('BUSPRO_STATE', str(tmp_path/'state.json'))
    monkeypatch.setenv('ECONTROL_ORGANIZATION', str(tmp_path/'organization.json'))
    monkeypatch.setenv('SUPERVISOR_TOKEN', 'synthetic-test-only')
    registry = {'config/label_registry/list':[{'label_id':'test','name':'HASSIO'}],
                'config/entity_registry/list':[{'entity_id':'sensor.imported','labels':['test']}],
                'config/device_registry/list':[]}
    async def command(name): return registry[name]
    ws = MagicMock();ws.command = AsyncMock(side_effect=command)
    monkeypatch.setattr(module, 'HomeAssistantWebSocket', lambda token:ws)
    response = MagicMock();response.__enter__.return_value.read.return_value = b'[]'
    monkeypatch.setattr(module.urllib.request, 'urlopen', lambda *args, **kwargs: response)
    app=module.create_app()
    return app, TestClient(app, base_url='http://testserver:8125'), registry


def test_removal_and_restore_reach_organization_snapshot_and_backup(harness):
    app, client, registry = harness
    store=app.state.store
    store.add_ha_device({'entity_id':'switch.manual','page':'extra'})
    mqtt=app.state.mqtt_manager
    mqtt.store.sync_mqtt([{'id':'separate','platform':'mqtt','entity_id':'sensor.imported'}], {})
    mqtt_key=mqtt.store.rows({})[0]['device_id']
    assert client.put('/api/integrations/mqtt/devices/'+mqtt_key+'/policy',
                      json={'eface':True,'commands':False}).status_code == 200
    before_mqtt=mqtt.store.load()
    assert client.post('/api/ha_devices/label-import/sync').status_code == 200
    imported=next(row for row in store.list_ha_devices() if row['entity_id']=='sensor.imported')
    client.put('/api/organization/device', json={'source':'ha','device_id':'sensor.imported','name_override':'Custom name','categories':['sensors']})
    registry['config/entity_registry/list'][0]['labels']=[]
    result=client.post('/api/ha_devices/label-import/sync')
    assert result.status_code==200 and result.json()['removed']==1
    assert [r['entity_id'] for r in result.json()['items']]==['switch.manual']
    assert 'ha:sensor.imported' not in client.get('/api/organization').json()['devices']
    devices=client.get('/api/user/snapshot').json()['smart_home']['devices']
    assert 'ha:sensor.imported' not in {d['id'] for d in devices}
    assert 'mqtt:'+mqtt_key in {d['id'] for d in devices}
    assert mqtt.store.load()==before_mqtt
    backup=json.loads(client.get('/api/backup').json()['text'])
    assert backup['ui']['ha_label_archive']['sensor.imported']['id']==imported['id']
    registry['config/entity_registry/list'][0]['labels']=['test']
    assert client.post('/api/ha_devices/label-import/sync').json()['restored']==1
    assert next(r for r in store.list_ha_devices() if r['entity_id']=='sensor.imported')['id']==imported['id']
    assert client.get('/api/organization').json()['devices']['ha:sensor.imported']['name_override']=='Custom name'


@pytest.mark.parametrize('bad', [None, {}, [None], [{}], [{'entity_id':None}]])
def test_malformed_registry_never_removes_devices(harness,bad):
    app, client, registry=harness
    assert client.post('/api/ha_devices/label-import/sync').status_code==200
    before=app.state.store.read_raw()
    registry['config/entity_registry/list']=bad
    assert client.post('/api/ha_devices/label-import/sync').status_code==502
    assert app.state.store.read_raw()==before


def test_registry_exception_and_disabled_sync_preserve_catalog(harness):
    app, client, registry=harness
    client.post('/api/ha_devices/label-import/sync')
    before=app.state.store.list_ha_devices()
    del registry['config/entity_registry/list']
    assert client.post('/api/ha_devices/label-import/sync').status_code==502
    assert app.state.store.list_ha_devices()==before
    client.put('/api/ha_devices/label-import/config',json={'enabled':False,'label':'HASSIO'})
    assert client.post('/api/ha_devices/label-import/sync').status_code==200
    assert app.state.store.list_ha_devices()==before
