from pathlib import Path

from e_hdl_buspro_mqtt.app.integration_overview import LABELS
from e_hdl_buspro_mqtt.app.mqtt_manager import MqttCatalog

APP = Path(__file__).resolve().parents[1] / 'e_hdl_buspro_mqtt/app'


def test_mqtt_branding_and_configuration_are_distinct_from_eface():
    mqtt = (APP/'static/hub/mqtt.js').read_text(encoding='utf-8')
    device = (APP/'static/hub/mqtt-device.js').read_text(encoding='utf-8')
    index = (APP/'static/index.html').read_text(encoding='utf-8')
    assert 'HASSIO' not in mqtt + device
    assert 'Programma in e-Control, applica in' not in index
    assert LABELS['mqtt'] == 'MQTT'
    assert 'mqtt-horizontal.svg' in index
    assert 'data-member-edit' in device
    assert 'data-device-mode' not in device
    assert 'data-member-enabled' not in device
    assert 'name="floor_id"' not in mqtt
    assert 'name="category"' not in mqtt
    composer = (APP/'static/hub/card-composer.js').read_text(encoding='utf-8')
    organization = (APP/'static/hub/organization.js').read_text(encoding='utf-8')
    assert 'Componi scheda multipla' in organization
    assert '#mqtt/entity/' not in organization
    assert 'Salva scheda multipla' in composer
    assert "const saved=await api(path)" in composer
    assert "api('user/snapshot')" in composer


def test_shared_physical_device_does_not_import_other_platforms(tmp_path):
    store = MqttCatalog(str(tmp_path/'mqtt.json'))
    registry = [
        {'id': platform, 'entity_id': 'sensor.'+platform, 'platform': platform,
         'device_id': 'same-physical-id'}
        for platform in ['mqtt', 'esphome', 'hue', 'template']
    ]
    store.sync_mqtt(registry, {})
    rows = store.rows({}, physical_id='same-physical-id')
    assert len(rows) == 1 and rows[0]['entity_id'] == 'sensor.mqtt'
    assert store.catalog({}) == []
