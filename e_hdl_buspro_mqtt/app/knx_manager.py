from __future__ import annotations

import asyncio
import json
import os
import tempfile
import threading
import time
from copy import deepcopy
from hashlib import sha256
from typing import Any


SCHEMA_VERSION = 1
SUPPORTED_DOMAINS = {"binary_sensor", "button", "climate", "cover", "fan", "light", "number", "scene", "select", "sensor", "switch"}
COMMAND_CAPABILITIES = {
    "light": ["on", "off"],
    "switch": ["on", "off"],
    "cover": ["open", "close", "stop"],
    "scene": ["execute"],
    "button": ["execute"],
    "fan": ["on", "off"],
    "climate": ["temperature"],
    "number": ["level"],
    "select": ["mode"],
}


class KnxNotConfigured(RuntimeError):
    pass


def _device_class(domain: str, state: dict[str, Any]) -> str:
    attrs = state.get("attributes") if isinstance(state, dict) else {}
    attrs = attrs if isinstance(attrs, dict) else {}
    native = str(attrs.get("device_class") or "").strip().lower()
    if domain == "light":
        modes = attrs.get("supported_color_modes") or []
        return "dimmer" if attrs.get("brightness") is not None or any(str(x) != "onoff" for x in modes) else "light"
    if domain == "cover":
        return {"garage": "garage_door", "gate": "gate", "awning": "awning", "shutter": "shutter"}.get(native, "cover")
    if domain == "climate":
        return "thermostat"
    if domain == "scene":
        return "scenario"
    if domain == "binary_sensor":
        return "presence" if native in {"motion", "occupancy", "presence"} else "binary_sensor"
    if domain == "sensor":
        return {
            "temperature": "temperature_sensor", "humidity": "humidity_sensor",
            "illuminance": "illuminance_sensor", "carbon_dioxide": "environment_sensor",
            "volatile_organic_compounds": "environment_sensor",
        }.get(native, "sensor")
    return domain


def _capabilities(domain: str, state: dict[str, Any]) -> list[str]:
    caps = list(COMMAND_CAPABILITIES.get(domain, []))
    attrs = state.get("attributes") if isinstance(state, dict) else {}
    attrs = attrs if isinstance(attrs, dict) else {}
    if domain == "light" and (attrs.get("brightness") is not None or attrs.get("supported_color_modes")):
        caps.append("level")
    if domain == "cover":
        try:
            if int(attrs.get("supported_features") or 0) & 4:
                caps.append("position")
        except (TypeError, ValueError):
            pass
    return list(dict.fromkeys(caps))


class KnxCatalogStore:
    """Persistent KNX-to-Ekonex identity map.  No HA secrets are stored here."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "devices": {}, "last_sync": None, "project": {}}

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
                    return self.empty()
                data.setdefault("devices", {})
                data.setdefault("project", {})
                return data
            except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
                return self.empty()

    def save(self, data: dict[str, Any]) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".knx-manager-", suffix=".json", dir=os.path.dirname(self.path) or ".")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def sync(self, registry: list[dict[str, Any]], states: dict[str, dict[str, Any]], project: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            devices = data.setdefault("devices", {})
            seen: set[str] = set()
            added = updated = 0
            for entry in registry:
                if str(entry.get("platform") or "").lower() != "knx":
                    continue
                entity_id = str(entry.get("entity_id") or "").strip().lower()
                domain = entity_id.partition(".")[0]
                if not entity_id or domain not in SUPPORTED_DOMAINS:
                    continue
                registry_id = str(entry.get("id") or entry.get("unique_id") or entity_id).strip()
                stable_id = "ha-" + sha256(registry_id.encode("utf-8")).hexdigest()[:20]
                seen.add(stable_id)
                state = states.get(entity_id) or {}
                attrs = state.get("attributes") if isinstance(state, dict) else {}
                attrs = attrs if isinstance(attrs, dict) else {}
                name = str(entry.get("name") or entry.get("original_name") or attrs.get("friendly_name") or entity_id).strip()
                old = devices.get(stable_id) or {}
                row = {
                    **old,
                    "device_id": stable_id,
                    "entity_id": entity_id,
                    "registry_id": registry_id,
                    "name": name,
                    "domain": domain,
                    "device_class": _device_class(domain, state),
                    "capabilities": _capabilities(domain, state),
                    "enabled": bool(old.get("enabled", False)),
                    "read_only": bool(old.get("read_only", True)),
                    "orphaned": False,
                    "last_seen": time.time(),
                }
                if not old:
                    added += 1
                elif row != old:
                    updated += 1
                devices[stable_id] = row
            for stable_id, row in devices.items():
                if stable_id not in seen:
                    row["orphaned"] = True
            if project is not None:
                data["project"] = deepcopy(project)
            data["last_sync"] = time.time()
            self.save(data)
            return {"added": added, "updated": updated, "total": len(devices), "orphaned": sum(bool(x.get("orphaned")) for x in devices.values())}

    def update(self, device_id: str, *, enabled: bool | None = None, read_only: bool | None = None) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            row = (data.get("devices") or {}).get(device_id)
            if not isinstance(row, dict):
                raise KeyError(device_id)
            if enabled is not None:
                row["enabled"] = bool(enabled)
            if read_only is not None:
                row["read_only"] = bool(read_only)
            self.save(data)
            return deepcopy(row)

    def catalog(self, states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in (self.load().get("devices") or {}).values():
            if not isinstance(row, dict) or not row.get("enabled"):
                continue
            state = states.get(str(row.get("entity_id") or "")) or {}
            raw_state = state.get("state") if isinstance(state, dict) else None
            available = raw_state not in {None, "unavailable", "unknown"} and not row.get("orphaned")
            rows.append({
                "device_id": row.get("device_id"), "name": row.get("name"),
                "device_class": row.get("device_class"), "native_type": row.get("domain"),
                "native_id": row.get("entity_id"), "home_assistant_entity_id": row.get("entity_id"),
                "capabilities": list(row.get("capabilities") or []),
                "read_only": bool(row.get("read_only", True)), "available": available,
                "stale": not available, "state": deepcopy(state),
            })
        return rows

    def organization_catalog(self) -> list[dict[str, Any]]:
        return [
            {"device_id": row.get("device_id"), "name": row.get("name") or row.get("device_id"), "device_class": row.get("device_class") or row.get("domain") or "device"}
            for row in (self.load().get("devices") or {}).values()
            if isinstance(row, dict) and not row.get("orphaned")
        ]


class HomeAssistantWebSocket:
    def __init__(self, token: str, url: str = "ws://supervisor/core/api/websocket"):
        self.token = token
        self.url = url

    async def command(self, command_type: str, **payload: Any) -> Any:
        import websockets

        async with websockets.connect(
            self.url,
            open_timeout=8,
            close_timeout=2,
            max_size=16 * 1024 * 1024,
        ) as ws:
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
            if hello.get("type") != "auth_required":
                raise RuntimeError("unexpected Home Assistant WebSocket greeting")
            await ws.send(json.dumps({"type": "auth", "access_token": self.token}))
            auth = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
            if auth.get("type") != "auth_ok":
                raise PermissionError("Home Assistant WebSocket authentication failed")
            message = {"id": 1, "type": command_type, **payload}
            await ws.send(json.dumps(message, ensure_ascii=False))
            while True:
                reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                if reply.get("id") != 1:
                    continue
                if not reply.get("success"):
                    error = reply.get("error") or {}
                    raise RuntimeError(str(error.get("message") or error.get("code") or "Home Assistant command failed"))
                return reply.get("result")


class KnxManager:
    def __init__(self, path: str, token: str):
        self.store = KnxCatalogStore(path)
        self.ws = HomeAssistantWebSocket(token) if token else None
        self.last_error = ""
        self.base_data: dict[str, Any] = {}

    async def sync(self, states: list[dict[str, Any]]) -> dict[str, Any]:
        if self.ws is None:
            raise RuntimeError("SUPERVISOR_TOKEN missing")
        try:
            entries = await self.ws.command("config_entries/get", domain="knx")
            if not isinstance(entries, list) or not entries:
                raise KnxNotConfigured("KNX integration is not configured")
            registry = await self.ws.command("config/entity_registry/list")
            base_data = await self.ws.command("knx/get_base_data")
            project = await self.ws.command("knx/get_knx_project") if base_data.get("project_info") else {}
            by_entity = {str(x.get("entity_id") or "").lower(): x for x in states if isinstance(x, dict)}
            result = self.store.sync(registry if isinstance(registry, list) else [], by_entity, project if isinstance(project, dict) else {})
            self.base_data = base_data if isinstance(base_data, dict) else {}
            self.last_error = ""
            return result
        except Exception as exc:
            self.last_error = str(exc)
            raise

    def status(self) -> dict[str, Any]:
        data = self.store.load()
        devices = data.get("devices") or {}
        conn = self.base_data.get("connection_info") if isinstance(self.base_data, dict) else {}
        return {
            "available": self.ws is not None,
            "connected": bool((conn or {}).get("connected")),
            "xknx_version": (conn or {}).get("version"),
            "current_address": (conn or {}).get("current_address"),
            "project": self.base_data.get("project_info") or data.get("project") or {},
            "devices": len(devices), "enabled": sum(bool(x.get("enabled")) for x in devices.values()),
            "last_sync": data.get("last_sync"), "error": self.last_error,
            "setup_required": self.last_error == "KNX integration is not configured",
        }
