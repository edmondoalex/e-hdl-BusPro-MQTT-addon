from pathlib import Path

from e_hdl_buspro_mqtt.app.esphome_manager import EspHomeCatalogStore


def test_esphome_catalog_sync_and_policy(tmp_path: Path):
    store = EspHomeCatalogStore(str(tmp_path / "esphome.json"))
    registry = [
        {"entity_id": "switch.pompa", "platform": "esphome", "original_name": "Pompa", "device_id": "node-1"},
        {"entity_id": "sensor.temperatura", "platform": "esphome", "original_name": "Temperatura", "device_id": "node-1"},
        {"entity_id": "light.altro", "platform": "mqtt", "original_name": "Altro"},
    ]
    states = [
        {"entity_id": "switch.pompa", "state": "on", "attributes": {"friendly_name": "Pompa"}},
        {"entity_id": "sensor.temperatura", "state": "21.4", "attributes": {"device_class": "temperature"}},
    ]
    synced = store.sync(registry, states)
    assert set(synced["entities"]) == {"switch.pompa", "sensor.temperatura"}
    assert synced["entities"]["switch.pompa"]["capabilities"] == ["on", "off"]
    assert synced["entities"]["sensor.temperatura"]["device_class"] == "temperature_sensor"
    assert not synced["entities"]["switch.pompa"]["enabled"]
    store.update("switch.pompa", enabled=True, read_only=False)
    rows = {row["device_id"]: row for row in store.rows({x["entity_id"]: x for x in states})}
    assert rows["switch.pompa"]["enabled"] is True
    assert rows["switch.pompa"]["read_only"] is False
    assert rows["switch.pompa"]["available"] is True


def test_esphome_catalog_preserves_policy_and_marks_removed(tmp_path: Path):
    store = EspHomeCatalogStore(str(tmp_path / "esphome.json"))
    registry = [{"entity_id": "switch.rele", "platform": "esphome", "original_name": "Relè"}]
    store.sync(registry, [])
    store.update("switch.rele", enabled=True, read_only=False)
    again = store.sync(registry, [])
    assert again["entities"]["switch.rele"]["enabled"] is True
    assert again["entities"]["switch.rele"]["read_only"] is False
    removed = store.sync([], [])
    assert removed["entities"]["switch.rele"]["orphaned"] is True
    assert removed["entities"]["switch.rele"]["enabled"] is False
    assert removed["entities"]["switch.rele"]["read_only"] is True
