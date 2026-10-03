from types import SimpleNamespace

import pytest

from e_hdl_buspro_mqtt.app.nuki_manager import NukiManager, NukiStore, canonical_device_id


class FakeMqtt:
    def __init__(self):
        self.published = []
        self.subscriptions = []
        self.handler = None

    def set_message_handler(self, handler): self.handler = handler
    def subscribe(self, topic, *, qos=0): self.subscriptions.append((topic, qos))
    def unsubscribe(self, topic): self.subscriptions = [item for item in self.subscriptions if item[0] != topic]
    def connect(self): pass
    def disconnect(self): pass
    def publish(self, topic, payload, *, qos=0, retain=False): self.published.append((topic, payload, qos))
    def status(self): return SimpleNamespace(connected=True, last_error=None)


def test_persistence_and_secret_is_separate(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    store.configure({"enabled": True, "mqtt_prefix": "doors", "cloud_enabled": True, "api_token": "secret"})
    assert store.load()["config"] == {"enabled": True, "mqtt_prefix": "doors", "cloud_enabled": True, "bridge_enabled": False, "bridge_host": "", "bridge_port": 8080}
    assert store.token() == "secret"
    assert "secret" not in (tmp_path / "nuki.json").read_text(encoding="utf-8")


def test_web_api_id_is_normalized_to_same_mqtt_device():
    assert canonical_device_id("18211616620") == "3D7F376C"
    assert canonical_device_id("22767029231") == "4D054BEF"
    assert canonical_device_id("4ca6faf4") == "4CA6FAF4"


def test_cloud_only_records_are_not_operational_devices(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["devices"]["21181354"] = {"device_id": "21181354", "name": "Vecchia Nuki", "web": True, "state": {}, "enabled": False, "read_only": True}
    store.save(data)
    assert store.rows() == []
    assert len(store.rows(include_cloud_only=True)) == 1


def test_discovery_event_identity_and_command(tmp_path):
    mqtt = FakeMqtt()
    manager = NukiManager(str(tmp_path / "nuki.json"), mqtt)
    manager.store.configure({"enabled": True})
    manager.store.ingest("nuki/123/state", "locked")
    manager.store.ingest("nuki/123/name", "Porta principale")
    data = manager.store.load()
    data["authorizations"]["42"] = {"auth_id": "42", "name": "Mario"}
    manager.store.save(data)
    manager.store.ingest("nuki/123/lockActionEvent", "1,4,42,7,0")
    snapshot = manager.snapshot()
    assert snapshot["devices"][0]["name"] == "Porta principale"
    assert snapshot["devices"][0]["state"]["state"] == "locked"
    assert snapshot["events"][0]["person"] == "Mario"
    assert snapshot["events"][0]["code_id"] == "7"
    assert snapshot["events"][0]["device_name"] == "Porta principale"
    assert snapshot["events"][0]["origin"] == "Tastierino"
    with pytest.raises(ValueError): manager.command("123", "unlock")
    manager.store.update_device("123", {"read_only": False, "enabled": True})
    assert manager.command("123", "unlock")["accepted"] is True
    assert mqtt.published == [("nuki/123/unlock", "true", 1)]


def test_access_events_normalize_cloud_ids_and_mqtt_origin(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "name": "Portoncino Scala", "state": {"state": "1"}}
    data["authorizations"]["46623"] = {"auth_id": "46623", "name": "Mario"}
    data["events"] = [{"id": "one", "device_id": "22767029231", "action_name": "Sblocco", "trigger": 172, "trigger_name": "Origine 172", "auth_id": 46623, "code_id": 0}]
    store.save(data)
    event = store.access_events()[0]
    assert event["device_id"] == "4D054BEF"
    assert event["device_name"] == "Portoncino Scala"
    assert event["person"] == "Mario"
    assert event["origin"] == "MQTT"
    assert event["code_id"] == ""


def test_start_subscribes_without_home_assistant(tmp_path):
    mqtt = FakeMqtt()
    manager = NukiManager(str(tmp_path / "nuki.json"), mqtt)
    manager.store.configure({"enabled": True})
    manager.start()
    assert mqtt.subscriptions == [("nuki/#", 1)]
    assert callable(mqtt.handler)


def test_disabled_integration_does_not_listen_and_reset_is_empty(tmp_path):
    mqtt = FakeMqtt()
    manager = NukiManager(str(tmp_path / "nuki.json"), mqtt)
    manager.start()
    assert mqtt.subscriptions == []
    manager.configure({"enabled": True, "api_token": "secret"})
    manager.store.ingest("nuki/123/state", "locked")
    snapshot = manager.reset()
    assert snapshot["config"]["enabled"] is False
    assert snapshot["devices"] == []
    assert snapshot["status"]["token_configured"] is False


def test_bridge_secret_sync_and_local_command(tmp_path):
    mqtt = FakeMqtt()
    manager = NukiManager(str(tmp_path / "nuki.json"), mqtt)
    manager.store.configure({"bridge_enabled": True, "bridge_host": "192.168.1.50", "bridge_token": "local-secret"})
    assert manager.store.bridge_token() == "local-secret"
    assert "local-secret" not in (tmp_path / "nuki.json").read_text(encoding="utf-8")
    calls = []

    def bridge(path, params=None, authenticated=True, **kwargs):
        calls.append((path, params, authenticated))
        if path == "/list":
            return [
                {"nukiId": 555225940, "deviceType": 0, "name": "Porta Ufficio", "lastKnownState": {"state": 1, "batteryCritical": False, "batteryChargeState": 28}},
                {"nukiId": 941005117, "deviceType": 0, "name": "Porta non raggiungibile"},
            ]
        return {"success": True}

    manager._bridge = bridge
    assert manager.sync_bridge()["devices"] == 2
    rows = {row["device_id"]: row for row in manager.snapshot()["devices"]}
    row = rows["21181354"]
    assert row["device_id"] == "21181354"
    assert row["name"] == "Porta Ufficio"
    assert row["available"] is True
    assert row["state"]["attributes"]["batteryChargeState"] == "28"
    assert rows["3816993D"]["available"] is False
    assert [item["device_id"] for item in manager.store.organization_catalog()] == ["21181354"]
    manager.store.update_device("21181354", {"read_only": False})
    result = manager.command("21181354", "unlock")
    assert result["source"] == "nuki_bridge"
    assert calls[-1][0] == "/lockAction"
    assert calls[-1][1] == {"nukiId": 555225940, "deviceType": 0, "action": 1}
    assert mqtt.published == []


def test_bridge_pairing_persists_token_and_imports_devices(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())

    def bridge(path, params=None, authenticated=True, **kwargs):
        if path == "/auth": return {"token": "paired-token"}
        if path == "/list": return []
        raise AssertionError(path)

    manager._bridge = bridge
    assert manager.pair_bridge("192.168.1.50", 8080) == {"devices": 0}
    assert manager.store.bridge_token() == "paired-token"
    assert manager.store.load()["config"]["bridge_enabled"] is True
    manager.stop()
