from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import os
import shutil
import tempfile
import threading
import time
from typing import Any
import urllib.error
import urllib.request
import uuid


BUILDER_APP_SLUG = "5c53de3b_esphome"


def _domain_profile(entity_id: str, attributes: dict[str, Any]) -> tuple[str, list[str]]:
    domain = entity_id.split(".", 1)[0]
    native = str(attributes.get("device_class") or "").strip().lower()
    if domain == "light":
        dimmable = bool(attributes.get("brightness") is not None or int(attributes.get("supported_features") or 0) & 1)
        return ("dimmer" if dimmable else "light", ["on", "off", *( ["level"] if dimmable else [])])
    if domain == "switch":
        return "switch", ["on", "off"]
    if domain == "fan":
        return "fan", ["on", "off"]
    if domain == "cover":
        return "cover", ["open", "close", "stop"]
    if domain == "climate":
        return "thermostat", ["temperature"]
    if domain == "number":
        return "sensor", ["level"]
    if domain == "select":
        return "switch", ["mode"]
    if domain in {"button", "scene"}:
        return "scenario", ["execute"]
    if domain == "binary_sensor":
        return "binary_sensor", []
    if domain == "sensor":
        return {
            "temperature": "temperature_sensor",
            "humidity": "humidity_sensor",
            "illuminance": "illuminance_sensor",
        }.get(native, "sensor"), []
    return domain or "sensor", []


class EspHomeCatalogStore:
    """Small persistent policy/catalog layer; YAML remains owned by Device Builder."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {"schema_version": 1, "entities": {}, "last_sync": None}

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict) or data.get("schema_version") != 1:
                    raise ValueError("unsupported schema")
            except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
                return self.empty()
            out = self.empty()
            out["last_sync"] = data.get("last_sync")
            out["entities"] = data.get("entities") if isinstance(data.get("entities"), dict) else {}
            return out

    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            folder = os.path.dirname(self.path) or "."
            os.makedirs(folder, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".esphome-manager-", suffix=".json", dir=folder)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                if os.path.isfile(self.path):
                    shutil.copy2(self.path, self.path + ".bak")
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        return deepcopy(data)

    def sync(self, registry: list[dict[str, Any]], states: list[dict[str, Any]]) -> dict[str, Any]:
        state_map = {str(row.get("entity_id") or "").lower(): row for row in states if isinstance(row, dict)}
        data = self.load()
        previous = data.get("entities") or {}
        entities: dict[str, dict[str, Any]] = {}
        for entry in registry:
            if not isinstance(entry, dict) or str(entry.get("platform") or "").lower() != "esphome":
                continue
            entity_id = str(entry.get("entity_id") or "").strip().lower()
            if not entity_id or entry.get("disabled_by"):
                continue
            state = state_map.get(entity_id) or {}
            attrs = state.get("attributes") if isinstance(state.get("attributes"), dict) else {}
            old = previous.get(entity_id) if isinstance(previous.get(entity_id), dict) else {}
            device_class, capabilities = _domain_profile(entity_id, attrs)
            entities[entity_id] = {
                "device_id": entity_id,
                "entity_id": entity_id,
                "config_entry_id": str(entry.get("config_entry_id") or ""),
                "registry_device_id": str(entry.get("device_id") or ""),
                "name": str(entry.get("name") or entry.get("original_name") or attrs.get("friendly_name") or entity_id),
                "domain": entity_id.split(".", 1)[0],
                "device_class": device_class,
                "capabilities": capabilities,
                "enabled": bool(old.get("enabled", False)),
                "read_only": bool(old.get("read_only", True)),
                "orphaned": False,
            }
        for entity_id, old in previous.items():
            if entity_id not in entities and isinstance(old, dict):
                entities[entity_id] = {**old, "orphaned": True, "enabled": False, "read_only": True}
        data = {"schema_version": 1, "entities": entities, "last_sync": int(time.time())}
        return self.save(data)

    def update(self, entity_id: str, *, enabled: bool | None = None, read_only: bool | None = None) -> dict[str, Any]:
        data = self.load()
        row = (data.get("entities") or {}).get(entity_id)
        if not isinstance(row, dict):
            raise KeyError(entity_id)
        if enabled is not None:
            row["enabled"] = bool(enabled)
        if read_only is not None:
            row["read_only"] = bool(read_only)
        return self.save(data)["entities"][entity_id]

    def rows(self, states: dict[str, Any]) -> list[dict[str, Any]]:
        result = []
        for row in (self.load().get("entities") or {}).values():
            if not isinstance(row, dict):
                continue
            entity_id = str(row.get("entity_id") or "")
            state = deepcopy(states.get(entity_id))
            raw = state.get("state") if isinstance(state, dict) else None
            available = raw not in {None, "unknown", "unavailable"} and not row.get("orphaned")
            result.append({
                **deepcopy(row),
                "native_type": row.get("domain"),
                "native_id": entity_id,
                "home_assistant_entity_id": entity_id,
                "available": available,
                "stale": not available,
                "state": state,
            })
        return result

    def catalog(self, states: dict[str, Any]) -> list[dict[str, Any]]:
        return [row for row in self.rows(states) if row.get("enabled")]

    def organization_catalog(self) -> list[dict[str, Any]]:
        return [
            {"device_id": row.get("device_id"), "name": row.get("name"), "device_class": row.get("device_class")}
            for row in (self.load().get("entities") or {}).values()
            if isinstance(row, dict) and not row.get("orphaned")
        ]


class EspHomeManager:
    def __init__(self, path: str, token: str, builder_url: str = "ws://127.0.0.1:65193/ws"):
        self.store = EspHomeCatalogStore(path)
        self.token = token
        self.builder_url = builder_url

    async def command(self, command: str, args: dict[str, Any] | None = None, *, timeout: int = 30, stream: bool = False) -> Any:
        import websockets

        message_id = uuid.uuid4().hex
        async with websockets.connect(self.builder_url, open_timeout=8, close_timeout=2, max_size=32 * 1024 * 1024) as ws:
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
            if hello.get("requires_auth"):
                raise RuntimeError("Il Builder richiede autenticazione diretta non configurata")
            await ws.send(json.dumps({"command": command, "message_id": message_id, "args": args or {}}, ensure_ascii=False))
            events: list[dict[str, Any]] = []
            while True:
                try:
                    reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                except asyncio.TimeoutError:
                    if stream:
                        return {"result": None, "events": events, "timed_out": True}
                    raise
                if reply.get("message_id") != message_id:
                    continue
                if reply.get("error_code"):
                    raise RuntimeError(str(reply.get("details") or reply.get("error_code")))
                if "result" in reply:
                    return {"result": reply.get("result"), "events": events} if stream else reply.get("result")
                if stream and reply.get("event"):
                    events.append({"event": reply.get("event"), "data": reply.get("data")})
                    if reply.get("event") == "result":
                        return {"result": reply.get("data"), "events": events}

    async def devices(self) -> dict[str, Any]:
        result = await self.command("devices/list")
        return result if isinstance(result, dict) else {"configured": [], "importable": []}

    async def status(self) -> dict[str, Any]:
        devices = await self.devices()
        configured = devices.get("configured") or []
        app = await asyncio.to_thread(self._supervisor, "GET", f"/addons/{BUILDER_APP_SLUG}/info")
        info = app.get("data") if isinstance(app, dict) and isinstance(app.get("data"), dict) else app
        info = info if isinstance(info, dict) else {}
        return {
            "available": True,
            "running": str(info.get("state") or "").lower() == "started",
            "version": str(info.get("version") or ""),
            "latest_version": str(info.get("version_latest") or info.get("version") or ""),
            "builder_update_available": bool(info.get("update_available")),
            "device_updates": sum(bool(row.get("update_available")) for row in configured if isinstance(row, dict)),
            "devices": len(configured),
        }

    def _supervisor(self, method: str, path: str, timeout: int = 120) -> Any:
        if not self.token:
            raise RuntimeError("Servizio di sistema non disponibile")
        req = urllib.request.Request(
            "http://supervisor/" + path.lstrip("/"),
            method=method,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read()
            return json.loads(body.decode("utf-8")) if body else {"result": "ok"}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(detail or str(exc)) from exc

    async def update_builder(self) -> Any:
        return await asyncio.to_thread(self._supervisor, "POST", f"/addons/{BUILDER_APP_SLUG}/update", 900)
