import tempfile
from pathlib import Path

from e_hdl_buspro_mqtt.app.ha_label_import import discover_labeled_entities
from e_hdl_buspro_mqtt.app.store import StateStore


def test_discovers_entity_and_inherited_device_labels():
    rows = discover_labeled_entities(
        label_name="HASSIO",
        labels=[{"label_id": "hassio", "name": "HASSIO"}],
        entities=[
            {"entity_id": "light.sala", "labels": ["hassio"], "original_name": "Sala"},
            {"entity_id": "binary_sensor.acqua", "device_id": "dev-1", "labels": []},
            {"entity_id": "switch.no", "labels": []},
        ],
        devices=[{"id": "dev-1", "labels": ["hassio"]}],
        states=[{"entity_id": "binary_sensor.acqua", "attributes": {"friendly_name": "Allagamento"}}],
    )
    assert [row["entity_id"] for row in rows] == ["light.sala", "binary_sensor.acqua"]
    assert rows[1]["name"] == "Allagamento"
    assert rows[1]["read_only"] is True
    assert rows[1]["eface_only"] is True


def test_sync_removes_from_active_catalog_and_restores_same_identity():
    with tempfile.TemporaryDirectory() as tmp:
        store = StateStore(str(Path(tmp) / "state.json"))
        first = store.sync_ha_labeled_devices(
            [{"entity_id": "lock.porta", "name": "Porta", "page": "locks", "read_only": False, "eface_only": False}],
            label="HASSIO",
        )
        assert first == {"found": 1, "added": 1, "updated": 0, "removed": 0, "restored": 0}
        second = store.sync_ha_labeled_devices(
            [{"entity_id": "lock.porta", "name": "Porta", "page": "locks", "read_only": False, "eface_only": False}],
            label="HASSIO",
        )
        assert second == {"found": 1, "added": 0, "updated": 1, "removed": 0, "restored": 0}
        assert len(store.list_ha_devices()) == 1
        original = store.list_ha_devices()[0]
        assert store.sync_ha_labeled_devices([], label="HASSIO")["removed"] == 1
        restarted = StateStore(str(Path(tmp) / "state.json"))
        assert restarted.list_ha_devices() == []
        assert restarted.archived_ha_label_entities() == {"lock.porta"}
        assert restarted.sync_ha_labeled_devices([], label="HASSIO")["removed"] == 0
        result = restarted.sync_ha_labeled_devices([{"entity_id":"lock.porta", "name":"Changed upstream"}], label="HASSIO")
        assert result["restored"] == 1
        assert restarted.list_ha_devices() == [original]
        assert restarted.archived_ha_label_entities() == set()


def test_manual_entities_never_become_label_owned(tmp_path):
    store = StateStore(str(tmp_path/'state.json'))
    manual = store.add_ha_device({'entity_id':'switch.manual', 'page':'extra', 'name':'Manual'})
    store.sync_ha_labeled_devices([{'entity_id':'switch.manual', 'page':'extra'}], label='HASSIO')
    store.sync_ha_labeled_devices([], label='HASSIO')
    assert store.list_ha_devices() == [manual]
    assert not store.archived_ha_label_entities()


def test_removed_label_restores_customization_and_permissions(tmp_path):
    store = StateStore(str(tmp_path/'state.json'))
    candidate = {'entity_id':'light.test', 'page':'lights', 'name':'Original'}
    store.sync_ha_labeled_devices([candidate], label='HASSIO')
    row = store.list_ha_devices()[0]
    edited = store.update_ha_device(device_id=row['id'], payload={**row, 'name':'Personalized', 'group':'Office', 'icon':'mdi:lamp'})
    store.update_ha_device_policy('light.test', enabled=False, read_only=True)
    expected = store.list_ha_devices()[0]
    store.sync_ha_labeled_devices([], label='HASSIO')
    store.sync_ha_labeled_devices([candidate], label='HASSIO')
    assert store.list_ha_devices() == [expected]


def test_label_on_device_still_selects_entity_after_direct_label_removed():
    args = dict(label_name='HASSIO', labels=[{'label_id':'tag', 'name':'HASSIO'}],
                entities=[{'entity_id':'sensor.test','device_id':'parent','labels':[]}], states=[])
    assert len(discover_labeled_entities(**args, devices=[{'id':'parent','labels':['tag']}])) == 1
    assert discover_labeled_entities(**args, devices=[{'id':'parent','labels':[]}]) == []


def test_label_configuration_defaults_and_persists():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "state.json")
        store = StateStore(path)
        assert store.get_ha_label_import() == {"enabled": True, "label": "HASSIO"}
        store.set_ha_label_import({"enabled": False, "label": "Casa"})
        assert StateStore(path).get_ha_label_import() == {"enabled": False, "label": "Casa"}


def test_editing_label_import_keeps_central_permissions():
    with tempfile.TemporaryDirectory() as tmp:
        store = StateStore(str(Path(tmp) / "state.json"))
        store.sync_ha_labeled_devices(
            [{"entity_id": "binary_sensor.acqua", "name": "Acqua", "page": "extra", "eface_only": True, "read_only": True}],
            label="HASSIO",
        )
        item = store.list_ha_devices()[0]
        updated = store.update_ha_device(device_id=item["id"], payload={**item, "name": "Allagamento"})
        assert updated["enabled"] is True
        assert updated["read_only"] is True
        assert updated["import_source"] == "ha_label"
