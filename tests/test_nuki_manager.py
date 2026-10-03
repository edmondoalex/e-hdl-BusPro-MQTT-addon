from types import SimpleNamespace

import pytest

from e_hdl_buspro_mqtt.app.nuki_manager import NukiManager, NukiStore


class FakeMqtt:
    def __init__(self):
        self.published = []
        self.subscriptions = []
        self.handler = None

    def set_message_handler(self, handler): self.handler = handler
    def subscribe(self, topic, *, qos=0): self.subscriptions.append((topic, qos))
    def connect(self): pass
    def disconnect(self): pass
    def publish(self, topic, payload, *, qos=0, retain=False): self.published.append((topic, payload, qos))
    def status(self): return SimpleNamespace(connected=True, last_error=None)


def test_persistence_and_secret_is_separate(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    store.configure({"enabled": True, "mqtt_prefix": "doors", "cloud_enabled": True, "api_token": "secret"})
    assert store.load()["config"] == {"enabled": True, "mqtt_prefix": "doors", "cloud_enabled": True}
    assert store.token() == "secret"
    assert "secret" not in (tmp_path / "nuki.json").read_text(encoding="utf-8")


def test_discovery_event_identity_and_command(tmp_path):
    mqtt = FakeMqtt()
    manager = NukiManager(str(tmp_path / "nuki.json"), mqtt)
    manager.store.configure({"enabled": True})
    manager.store.ingest("nuki/123/state", "locked")
    data = manager.store.load()
    data["authorizations"]["42"] = {"auth_id": "42", "name": "Mario"}
    manager.store.save(data)
    manager.store.ingest("nuki/123/lockActionEvent", "1,4,42,7,0")
    snapshot = manager.snapshot()
    assert snapshot["devices"][0]["state"]["state"] == "locked"
    assert snapshot["events"][0]["person"] == "Mario"
    assert snapshot["events"][0]["code_id"] == 7
    with pytest.raises(ValueError): manager.command("123", "unlock")
    manager.store.update_device("123", {"read_only": False, "enabled": True})
    assert manager.command("123", "unlock")["accepted"] is True
    assert mqtt.published == [("nuki/123/unlock", "true", 1)]


def test_start_subscribes_without_home_assistant(tmp_path):
    mqtt = FakeMqtt()
    manager = NukiManager(str(tmp_path / "nuki.json"), mqtt)
    manager.start()
    assert mqtt.subscriptions == [("nuki/#", 1)]
    assert callable(mqtt.handler)
