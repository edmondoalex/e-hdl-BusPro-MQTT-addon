from __future__ import annotations

from copy import deepcopy
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


ACTION_NAMES = {1: "Sblocco", 2: "Blocco", 3: "Apertura", 4: "Lock 'n' Go", 5: "Lock 'n' Go con apertura", 240: "Porta aperta", 241: "Porta chiusa", 242: "Sensore porta bloccato"}
TRIGGER_NAMES = {0: "Sistema", 1: "Manuale", 2: "Pulsante", 3: "Fob", 4: "Tastierino", 5: "Auto Unlock", 6: "Web API", 7: "App", 8: "HomeKit", 9: "MQTT", 10: "Matter"}
COMMAND_TOPICS = {"unlock": "unlock", "lock": "lock", "unlatch": "unlatch", "lockngo": "lockNgo", "lockngo_unlatch": "lockNgoUnlatch"}
LOCK_STATES = {0: "uncalibrated", 1: "locked", 2: "unlocking", 3: "unlocked", 4: "locking", 5: "unlatched", 6: "unlocked", 7: "unlatching", 254: "motor_blocked", 255: "undefined"}


class NukiStore:
    def __init__(self, path: str):
        self.path = path
        self.secret_path = path + ".credentials"
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {"schema_version": 1, "config": {"enabled": False, "mqtt_prefix": "nuki", "cloud_enabled": False}, "devices": {}, "authorizations": {}, "events": [], "rules": []}

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
        for key in ("enabled", "cloud_enabled"):
            if key in payload: config[key] = bool(payload[key])
        if "mqtt_prefix" in payload:
            prefix = str(payload["mqtt_prefix"] or "nuki").strip().strip("/")
            if not prefix or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in prefix): raise ValueError("Prefisso MQTT non valido")
            config["mqtt_prefix"] = prefix
        if payload.get("api_token"): self.set_token(str(payload["api_token"]))
        return self.save(data)

    def update_device(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self.load(); row = data["devices"].get(device_id)
        if not isinstance(row, dict): raise KeyError(device_id)
        for key in ("enabled", "read_only"):
            if key in payload: row[key] = bool(payload[key])
        self.save(data); return deepcopy(row)

    def ingest(self, topic: str, payload: str) -> dict[str, Any] | None:
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
                auth = data["authorizations"].get(str(nums[2])) or {}
                event = {"id": f"{int(time.time()*1000)}-{device_id}", "device_id": device_id, "timestamp": int(time.time()), "action": nums[0], "action_name": ACTION_NAMES.get(nums[0], f"Azione {nums[0]}"), "trigger": nums[1], "trigger_name": TRIGGER_NAMES.get(nums[1], f"Origine {nums[1]}"), "auth_id": nums[2], "code_id": nums[3], "detail": nums[4], "person": auth.get("name") or (f"Autorizzazione {nums[2]}" if nums[2] else "Origine non identificata")}
                data["events"] = ([event] + data["events"])[:1000]
                row["last_event"] = event
        self.save(data); return deepcopy(row)

    def rows(self) -> list[dict[str, Any]]:
        now = time.time(); result = []
        for row in self.load()["devices"].values():
            state = row.get("state") or {}; raw_state = state.get("state") or state.get("lockState") or "unknown"
            lock_state = LOCK_STATES.get(int(raw_state), raw_state) if str(raw_state).isdigit() else raw_state
            recent = now - float(row.get("last_seen") or 0) < 180
            available = str(state.get("connected") or "").strip().lower() == "true" or recent
            result.append({**deepcopy(row), "source": "nuki", "native_type": "smart_lock", "native_id": row.get("device_id"), "available": available, "stale": not available, "state": {"state": lock_state, "attributes": deepcopy(state)}})
        return result

    def catalog(self) -> list[dict[str, Any]]: return [row for row in self.rows() if row.get("enabled")]
    def organization_catalog(self) -> list[dict[str, Any]]: return [{"device_id": x["device_id"], "name": x["name"], "device_class": "lock"} for x in self.rows()]


class NukiManager:
    def __init__(self, path: str, mqtt: Any):
        self.store, self.mqtt = NukiStore(path), mqtt
        self._started = False
    def start(self) -> None:
        if not self.store.load()["config"].get("enabled"):
            self._started = False
            return
        prefix = self.store.load()["config"].get("mqtt_prefix") or "nuki"
        self.mqtt.set_message_handler(lambda topic, payload, retained: self.store.ingest(topic, payload))
        self.mqtt.subscribe(f"{prefix}/#", qos=1); self.mqtt.connect()
        self._started = True
    def stop(self) -> None:
        if self._started:
            prefix = self.store.load()["config"].get("mqtt_prefix") or "nuki"
            self.mqtt.unsubscribe(f"{prefix}/#")
            self.mqtt.disconnect()
        self._started = False
    def configure(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.stop()
        self.store.configure(payload)
        self.start()
        return self.snapshot()
    def reset(self) -> dict[str, Any]:
        self.stop()
        for path in (self.store.path, self.store.path + ".bak", self.store.secret_path):
            try: os.unlink(path)
            except FileNotFoundError: pass
        return self.snapshot()
    def command(self, device_id: str, action: str) -> dict[str, Any]:
        row = next((x for x in self.store.rows() if x["device_id"] == device_id), None)
        if not row: raise KeyError(device_id)
        if row.get("read_only", True): raise ValueError("Comandi Nuki disabilitati")
        suffix = COMMAND_TOPICS.get(action)
        if not suffix: raise ValueError("Comando Nuki non supportato")
        prefix = self.store.load()["config"].get("mqtt_prefix") or "nuki"
        self.mqtt.publish(f"{prefix}/{device_id}/{suffix}", "true", qos=1)
        return {"ok": True, "accepted": True, "confirmed": False, "source": "nuki"}
    def _api(self, path: str) -> Any:
        token = self.store.token()
        if not token: raise ValueError("Token Nuki Web API non configurato")
        req = urllib.request.Request("https://api.nuki.io" + path, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as response: return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc: raise ValueError(f"Nuki Web API HTTP {exc.code}") from exc
    def sync_cloud(self) -> dict[str, Any]:
        locks = self._api("/smartlock")
        data = self.store.load(); count = 0
        for item in locks if isinstance(locks, list) else []:
            did = str(item.get("smartlockId") or "");
            if not did: continue
            row = data["devices"].setdefault(did, {"device_id": did, "enabled": False, "read_only": True, "state": {}, "capabilities": list(COMMAND_TOPICS)})
            row.update({"name": item.get("name") or f"Nuki {did}", "device_class": "lock", "web": True, "device_type": item.get("type")}); count += 1
            try:
                auths = self._api(f"/smartlock/{urllib.parse.quote(did)}/auth")
                for auth in auths if isinstance(auths, list) else []:
                    aid = str(auth.get("id") or auth.get("authId") or "")
                    if aid: data["authorizations"][aid] = {"auth_id": aid, "name": auth.get("name") or aid, "enabled": auth.get("enabled", True), "allowed_from": auth.get("allowedFromDate"), "allowed_until": auth.get("allowedUntilDate")}
            except ValueError: pass
            try:
                logs = self._api(f"/smartlock/{urllib.parse.quote(did)}/log?limit=50")
                for log in logs if isinstance(logs, list) else []:
                    event_id = str(log.get("id") or "")
                    if event_id and not any(x.get("id") == event_id for x in data["events"]):
                        data["events"].append({"id": event_id, "device_id": did, "timestamp": log.get("date"), "action": log.get("action"), "action_name": ACTION_NAMES.get(log.get("action"), f"Azione {log.get('action')}"), "trigger": log.get("trigger"), "auth_id": log.get("authId"), "person": log.get("name") or "Origine non identificata", "state": log.get("state")})
            except ValueError: pass
        data["events"] = sorted(data["events"], key=lambda x: str(x.get("timestamp") or ""), reverse=True)[:1000]
        self.store.save(data); return {"devices": count, "authorizations": len(data["authorizations"]), "events": len(data["events"])}
    def snapshot(self) -> dict[str, Any]:
        data = self.store.load(); status = self.mqtt.status()
        return {"status": {"configured": bool(data["config"].get("enabled")), "mqtt_connected": bool(self._started and status.connected), "mqtt_error": status.last_error if self._started else None, "cloud_enabled": bool(data["config"].get("cloud_enabled")), "token_configured": bool(self.store.token()), "devices": len(data["devices"])}, "config": data["config"], "devices": self.store.rows(), "authorizations": list(data["authorizations"].values()), "events": data["events"][:200], "rules": data["rules"]}
