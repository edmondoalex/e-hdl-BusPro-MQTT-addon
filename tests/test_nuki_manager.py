from types import SimpleNamespace
from pathlib import Path

import pytest

from e_hdl_buspro_mqtt.app.nuki_manager import NukiManager, NukiStore, canonical_device_id
from e_hdl_buspro_mqtt.app import nuki_manager as nuki_module
from e_hdl_buspro_mqtt.app.mqtt_client import MqttClient


def test_nuki_admin_exposes_persistent_icon_editor():
    source = (Path(__file__).resolve().parents[1] / "e_hdl_buspro_mqtt" / "app" / "static" / "hub" / "nuki.js").read_text(encoding="utf-8")
    assert "data-nuki-icon-form" in source
    assert "name=\"icon_override\"" in source
    assert "data-icon-preview-value" in source
    assert "api/integrations/nuki/devices/${encodeURIComponent(iconForm.dataset.id)}/configuration" in source


class FakeMqtt:
    def __init__(self):
        self.published = []
        self.subscriptions = []
        self.handler = None

    def set_message_handler(self, handler, *, include_metadata=False): self.handler = handler
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
    assert canonical_device_id("21181354") == "21181354"
    assert canonical_device_id("21181354", cloud_id=True) == "014333AA"


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
    data["authorizations"]["42"] = {"auth_id": "42", "device_id": "123", "name": "Mario"}
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
    data["authorizations"]["46623"] = {"auth_id": "46623", "device_id": "4D054BEF", "name": "Mario"}
    data["events"] = [{"id": "one", "device_id": "22767029231", "action_name": "Sblocco", "trigger": 172, "trigger_name": "Origine 172", "auth_id": 46623, "code_id": 0}]
    store.save(data)
    event = store.access_events()[0]
    assert event["device_id"] == "4D054BEF"
    assert event["device_name"] == "Portoncino Scala"
    assert event["person"] == "Mario"
    assert event["origin"] == "MQTT"
    assert event["code_id"] == ""


def test_access_events_prefer_named_keypad_code_over_generic_keypad(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "name": "Portoncino Scala", "state": {"state": "1"}}
    data["authorizations"]["77529"] = {"auth_id": "77529", "device_id": "4D054BEF", "name": "Nuki Keypad", "type": 3}
    data["authorizations"]["8192"] = {"auth_id": "8192", "device_id": "4D054BEF", "name": "Claudia", "type": 13}
    data["events"] = [{"id": "keypad", "device_id": "4D054BEF", "action_name": "Sblocco", "trigger": 255, "auth_id": 77529, "code_id": 8192}]
    store.save(data)
    assert store.access_events()[0]["person"] == "Claudia"


def test_access_events_prefer_person_name_over_generic_keypad_authorization(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["authorizations"]["77529"] = {"auth_id": "77529", "device_id": "4D054BEF", "name": "Nuki Keypad", "type": 3}
    data["events"] = [{"id": "cloud-log", "device_id": "4D054BEF", "auth_id": 77529,
                       "code_id": 0, "person": "Mario Rossi"}]
    store.save(data)
    assert store.access_events()[0]["person"] == "Mario Rossi"


def test_access_events_ignore_generic_event_name_for_named_keypad_code(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["authorizations"]["77529"] = {"auth_id": "77529", "device_id": "4D054BEF", "name": "Nuki Keypad", "type": 3}
    data["authorizations"]["8192"] = {"auth_id": "8192", "device_id": "4D054BEF", "name": "Claudia", "type": 13}
    data["events"] = [{"id": "cloud-keypad", "device_id": "4D054BEF", "auth_id": 77529,
                       "code_id": 8192, "person": "Nuki Keypad"}]
    store.save(data)
    assert store.access_events()[0]["person"] == "Claudia"


@pytest.mark.parametrize(("source", "expected_origin"), [("MQTT", "MQTT"), ("Nuki Bridge", "Nuki Bridge")])
def test_access_events_keep_transport_source_out_of_person_field(tmp_path, source, expected_origin):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["events"] = [{"id": "transport", "device_id": "4D054BEF", "trigger": 0,
                       "person": source, "action_name": "Sblocco"}]
    store.save(data)
    event = store.access_events()[0]
    assert event["person"] == "Origine non identificata"
    assert event["origin"] == expected_origin


def test_routine_access_prefers_local_mqtt_and_never_replays_web_copy(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "name": "Scala", "enabled": True,
                                    "read_only": True, "state": {"state": "3"}}
    data["authorizations"]["8192"] = {"auth_id": "8192", "device_id": "4D054BEF",
                                     "name": "easas keypad", "type": 13, "code": "secret-pin", "enabled": True}
    data["authorizations"]["77529"] = {"auth_id": "77529", "device_id": "4D054BEF",
                                      "name": "Nuki Keypad", "type": 3, "enabled": True}
    data["events"] = [
        {"id": "cloud-1", "device_id": "4D054BEF", "action": 1, "auth_id": 77529, "code_id": 8192,
         "timestamp": "2026-10-05T09:00:00Z", "transport": "web_api"},
        {"id": "mqtt-1", "device_id": "4D054BEF", "action": 1, "code_id": 8192,
         "timestamp": "2026-10-05T09:00:01Z", "transport": "mqtt"},
        {"id": "cloud-2", "device_id": "4D054BEF", "action": 1, "code_id": 0,
         "timestamp": "2026-10-05T09:00:02Z", "transport": "web_api"},
    ]
    store.save(data)
    catalog = store.catalog()
    events = store.routine_access_events()
    assert catalog[0]["routine_events"][0]["selectors"] == [
        {"kind": "code_id", "id": "8192", "label": "easas keypad"},
        {"kind": "auth_id", "id": "77529", "label": "Nuki Keypad"}]
    assert events == [{"event_id": "nuki:4D054BEF:mqtt-1", "source": "nuki", "device_id": "4D054BEF",
                       "event_type": "access.used", "action": "unlock", "occurred_at": "2026-10-05T09:00:01Z",
                       "selectors": [{"kind": "code_id", "id": "8192"}]}]
    assert "secret-pin" not in str(catalog) + str(events)


def test_deleted_nuki_authorization_is_removed_from_routine_choices(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "name": "Scala", "enabled": True,
                                    "read_only": True, "state": {"state": "3"}, "web": True}
    data["authorizations"]["8192"] = {"auth_id": "8192", "device_id": "4D054BEF", "type": 13,
                                     "name": "Codice eliminato", "enabled": True}
    manager.store.save(data)
    manager._api = lambda path: ([{"smartlockId": "22767029231", "name": "Scala"}]
                                  if path == "/smartlock" else [])
    manager.sync_cloud()
    assert "8192" not in manager.store.load()["authorizations"]
    assert [item["event_type"] for item in manager.store.catalog()[0]["routine_events"]] == ["access.button"]


def test_numeric_only_mqtt_id_links_web_keypad_code_and_deduplicates_cloud_log(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["21181354"] = {"device_id": "21181354", "name": "Porta Ufficio", "enabled": True,
                                    "read_only": True, "state": {"state": "3"}}
    manager.store.save(data)
    keypad = {"id": "63d66af4e8845a5400cf6053", "authId": 1, "name": "Codice di accesso", "type": 13, "enabled": True}
    cloud_log = {"id": "6ac36dd6badb5149c0ec3ae0", "date": "2026-10-05T09:28:54Z", "action": 1,
                 "trigger": 255, "authId": keypad["id"], "name": "easas keypad (Keypad)", "state": 0}
    manager._api = lambda path: ([{"smartlockId": "555225940", "name": "Porta Ufficio"}] if path == "/smartlock"
                                  else [keypad] if path.endswith("/auth") else [cloud_log])
    manager.sync_cloud()
    manager.sync_cloud()
    assert len(manager.store.load()["events"]) == 1
    assert manager.store.access_events()[0]["origin"] == "Keypad"
    code = next(item for item in manager.store.catalog()[0]["routine_events"] if item["event_type"] == "access.used")
    assert code["selectors"] == [{"kind": "code_id", "id": "1", "label": "easas keypad (Keypad)"}]
    assert manager.store.routine_access_events() == [{"event_id": "nuki:21181354:6ac36dd6badb5149c0ec3ae0",
                                                     "source": "nuki", "device_id": "21181354", "event_type": "access.used",
                                                     "action": "unlock", "occurred_at": "2026-10-05T09:28:54Z",
                                                     "selectors": [{"kind": "code_id", "id": "1"}]}]


def test_nuki_button_is_separate_event_without_code_or_person(tmp_path):
    store = NukiStore(str(tmp_path / "nuki.json"))
    data = store.load()
    data["devices"]["21181354"] = {"device_id": "21181354", "name": "Porta Ufficio", "enabled": True,
                                    "read_only": True, "state": {"state": "3"}}
    data["events"] = [{"id": "button-1", "device_id": "21181354", "timestamp": "2026-10-05T09:00:00Z",
                       "transport": "web_api", "action": 1, "trigger": 2, "state": 0}]
    store.save(data)
    assert store.routine_access_events() == [{"event_id": "nuki:21181354:button-1", "source": "nuki",
                                             "device_id": "21181354", "event_type": "access.button", "action": "unlock",
                                             "occurred_at": "2026-10-05T09:00:00Z",
                                             "selectors": [{"kind": "trigger_id", "id": "2"}]}]


def test_local_mqtt_event_does_not_query_web_and_retained_is_ignored(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    manager.store.configure({"enabled": True, "cloud_enabled": True, "api_token": "test"})
    data = manager.store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "cloud_id": "22767029231",
                                    "state": {}, "enabled": True}
    manager.store.save(data)
    manager._on_mqtt_message("nuki/4D054BEF/lockActionEvent", "1,255,77529,8192,0", True)
    assert manager._cloud_pending == {}
    assert manager.store.load()["events"] == []
    manager._on_mqtt_message("nuki/4D054BEF/lockActionEvent", "1,255,77529,8192,0", False)
    assert manager._cloud_pending == {}
    assert manager.store.load()["devices"]["4D054BEF"]["mqtt_access_events"] is True
    assert len(manager.store.load()["events"]) == 1


def test_local_mqtt_code_is_available_offline_and_duplicate_delivery_is_ignored(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "name": "Scala", "enabled": True,
                                    "read_only": True, "state": {"state": "3"}}
    data["authorizations"]["8192"] = {"auth_id": "8192", "device_id": "4D054BEF",
                                      "name": "Codice Scala", "type": 13, "enabled": True}
    manager.store.save(data)
    manager._on_mqtt_message("nuki/4D054BEF/lockActionEvent", "1,255,77529,8192,0", False)
    manager._on_mqtt_message("nuki/4D054BEF/lockActionEvent", "1,255,77529,8192,0", False)
    assert len(manager.store.load()["events"]) == 1
    event = manager.store.routine_access_events()[0]
    assert event["selectors"] == [{"kind": "code_id", "id": "8192"}]
    assert event["event_id"].startswith("nuki:4D054BEF:mqtt-")
    assert NukiStore(manager.store.path).routine_access_events() == [event]


def test_mqtt_packet_metadata_suppresses_retransmit_but_not_later_real_action(tmp_path, monkeypatch):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "enabled": True, "state": {"state": "3"}}
    data["authorizations"]["8192"] = {"auth_id": "8192", "device_id": "4D054BEF",
                                      "name": "Codice", "type": 13, "enabled": True}
    manager.store.save(data)
    now = [1_000_000.0]
    monkeypatch.setattr(nuki_module.time, "time", lambda: now[0])
    topic, payload = "nuki/4D054BEF/lockActionEvent", "1,255,77529,8192,0"
    manager._on_mqtt_message(topic, payload, False, False, 17)
    now[0] += 10
    manager._on_mqtt_message(topic, payload, False, True, 17)
    assert len(manager.store.load()["events"]) == 1
    now[0] += 1
    manager._on_mqtt_message(topic, payload, False, False, 18)
    assert len(manager.store.load()["events"]) == 2
    assert len({event["event_id"] for event in manager.store.routine_access_events()}) == 2


def test_mqtt_client_metadata_is_opt_in_and_existing_handlers_keep_three_arguments():
    client = MqttClient(host="localhost", port=1883, username="", password="", client_id="test-nuki-metadata")
    received = []
    message = SimpleNamespace(topic="nuki/X/state", payload=b"locked", retain=False, dup=True, mid=17)
    client.set_message_handler(lambda *args: received.append(args))
    client._on_message(None, None, message)
    assert received == [("nuki/X/state", "locked", False)]
    client.set_message_handler(lambda *args: received.append(args), include_metadata=True)
    client._on_message(None, None, message)
    assert received[-1] == ("nuki/X/state", "locked", False, True, 17)


def test_full_web_sync_does_not_erase_local_event_arriving_during_http(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "enabled": True,
                                    "state": {"state": "3"}}
    manager.store.save(data)
    def fake_api(path):
        if path == "/smartlock":
            return [{"smartlockId": "22767029231", "name": "Scala"}]
        if path.endswith("/auth"):
            return [{"id": "web-code-8192", "authId": 8192, "name": "Codice Scala", "type": 13}]
        manager.store.ingest("nuki/4D054BEF/lockActionEvent", "1,255,77529,8192,0")
        return [{"id": "web-copy", "date": "2026-10-05T09:00:00Z", "action": 1,
                 "authId": "web-code-8192", "trigger": 255, "state": 0}]
    manager._api = fake_api
    manager.sync_cloud()
    stored = manager.store.load()
    assert len(stored["events"]) == 2
    assert stored["devices"]["4D054BEF"]["mqtt_access_events"] is True
    assert stored["devices"]["4D054BEF"]["state"]["lockActionEvent"] == "1,255,77529,8192,0"
    assert len(manager.store.routine_access_events()) == 1
    assert manager.store.routine_access_events()[0]["event_id"].startswith("nuki:4D054BEF:mqtt-")


def test_local_bridge_state_change_queues_cloud_refresh_once(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["21181354"] = {"device_id": "21181354", "cloud_id": "555225940",
                                    "state": {"state": "1"}, "enabled": True}
    manager.store.save(data)
    signals = []
    manager._queue_cloud_refresh = signals.append
    manager._bridge = lambda path: [{"nukiId": 555225940, "name": "Porta Ufficio",
                                     "lastKnownState": {"state": 3}}]
    manager.sync_bridge()
    manager.sync_bridge()
    assert signals == ["21181354"]


def test_mqtt_capable_lock_never_queues_targeted_web_lookup(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    manager.store.configure({"cloud_enabled": True, "api_token": "test"})
    data = manager.store.load()
    data["devices"]["4D054BEF"] = {"device_id": "4D054BEF", "cloud_id": "22767029231",
                                       "mqtt_access_events": True, "state": {"lockActionEvent": "1,255,77529,8192,0"}}
    manager.store.save(data)
    manager._queue_cloud_refresh("4D054BEF")
    assert manager._cloud_pending == {}


def test_targeted_cloud_log_fetch_is_idempotent_and_retains_exact_code_id(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["21181354"] = {"device_id": "21181354", "cloud_id": "555225940",
                                    "state": {"state": "3"}, "enabled": True}
    data["authorizations"]["1"] = {"auth_id": "1", "web_id": "hex-auth-1",
                                      "device_id": "21181354", "name": "Codice", "type": 13, "enabled": True}
    manager.store.save(data)
    calls = []
    def fake_api(path):
        calls.append(path)
        return [{"id": "web-log-1", "date": "2026-10-05T09:28:54Z", "action": 1,
                 "trigger": 255, "authId": "hex-auth-1", "name": "Codice (Keypad)", "state": 0}]
    manager._api = fake_api
    assert manager.sync_cloud_logs("21181354") == {"events": 1}
    assert manager.sync_cloud_logs("21181354") == {"events": 0}
    assert calls == ["/smartlock/555225940/log?limit=50"] * 2
    assert len(manager.store.load()["events"]) == 1
    assert manager.store.routine_access_events()[0]["selectors"] == [{"kind": "code_id", "id": "1"}]


def test_directory_keeps_same_local_auth_id_separate_for_each_lock(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    def api(path):
        if path == "/smartlock":
            return [{"smartlockId": 1, "name": "Studio"}, {"smartlockId": 2, "name": "Ingresso"}]
        if "/auth" in path:
            number = path.split("/")[2]
            return [{"authId": 7, "id": f"web-{number}", "type": 13, "name": f"Codice {number}",
                     "code": "SECRET-PIN", "enabled": number == "1", "remoteAllowed": False}]
        return []
    manager._api = api
    manager.sync_cloud()
    manager.store.ingest("nuki/00000001/state", "locked")
    manager.store.ingest("nuki/00000002/state", "locked")
    directory = manager.store.access_directory()
    assert directory["counts"]["codes"] == 2
    by_lock = {lock["device_id"]: lock for lock in directory["locks"]}
    assert by_lock["00000001"]["entries"][0]["name"] == "Codice 1"
    assert by_lock["00000002"]["entries"][0]["name"] == "Codice 2"
    assert by_lock["00000002"]["entries"][0]["enabled"] is False
    assert NukiStore(manager.store.path).access_directory() == directory
    assert "SECRET-PIN" not in str(manager.snapshot())
    manager.store.ingest("nuki/00000001/lockActionEvent", "1,255,0,7,0")
    assert manager.store.access_events()[0]["person"] == "Codice 1"
    manager.store.ingest("nuki/00000002/lockActionEvent", "1,255,0,7,0")
    assert manager.store.access_events()[0]["person"] == "Codice 2"


def test_directory_never_assigns_legacy_or_other_lock_authorizations_by_name(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"] = {did: {"device_id": did, "name": did, "state": {"state": "1"}}
                       for did in ("00000001", "00000002")}
    data["authorizations"] = {
        "legacy": {"auth_id": "42", "name": "Nome uguale", "code": "LEGACY-PIN"},
        "scoped": {"auth_id": "42", "device_id": "00000002", "type": 0, "name": "Nome uguale"},
        "keypad": {"auth_id": "43", "device_id": "00000002", "type": 3, "name": "Keypad"},
        "future": {"auth_id": "44", "device_id": "00000002", "type": 98, "name": "Nuovo tipo"},
    }
    data["events"] = [{"id": "one", "device_id": "00000001", "auth_id": 42, "action": 1}]
    manager.store.save(data)
    directory = manager.store.access_directory()
    assert len(directory["unassigned"]) == 1
    assert directory["locks"][0]["entries"] == []
    assert {entry["group"] for entry in directory["locks"][1]["entries"]} == {"users", "accessories", "other"}
    assert manager.store.access_events()[0]["person"] == "Autorizzazione 42"
    assert "LEGACY-PIN" not in str(manager.snapshot())


def test_failed_authorization_refresh_preserves_saved_directory(tmp_path):
    manager = NukiManager(str(tmp_path / "nuki.json"), FakeMqtt())
    data = manager.store.load()
    data["devices"]["00000001"] = {"device_id": "00000001", "name": "Studio", "state": {"state": "1"},
                                    "authorizations_synced_at": 123, "authorizations_status": "ok"}
    data["authorizations"]["7"] = {"auth_id": "7", "device_id": "00000001", "type": 2, "name": "Telecomando"}
    manager.store.save(data)
    def api(path):
        if path == "/smartlock": return [{"smartlockId": 1, "name": "Studio"}]
        if "/auth" in path: raise ValueError("Nuki Web non disponibile")
        return []
    manager._api = api
    manager.sync_cloud()
    lock = NukiStore(manager.store.path).access_directory()["locks"][0]
    assert lock["sync_status"] == "error"
    assert lock["last_synced_at"] == 123
    assert lock["entries"][0]["type_label"] == "Fob"


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
