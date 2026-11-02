from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import shutil
import tempfile
import threading
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid


ACTION_NAMES = {1: "Sblocco", 2: "Blocco", 3: "Apertura", 4: "Lock 'n' Go", 5: "Lock 'n' Go con apertura", 240: "Porta aperta", 241: "Porta chiusa", 242: "Sensore porta bloccato"}
TRIGGER_NAMES = {0: "Sistema/App/Keypad", 1: "Manuale", 2: "Pulsante", 3: "Fob/Automatico", 4: "Tastierino", 5: "Auto Unlock", 6: "Chiusura automatica/Web API", 7: "App", 8: "HomeKit", 9: "MQTT", 10: "Matter", 171: "HomeKit/Matter", 172: "MQTT"}
WEB_TRIGGER_NAMES = {0: "Sistema", 1: "Manuale", 2: "Pulsante", 3: "Automatico", 4: "Nuki Web", 5: "App", 6: "Chiusura automatica", 7: "Accessorio", 255: "Keypad"}
COMMAND_TOPICS = {"unlock": "unlock", "lock": "lock", "unlatch": "unlatch", "lockngo": "lockNgo", "lockngo_unlatch": "lockNgoUnlatch"}
LOCK_STATES = {0: "uncalibrated", 1: "locked", 2: "unlocking", 3: "unlocked", 4: "locking", 5: "unlatched", 6: "unlocked", 7: "unlatching", 254: "motor_blocked", 255: "undefined"}
AUTH_TYPES = {
    0: ("users", "App Nuki"), 1: ("accessories", "Bridge"),
    2: ("accessories", "Fob"), 3: ("accessories", "Keypad"),
    13: ("codes", "Codice keypad"), 14: ("accessories", "Z-Key"),
    15: ("other", "Autorizzazione virtuale"),
}


def canonical_device_id(value: Any, *, cloud_id: bool = False) -> str:
    """Return the 8-char MQTT id from either MQTT id or Web API smartlockId."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    # An 8-character MQTT ID can contain only digits; converting it again as
    # decimal changes its identity (and breaks event deduplication).
    if raw.isdigit() and (cloud_id or len(raw) != 8):
        return f"{int(raw) & 0xFFFFFFFF:08X}"
    return raw.upper()


def event_time_seconds(event: dict[str, Any]) -> float:
    value = event.get("timestamp")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
        except ValueError:
            return 0.0
    return 0.0


class NukiStore:
    def __init__(self, path: str):
        self.path = path
        self.secret_path = path + ".credentials"
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {"schema_version": 1, "config": {"enabled": False, "mqtt_prefix": "nuki", "cloud_enabled": False, "bridge_enabled": False, "bridge_host": "", "bridge_port": 8080}, "devices": {}, "authorizations": {}, "events": [], "rules": []}

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict) or data.get("schema_version") != 1:
                    raise ValueError("unsupported schema")
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                return self.empty()
            out = self.empty()
            for key in out:
                if key in data and isinstance(data[key], type(out[key])):
                    if key == "config":
                        out[key].update(data[key])
                    else:
                        out[key] = data[key]
            return out

    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            folder = os.path.dirname(self.path) or "."
            os.makedirs(folder, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".nuki-", suffix=".json", dir=folder)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
                    handle.flush(); os.fsync(handle.fileno())
                if os.path.isfile(self.path): shutil.copy2(self.path, self.path + ".bak")
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
            return deepcopy(data)

    def set_token(self, token: str) -> None:
        token = str(token or "").strip()
        if not token: return
        folder = os.path.dirname(self.secret_path) or "."; os.makedirs(folder, exist_ok=True)
        with open(self.secret_path, "w", encoding="utf-8") as handle: handle.write(token)
        try: os.chmod(self.secret_path, 0o600)
        except OSError: pass

    def token(self) -> str:
        try:
            with open(self.secret_path, "r", encoding="utf-8") as handle: return handle.read().strip()
        except OSError: return ""

    def configure(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self.load(); config = data["config"]
        for key in ("enabled", "cloud_enabled", "bridge_enabled"):
            if key in payload: config[key] = bool(payload[key])
        if "bridge_host" in payload: config["bridge_host"] = str(payload["bridge_host"] or "").strip()
        if "bridge_port" in payload: config["bridge_port"] = max(1, min(65535, int(payload["bridge_port"] or 8080)))
        if "mqtt_prefix" in payload:
            prefix = str(payload["mqtt_prefix"] or "nuki").strip().strip("/")
            if not prefix or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in prefix): raise ValueError("Prefisso MQTT non valido")
            config["mqtt_prefix"] = prefix
        if payload.get("api_token"): self.set_token(str(payload["api_token"]))
        if payload.get("bridge_token"): self.set_bridge_token(str(payload["bridge_token"]))
        return self.save(data)

    def set_bridge_token(self, token: str) -> None:
        token = str(token or "").strip()
        if not token: return
        path = self.secret_path + ".bridge"
        folder = os.path.dirname(path) or "."; os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle: handle.write(token)
        try: os.chmod(path, 0o600)
        except OSError: pass

    def bridge_token(self) -> str:
        try:
            with open(self.secret_path + ".bridge", "r", encoding="utf-8") as handle: return handle.read().strip()
        except OSError: return ""

    def update_device(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self.load(); row = data["devices"].get(device_id)
        if not isinstance(row, dict): raise KeyError(device_id)
        for key in ("enabled", "read_only"):
            if key in payload: row[key] = bool(payload[key])
        self.save(data); return deepcopy(row)

    @staticmethod
    def authorization(data: dict[str, Any], device_id: str, identifier: Any) -> dict[str, Any]:
        identifier = str(identifier or "").strip()
        if not identifier or identifier == "0":
            return {}
        did = canonical_device_id(device_id)
        matches = [auth for auth in data["authorizations"].values() if isinstance(auth, dict)
                   and canonical_device_id(auth.get("device_id")) == did
                   and identifier in {str(auth.get("auth_id") or ""), str(auth.get("web_id") or "")}]
        return matches[0] if len(matches) == 1 else {}

    @staticmethod
    def public_authorizations(data: dict[str, Any]) -> list[dict[str, Any]]:
        fields = ("auth_id", "web_id", "device_id", "name", "type", "enabled", "allowed_from",
                  "allowed_until", "remote_allowed", "account_user_id")
        return [{key: auth[key] for key in fields if key in auth}
                for auth in data["authorizations"].values() if isinstance(auth, dict)]

    def access_directory(self) -> dict[str, Any]:
        """Present explicit Nuki authorization-to-lock relationships, without PINs."""
        data = self.load()
        locks = {}
        for device in self.rows(include_cloud_only=True):
            did = canonical_device_id(device.get("device_id"))
            locks[did] = {"device_id": did, "name": device.get("name") or f"Nuki {did}",
                          "available": bool(device.get("available")), "state": device.get("state"),
                          "last_synced_at": device.get("authorizations_synced_at"),
                          "sync_status": device.get("authorizations_status") or "unknown", "entries": []}
        unassigned = []
        counts = {"users": 0, "codes": 0, "accessories": 0, "other": 0}
        for auth in self.public_authorizations(data):
            try:
                auth_type = int(auth.get("type"))
            except (ValueError, TypeError):
                auth_type = None
            group, label = AUTH_TYPES.get(auth_type, ("other", "Tipo non disponibile" if auth_type is None else f"Altro tipo Nuki ({auth_type})"))
            did = canonical_device_id(auth.get("device_id"))
            entry = {**auth, "device_id": did, "group": group, "type_label": label,
                     "enabled": auth.get("enabled", True),
                     "name": str(auth.get("name") or "Autorizzazione senza nome")}
            if not did or did not in locks:
                unassigned.append(entry)
                continue
            locks[did]["entries"].append(entry)
            counts[group] += 1
        for lock in locks.values():
            lock["entries"].sort(key=lambda entry: (not entry["enabled"], entry["name"].casefold(), str(entry.get("auth_id"))))
        return {"locks": sorted(locks.values(), key=lambda lock: lock["name"].casefold()),
                "unassigned": unassigned, "counts": {"locks": len(locks), **counts}}

    def ingest(self, topic: str, payload: str, *, mqtt_duplicate: bool = False,
               packet_id: int = 0) -> dict[str, Any] | None:
        with self._lock:
            return self._ingest_locked(topic, payload, mqtt_duplicate=mqtt_duplicate, packet_id=packet_id)

    def _ingest_locked(self, topic: str, payload: str, *, mqtt_duplicate: bool = False,
                       packet_id: int = 0) -> dict[str, Any] | None:
        data = self.load(); prefix = str(data["config"].get("mqtt_prefix") or "nuki")
        parts = topic.split("/")
        if len(parts) < 3 or parts[0] != prefix: return None
        device_id, field = parts[1], "/".join(parts[2:])
        row = data["devices"].setdefault(device_id, {"device_id": device_id, "name": f"Nuki {device_id}", "device_class": "lock", "capabilities": list(COMMAND_TOPICS), "enabled": False, "read_only": True, "state": {}, "last_seen": 0})
        row["last_seen"] = int(time.time()); row["state"][field] = payload
        if field in {"name", "deviceName"} and str(payload or "").strip():
            row["name"] = str(payload).strip()
        if field == "lockActionEvent":
            values = [x.strip() for x in payload.split(",")]
            if len(values) >= 5:
                nums = [int(x) if x.lstrip("-").isdigit() else 0 for x in values[:5]]
                auth = self.authorization(data, device_id, nums[2])
                now = time.time()
                duplicate = next((event for event in data["events"] if event.get("transport") == "mqtt"
                                  and canonical_device_id(event.get("device_id")) == canonical_device_id(device_id)
                                  and all(str(event.get(key)) == str(value) for key, value in zip(
                                      ("action", "trigger", "auth_id", "code_id", "detail"), nums))
                                  and (abs(now - event_time_seconds(event)) < 2
                                       or (mqtt_duplicate and packet_id > 0 and event.get("mqtt_packet_id") == packet_id
                                           and abs(now - event_time_seconds(event)) < 120))), None)
                row["mqtt_access_events"] = True
                if not duplicate:
                    event = {"id": f"mqtt-{uuid.uuid4().hex}", "device_id": device_id, "timestamp": now,
                             "action": nums[0], "action_name": ACTION_NAMES.get(nums[0], f"Azione {nums[0]}"),
                             "trigger": nums[1], "trigger_name": TRIGGER_NAMES.get(nums[1], f"Origine {nums[1]}"),
                             "auth_id": nums[2], "code_id": nums[3], "detail": nums[4],
                             "mqtt_packet_id": packet_id if packet_id > 0 else None,
                             "person": auth.get("name") or (f"Autorizzazione {nums[2]}" if nums[2] else "Origine non identificata"),
                             "transport": "mqtt"}
                    data["events"] = ([event] + data["events"])[:1000]
                    row["last_event"] = event
                else:
                    row["last_event"] = duplicate
        self.save(data); return deepcopy(row)

    def rows(self, *, include_cloud_only: bool = False) -> list[dict[str, Any]]:
        now = time.time(); result = []; data = self.load()
        cloud_authoritative = bool(data["config"].get("cloud_enabled") and self.token())
        for row in data["devices"].values():
            state = row.get("state") or {}; raw_state = state.get("state") or state.get("lockState") or "unknown"
            if cloud_authoritative and not row.get("web") and row.get("bridge_id") is None:
                continue
            if not cloud_authoritative and not include_cloud_only and not state and not row.get("last_seen"):
                continue
            lock_state = LOCK_STATES.get(int(raw_state), raw_state) if str(raw_state).isdigit() else raw_state
            recent = now - float(row.get("last_seen") or 0) < 180
            available = str(state.get("connected") or "").strip().lower() == "true" or recent
            result.append({**deepcopy(row), "source": "nuki", "native_type": "smart_lock", "native_id": row.get("device_id"), "available": available, "stale": not available, "state": {"state": lock_state, "attributes": deepcopy(state)}})
        return result

    def catalog(self) -> list[dict[str, Any]]:
        data = self.load()
        authorizations = data.get("authorizations") or {}
        observed_names = {}
        for event in data.get("events") or []:
            if not isinstance(event, dict) or event.get("transport") != "web_api" or str(event.get("trigger")) != "255":
                continue
            web_id = str(event.get("auth_id") or "").strip()
            name = str(event.get("person") or "").strip()
            if web_id and name and name.casefold() != "origine non identificata" and web_id not in observed_names:
                observed_names[web_id] = name
        result = []
        for row in self.rows():
            if not row.get("enabled"):
                continue
            device_id = canonical_device_id(row.get("device_id"))
            selectors = []
            for auth in authorizations.values():
                if not isinstance(auth, dict) or canonical_device_id(auth.get("device_id")) != device_id or not auth.get("enabled", True):
                    continue
                identifier = str(auth.get("auth_id") or "").strip()
                if not identifier or identifier == "0":
                    continue
                kind = "code_id" if str(auth.get("type") or "") == "13" else "auth_id"
                label = observed_names.get(str(auth.get("web_id") or "")) if kind == "code_id" else None
                selectors.append({"kind": kind, "id": identifier, "label": str(label or auth.get("name") or identifier)[:100]})
            clean = deepcopy(row)
            clean["routine_events"] = []
            if selectors:
                clean["routine_events"].append({"event_type": "access.used", "actions": ["unlock", "lock", "open"], "selectors": selectors})
            clean["routine_events"].append({"event_type": "access.button", "actions": ["unlock", "lock", "open"],
                                            "selectors": [{"kind": "trigger_id", "id": "2", "label": "Pulsante fisico Nuki"}]})
            result.append(clean)
        return result

    def routine_access_events(self, limit: int = 200) -> list[dict[str, Any]]:
        """Use local MQTT where available; Web logs are for Bridge-only locks."""
        data = self.load()
        declared = {row["device_id"]: {item["event_type"]: item["selectors"] for item in row["routine_events"]}
                    for row in self.catalog() if row.get("routine_events")}
        local_devices = {canonical_device_id(row.get("device_id")) for row in data["devices"].values()
                         if isinstance(row, dict) and (row.get("mqtt_access_events")
                                                       or (row.get("state") or {}).get("lockActionEvent"))}
        local_devices.update(canonical_device_id(event.get("device_id")) for event in data["events"]
                             if isinstance(event, dict) and event.get("transport") == "mqtt")
        authorizations = {(canonical_device_id(row.get("device_id")), str(row.get("web_id"))): row
                          for row in (data.get("authorizations") or {}).values()
                          if isinstance(row, dict) and row.get("web_id") and row.get("enabled", True)}
        action_names = {1: "unlock", 2: "lock", 3: "open"}
        result = []
        seen = set()
        for event in (data.get("events") or [])[:max(1, min(1000, int(limit)))]:
            if not isinstance(event, dict) or event.get("transport") not in {"mqtt", "web_api"}:
                continue
            device_id = canonical_device_id(event.get("device_id"))
            transport = event.get("transport")
            if (device_id in local_devices) != (transport == "mqtt"):
                continue
            if transport == "web_api" and event.get("state") not in (None, 0, "0"):
                continue
            try:
                action = action_names.get(int(event.get("action")))
            except (TypeError, ValueError):
                action = None
            event_id = str(event.get("id") or "").strip()
            if not device_id or not event_id or not action or device_id not in declared or (device_id, event_id) in seen:
                continue
            seen.add((device_id, event_id))
            if str(event.get("trigger")) == "2":
                result.append({"event_id": f"nuki:{device_id}:{event_id}", "source": "nuki", "device_id": device_id,
                               "event_type": "access.button", "action": action, "occurred_at": event.get("timestamp"),
                               "selectors": [{"kind": "trigger_id", "id": "2"}]})
                continue
            selectors = []
            if transport == "mqtt":
                code_id = str(event.get("code_id") or "").strip()
                auth_id = str(event.get("auth_id") or "").strip()
                if code_id and code_id != "0":
                    if any(option["kind"] == "code_id" and option["id"] == code_id
                           for option in declared[device_id].get("access.used", [])):
                        selectors.append({"kind": "code_id", "id": code_id})
                elif auth_id and auth_id != "0":
                    if any(option["kind"] == "auth_id" and option["id"] == auth_id
                           for option in declared[device_id].get("access.used", [])):
                        selectors.append({"kind": "auth_id", "id": auth_id})
                if selectors:
                    result.append({"event_id": f"nuki:{device_id}:{event_id}", "source": "nuki", "device_id": device_id,
                                   "event_type": "access.used", "action": action, "occurred_at": event.get("timestamp"),
                                   "selectors": selectors})
                continue
            web_id = str(event.get("auth_id") or "").strip()
            auth = authorizations.get((device_id, web_id))
            if auth:
                kind = "code_id" if str(auth.get("type") or "") == "13" else "auth_id"
                identifier = str(auth.get("auth_id") or "").strip()
                if any(option["kind"] == kind and option["id"] == identifier for option in declared[device_id].get("access.used", [])):
                    selectors.append({"kind": kind, "id": identifier})
            for kind in ("auth_id", "code_id"):
                identifier = str(event.get(kind) or "").strip()
                if identifier and identifier != "0" and any(option["kind"] == kind and option["id"] == identifier for option in declared[device_id].get("access.used", [])) and {"kind": kind, "id": identifier} not in selectors:
                    selectors.append({"kind": kind, "id": identifier})
            if selectors:
                result.append({"event_id": f"nuki:{device_id}:{event_id}", "source": "nuki", "device_id": device_id,
                               "event_type": "access.used", "action": action, "occurred_at": event.get("timestamp"),
                               "selectors": selectors})
        return result
    def organization_catalog(self) -> list[dict[str, Any]]:
        return [
            {"device_id": row["device_id"], "name": row["name"], "device_class": "lock"}
            for row in self.rows()
            if row.get("available") or row.get("enabled")
        ]

    def access_events(self, limit: int = 200) -> list[dict[str, Any]]:
        data = self.load()
        names = {canonical_device_id(key): str(row.get("name") or key) for key, row in data["devices"].items()}
        result: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for raw in (data.get("events") or [])[:max(1, min(1000, int(limit)) )]:
            event = deepcopy(raw)
            event.pop("mqtt_packet_id", None)
            device_id = canonical_device_id(event.get("device_id"))
            event_id = str(event.get("id") or "").strip()
            if event_id and (device_id, event_id) in seen:
                continue
            if event_id:
                seen.add((device_id, event_id))
            auth_id = str(event.get("auth_id") or "").strip()
            code_id = str(event.get("code_id") or "").strip()
            authorization = self.authorization(data, device_id, auth_id)
            code_authorization = self.authorization(data, device_id, code_id)
            def usable_person(value: Any) -> str:
                name = str(value or "").strip()
                if not name or name.startswith("Autorizzazione ") or name.casefold() in {
                    "origine non identificata", "nuki keypad", "keypad", "tastierino",
                    "mqtt", "nuki bridge", "nuki web",
                }:
                    return ""
                return name

            code_name = usable_person((code_authorization or {}).get("name"))
            authorization_name = usable_person((authorization or {}).get("name"))
            event_name = usable_person(event.get("person"))
            # A named keypad code identifies the code, not necessarily its user.
            named_keypad_code = code_name if str((code_authorization or {}).get("type") or "") == "13" else ""
            person = named_keypad_code or event_name or code_name or authorization_name
            if not person:
                person = f"Codice keypad {code_id}" if code_id and code_id != "0" else (f"Autorizzazione {auth_id}" if auth_id and auth_id != "0" else "Origine non identificata")
            trigger = event.get("trigger")
            try: trigger_number = int(trigger)
            except (TypeError, ValueError): trigger_number = -1
            event_source = str(event.get("person") or "").strip()
            source_origin = {
                "mqtt": "MQTT", "nuki bridge": "Nuki Bridge", "nuki web": "Nuki Web",
            }.get(event_source.casefold())
            trigger_names = WEB_TRIGGER_NAMES if event.get("transport") == "web_api" else TRIGGER_NAMES
            origin = str(source_origin or trigger_names.get(trigger_number) or event.get("trigger_name") or "").strip()
            event.update({
                "device_id": device_id,
                "device_name": names.get(device_id, f"Nuki {device_id}"),
                "person": person,
                "origin": origin or "Non identificata",
                "auth_id": "" if auth_id == "0" else auth_id,
                "code_id": "" if code_id == "0" else code_id,
            })
            result.append(event)
        return result


class NukiManager:
    def __init__(self, path: str, mqtt: Any):
        self.store, self.mqtt = NukiStore(path), mqtt
        self._started = False
        self._bridge_stop = threading.Event()
        self._bridge_thread: threading.Thread | None = None
        self._cloud_stop = threading.Event()
        self._cloud_thread: threading.Thread | None = None
        self._cloud_wake = threading.Event()
        self._cloud_queue_lock = threading.Lock()
        self._cloud_pending: dict[str, list[float]] = {}
        self._cloud_last_signal: dict[str, float] = {}
        self._cloud_sync_lock = threading.Lock()
    def _on_mqtt_message(self, topic: str, payload: str, retained: bool,
                         duplicate: bool = False, packet_id: int = 0) -> None:
        if retained and topic.endswith("/lockActionEvent"):
            return
        self.store.ingest(topic, payload, mqtt_duplicate=duplicate, packet_id=packet_id)
    def _queue_cloud_refresh(self, device_id: Any) -> None:
        data = self.store.load()
        if not (data["config"].get("cloud_enabled") and self.store.token()): return
        did = canonical_device_id(device_id)
        row = data["devices"].get(did) or {}
        if not row.get("cloud_id") or row.get("mqtt_access_events") or (row.get("state") or {}).get("lockActionEvent"):
            return
        now = time.monotonic()
        with self._cloud_queue_lock:
            if now - self._cloud_last_signal.get(did, -1e9) < 30: return
            self._cloud_last_signal[did] = now
            # Give Nuki Web a moment to receive the log, then retry once.
            self._cloud_pending[did] = [now + 2, now + 35]
        self._cloud_wake.set()
    def start(self) -> None:
        config = self.store.load()["config"]
        if config.get("enabled"):
            prefix = config.get("mqtt_prefix") or "nuki"
            self.mqtt.set_message_handler(self._on_mqtt_message, include_metadata=True)
            self.mqtt.subscribe(f"{prefix}/#", qos=1); self.mqtt.connect()
            self._started = True
        else:
            self._started = False
        self._start_bridge_poll()
        self._start_cloud_poll()
    def stop(self) -> None:
        self._bridge_stop.set()
        if self._bridge_thread and self._bridge_thread.is_alive(): self._bridge_thread.join(timeout=2)
        self._bridge_thread = None
        self._cloud_stop.set()
        self._cloud_wake.set()
        if self._cloud_thread and self._cloud_thread.is_alive(): self._cloud_thread.join(timeout=2)
        self._cloud_thread = None
        with self._cloud_queue_lock:
            self._cloud_pending.clear()
            self._cloud_last_signal.clear()
        self._cloud_wake.clear()
        if self._started:
            prefix = self.store.load()["config"].get("mqtt_prefix") or "nuki"
            self.mqtt.unsubscribe(f"{prefix}/#")
            self.mqtt.disconnect()
        self._started = False
    def _start_cloud_poll(self) -> None:
        config = self.store.load()["config"]
        if not (config.get("cloud_enabled") and self.store.token()): return
        if self._cloud_thread and self._cloud_thread.is_alive(): return
        self._cloud_stop.clear()
        self._cloud_wake.clear()
        def poll() -> None:
            if self._cloud_stop.wait(5): return
            last_full = 0.0
            while True:
                if self._cloud_stop.is_set(): return
                now = time.monotonic()
                if now - last_full >= 60:
                    try: self.sync_cloud()
                    except (ValueError, OSError): pass
                    last_full = time.monotonic()
                    continue
                with self._cloud_queue_lock:
                    due = min((times[0] for times in self._cloud_pending.values() if times), default=float("inf"))
                timeout = max(0.0, min(last_full + 60, due) - now)
                self._cloud_wake.wait(timeout)
                self._cloud_wake.clear()
                if self._cloud_stop.is_set(): return
                now = time.monotonic()
                ready = []
                with self._cloud_queue_lock:
                    for did, times in list(self._cloud_pending.items()):
                        if times and times[0] <= now:
                            ready.append(did)
                            times.pop(0)
                            if not times: del self._cloud_pending[did]
                for did in ready:
                    try: self.sync_cloud_logs(did)
                    except (ValueError, OSError): pass
        self._cloud_thread = threading.Thread(target=poll, name="nuki-cloud", daemon=True)
        self._cloud_thread.start()
    def _start_bridge_poll(self) -> None:
        config = self.store.load()["config"]
        if not (config.get("bridge_enabled") and self.store.bridge_token()): return
        if self._bridge_thread and self._bridge_thread.is_alive(): return
        self._bridge_stop.clear()
        def poll() -> None:
            while not self._bridge_stop.wait(10):
                try: self.sync_bridge()
                except (ValueError, OSError): pass
        self._bridge_thread = threading.Thread(target=poll, name="nuki-bridge", daemon=True)
        self._bridge_thread.start()
    def configure(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.stop()
        self.store.configure(payload)
        self.start()
        return self.snapshot()
    def reset(self) -> dict[str, Any]:
        self.stop()
        for path in (self.store.path, self.store.path + ".bak", self.store.secret_path, self.store.secret_path + ".bridge"):
            try: os.unlink(path)
            except FileNotFoundError: pass
        return self.snapshot()
    def command(self, device_id: str, action: str) -> dict[str, Any]:
        row = next((x for x in self.store.rows() if x["device_id"] == device_id), None)
        if not row: raise KeyError(device_id)
        if row.get("read_only", True): raise ValueError("Comandi Nuki disabilitati")
        suffix = COMMAND_TOPICS.get(action)
        if not suffix: raise ValueError("Comando Nuki non supportato")
        attributes = (row.get("state") or {}).get("attributes") or {}
        if row.get("bridge_id") is not None and not attributes.get("firmware"):
            actions = {"unlock": 1, "lock": 2, "unlatch": 3, "lockngo": 4, "lockngo_unlatch": 5}
            self._bridge("/lockAction", {"nukiId": row["bridge_id"], "deviceType": row.get("device_type", 0), "action": actions[action]})
            return {"ok": True, "accepted": True, "confirmed": False, "source": "nuki_bridge"}
        prefix = self.store.load()["config"].get("mqtt_prefix") or "nuki"
        self.mqtt.publish(f"{prefix}/{device_id}/{suffix}", "true", qos=1)
        return {"ok": True, "accepted": True, "confirmed": False, "source": "nuki"}
    def discover_bridges(self) -> list[dict[str, Any]]:
        try:
            with urllib.request.urlopen("https://api.nuki.io/discover/bridges", timeout=10) as response:
                return list((json.loads(response.read().decode("utf-8")) or {}).get("bridges") or [])
        except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Rilevamento Nuki Bridge non riuscito: {exc}") from exc
    def _bridge(self, path: str, params: dict[str, Any] | None = None, *, authenticated: bool = True, timeout: int = 10) -> Any:
        cfg = self.store.load()["config"]; host = str(cfg.get("bridge_host") or "").strip()
        if not host: raise ValueError("Nuki Bridge non configurato")
        query = dict(params or {})
        if authenticated:
            token = self.store.bridge_token()
            if not token: raise ValueError("Token Nuki Bridge non configurato")
            query["token"] = token
        endpoint = f"http://{host}:{int(cfg.get('bridge_port') or 8080)}{path}?{urllib.parse.urlencode(query)}"
        try:
            with urllib.request.urlopen(endpoint, timeout=timeout) as response: return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            messages = {
                403: "Autorizzazione HTTP disabilitata sul Nuki Bridge. Abilitala nelle impostazioni del Bridge e riprova.",
                404: "Pairing non completato: premi Associa Bridge e poi il pulsante fisico del Bridge entro 30 secondi.",
                503: "Nuki Bridge temporaneamente occupato. Attendi alcuni secondi, premi Associa Bridge e poi il pulsante fisico.",
            }
            raise ValueError(messages.get(exc.code, f"Nuki Bridge HTTP {exc.code}")) from exc
        except urllib.error.URLError as exc: raise ValueError(f"Nuki Bridge non raggiungibile: {exc.reason}") from exc
    def pair_bridge(self, host: str, port: int = 8080) -> dict[str, Any]:
        self.store.configure({"bridge_host": host, "bridge_port": port, "bridge_enabled": True})
        result = self._bridge("/auth", authenticated=False, timeout=35); token = str(result.get("token") or "")
        if not token: raise ValueError("Pairing non completato: premi Associa Bridge e poi il pulsante fisico entro 30 secondi")
        self.store.configure({"bridge_token": token})
        result = self.sync_bridge(); self._start_bridge_poll()
        return result
    def sync_bridge(self) -> dict[str, Any]:
        items = self._bridge("/list"); count = 0; changed = []
        with self.store._lock:
            data = self.store.load()
            for item in items if isinstance(items, list) else []:
                bridge_id = item.get("nukiId"); did = canonical_device_id(bridge_id, cloud_id=True)
                if not did: continue
                row = data["devices"].setdefault(did, {"device_id": did, "enabled": False, "read_only": True, "capabilities": list(COMMAND_TOPICS), "state": {}})
                known = item.get("lastKnownState") if isinstance(item.get("lastKnownState"), dict) else {}
                old_state = str((row.get("state") or {}).get("state") or "")
                new_state = str(known.get("state") or "")
                if old_state and new_state and old_state != new_state:
                    changed.append(did)
                row.update({"name": item.get("name") or row.get("name") or f"Nuki {did}", "bridge_id": bridge_id, "device_type": item.get("deviceType", 0), "device_class": "lock"})
                for key, value in known.items(): row["state"][key] = str(value).lower() if isinstance(value, bool) else str(value)
                row["state"]["connected"] = "true" if known else "false"
                row["last_seen"] = int(time.time()) if known else 0
                count += 1
            self.store.save(data)
        for did in changed: self._queue_cloud_refresh(did)
        return {"devices": count}
    def _api(self, path: str) -> Any:
        token = self.store.token()
        if not token: raise ValueError("Token Nuki Web API non configurato")
        req = urllib.request.Request("https://api.nuki.io" + path, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as response: return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc: raise ValueError(f"Nuki Web API HTTP {exc.code}") from exc
    def sync_cloud_logs(self, device_id: str) -> dict[str, int]:
        """Fetch only one lock's activity log after a local MQTT/Bridge signal."""
        did = canonical_device_id(device_id)
        with self._cloud_sync_lock:
            row = (self.store.load()["devices"].get(did) or {})
            cloud_id = str(row.get("cloud_id") or "")
            if not cloud_id: return {"events": 0}
            logs = self._api(f"/smartlock/{urllib.parse.quote(cloud_id)}/log?limit=50")
            if not isinstance(logs, list): return {"events": 0}
            with self.store._lock:
                data = self.store.load()
                if str((data["devices"].get(did) or {}).get("cloud_id") or "") != cloud_id:
                    return {"events": 0}
                existing = {(canonical_device_id(item.get("device_id")), str(item.get("id") or ""))
                            for item in data["events"] if isinstance(item, dict)}
                added = 0
                for log in logs:
                    if not isinstance(log, dict): continue
                    event_id = str(log.get("id") or "")
                    if not event_id or (did, event_id) in existing: continue
                    data["events"].append({"id": event_id, "device_id": did, "timestamp": log.get("date"),
                                           "action": log.get("action"),
                                           "action_name": ACTION_NAMES.get(log.get("action"), f"Azione {log.get('action')}"),
                                           "trigger": log.get("trigger"), "auth_id": log.get("authId"),
                                           "code_id": log.get("codeId"), "person": log.get("name") or "Origine non identificata",
                                           "state": log.get("state"), "transport": "web_api"})
                    existing.add((did, event_id)); added += 1
                if added:
                    data["events"].sort(key=event_time_seconds, reverse=True)
                    data["events"] = data["events"][:1000]
                    self.store.save(data)
                return {"events": added}
    def sync_cloud(self) -> dict[str, Any]:
        with self._cloud_sync_lock:
            return self._sync_cloud()
    def _sync_cloud(self) -> dict[str, Any]:
        locks = self._api("/smartlock")
        data = self.store.load(); count = 0; current_cloud_ids: set[str] = set()
        for item in locks if isinstance(locks, list) else []:
            cloud_id = str(item.get("smartlockId") or "")
            did = canonical_device_id(cloud_id, cloud_id=True)
            if not did: continue
            current_cloud_ids.add(cloud_id)
            legacy = data["devices"].pop(cloud_id, None) if cloud_id != did else None
            row = data["devices"].setdefault(did, legacy or {"device_id": did, "enabled": False, "read_only": True, "state": {}, "capabilities": list(COMMAND_TOPICS)})
            row["device_id"] = did
            row.update({"name": item.get("name") or row.get("name") or f"Nuki {did}", "device_class": "lock", "web": True, "cloud_id": cloud_id, "device_type": item.get("type")}); count += 1
            try:
                auths = self._api(f"/smartlock/{urllib.parse.quote(cloud_id)}/auth")
                fetched_auths = {}
                for auth in auths if isinstance(auths, list) else []:
                    aid = str(auth.get("authId") or auth.get("id") or "")
                    if aid:
                        fetched_auths[f"{did}:{aid}"] = {"auth_id": aid, "web_id": str(auth.get("id") or ""), "device_id": did, "name": auth.get("name") or aid, "type": auth.get("type"), "enabled": auth.get("enabled", True), "allowed_from": auth.get("allowedFromDate"), "allowed_until": auth.get("allowedUntilDate"), "remote_allowed": auth.get("remoteAllowed"), "account_user_id": auth.get("accountUserId")}
                if isinstance(auths, list):
                    for aid, authorization in list(data["authorizations"].items()):
                        if canonical_device_id(authorization.get("device_id")) == did:
                            del data["authorizations"][aid]
                    data["authorizations"].update(fetched_auths)
                    row["authorizations_synced_at"] = time.time()
                    row["authorizations_status"] = "ok"
                else:
                    row["authorizations_status"] = "error"
            except (ValueError, OSError):
                row["authorizations_status"] = "error"
            try:
                logs = self._api(f"/smartlock/{urllib.parse.quote(cloud_id)}/log?limit=50")
                for log in logs if isinstance(logs, list) else []:
                    event_id = str(log.get("id") or "")
                    if not event_id:
                        continue
                    existing = next((x for x in data["events"] if x.get("id") == event_id and canonical_device_id(x.get("device_id")) == did), None)
                    if existing:
                        existing["transport"] = "web_api"
                    else:
                        data["events"].append({"id": event_id, "device_id": did, "timestamp": log.get("date"), "action": log.get("action"), "action_name": ACTION_NAMES.get(log.get("action"), f"Azione {log.get('action')}"), "trigger": log.get("trigger"), "auth_id": log.get("authId"), "code_id": log.get("codeId"), "person": log.get("name") or "Origine non identificata", "state": log.get("state"), "transport": "web_api"})
            except ValueError: pass
        for did, row in list(data["devices"].items()):
            if row.get("web") and str(row.get("cloud_id") or "") not in current_cloud_ids:
                if row.get("state") or row.get("last_seen"):
                    row.pop("web", None); row.pop("cloud_id", None); row.pop("device_type", None)
                else:
                    del data["devices"][did]
        with self.store._lock:
            current = self.store.load()
            data["config"] = current["config"]
            for did, live_row in current["devices"].items():
                if did not in data["devices"]:
                    if live_row.get("state") or live_row.get("last_seen"):
                        data["devices"][did] = live_row
                    continue
                for key in ("state", "last_seen", "last_event", "mqtt_access_events", "enabled", "read_only"):
                    if key in live_row:
                        data["devices"][did][key] = deepcopy(live_row[key])
            unique_events = {}
            for event in sorted(data["events"] + current["events"], key=event_time_seconds, reverse=True):
                key = (canonical_device_id(event.get("device_id")), str(event.get("id") or ""))
                unique_events.setdefault(key, event)
            data["events"] = list(unique_events.values())[:1000]
            self.store.save(data)
        return {"devices": count, "authorizations": len(data["authorizations"]), "events": len(data["events"])}
    def snapshot(self) -> dict[str, Any]:
        data = self.store.load(); status = self.mqtt.status()
        devices = self.store.rows()
        cloud_only = [row for row in self.store.rows(include_cloud_only=True) if not (row.get("state") or {}).get("attributes")]
        return {"status": {"configured": bool(data["config"].get("enabled")), "mqtt_connected": bool(self._started and status.connected), "mqtt_error": status.last_error if self._started else None, "cloud_enabled": bool(data["config"].get("cloud_enabled")), "token_configured": bool(self.store.token()), "bridge_enabled": bool(data["config"].get("bridge_enabled")), "bridge_token_configured": bool(self.store.bridge_token()), "devices": len(devices), "cloud_only": len(cloud_only)}, "config": data["config"], "devices": devices, "cloud_only": cloud_only, "authorizations": self.store.public_authorizations(data), "access_directory": self.store.access_directory(), "events": self.store.access_events(), "rules": data["rules"]}
