from __future__ import annotations

import json
import io
import os
import shutil
import tempfile
import threading
import time
import urllib.request
import zipfile
from copy import deepcopy
from hashlib import sha256
from typing import Any

from .knx_manager import SUPPORTED_DOMAINS, HomeAssistantWebSocket, _capabilities, _device_class


SCHEMA_VERSION = 1
INTEGRATIONS = {
    "myhome_scs": {
        "domain": "myhome",
        "name": "MyHOME SCS",
        "transport": "OpenWebNet locale",
        "official": False,
    },
    "home_plus_control": {
        "domain": "netatmo",
        "name": "Home + Control / Netatmo",
        "transport": "Netatmo cloud",
        "official": True,
    },
}

MYHOME_RELEASE = "0.9.4"
MYHOME_ARCHIVE_URL = "https://codeload.github.com/OpenWebNet-HA/MyHOME/zip/refs/tags/0.9.4"
MYHOME_ARCHIVE_SHA256 = "058cc6bcbae919a5b3972e7c05ca41b181ad635595e8b42bdd9163a348f60e47"


class MyHomeComponentInstaller:
    """Install the pinned, unmodified AGPL MyHOME component in HA config."""

    def __init__(self, config_dir: str = "/config"):
        self.config_dir = config_dir
        self.target = os.path.join(config_dir, "custom_components", "myhome")

    def status(self) -> dict[str, Any]:
        manifest_path = os.path.join(self.target, "manifest.json")
        manifest: dict[str, Any] = {}
        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            manifest = loaded if isinstance(loaded, dict) else {}
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            pass
        return {
            "installed": bool(manifest),
            "installed_version": str(manifest.get("version") or "") if manifest else "",
            "managed_version": MYHOME_RELEASE,
            "domain": str(manifest.get("domain") or "") if manifest else "",
            "restart_required": False,
            "license": "AGPL-3.0",
            "source": "https://github.com/OpenWebNet-HA/MyHOME",
        }

    def install(self) -> dict[str, Any]:
        archive_limit = 20 * 1024 * 1024
        request = urllib.request.Request(MYHOME_ARCHIVE_URL, headers={"User-Agent": "e-Control-Hub"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read(archive_limit + 1)
        if len(content) > archive_limit:
            raise RuntimeError("MyHOME package exceeds the allowed size")
        digest = sha256(content).hexdigest()
        if digest != MYHOME_ARCHIVE_SHA256:
            raise RuntimeError("MyHOME package integrity check failed")
        custom_root = os.path.join(self.config_dir, "custom_components")
        os.makedirs(custom_root, exist_ok=True)
        staging = tempfile.mkdtemp(prefix=".econtrol-myhome-", dir=custom_root)
        backup = ""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members = [
                    item for item in archive.infolist()
                    if "/custom_components/myhome/" in item.filename and not item.is_dir()
                ]
                if not members:
                    raise RuntimeError("MyHOME component not found in verified package")
                component_dir = os.path.join(staging, "myhome")
                os.makedirs(component_dir, exist_ok=True)
                marker = "/custom_components/myhome/"
                for item in members:
                    relative = item.filename.split(marker, 1)[1].replace("\\", "/")
                    parts = [part for part in relative.split("/") if part]
                    if not parts or any(part in {".", ".."} for part in parts):
                        raise RuntimeError("Unsafe path in MyHOME package")
                    destination = os.path.abspath(os.path.join(component_dir, *parts))
                    if os.path.commonpath([destination, os.path.abspath(component_dir)]) != os.path.abspath(component_dir):
                        raise RuntimeError("Unsafe path in MyHOME package")
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    with archive.open(item) as source_handle, open(destination, "wb") as target_handle:
                        shutil.copyfileobj(source_handle, target_handle)
            manifest_path = os.path.join(component_dir, "manifest.json")
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
            if manifest.get("domain") != "myhome":
                raise RuntimeError("Verified package contains an invalid MyHOME manifest")
            if os.path.isdir(self.target):
                backup_root = os.path.join(custom_root, ".econtrol-backups")
                os.makedirs(backup_root, exist_ok=True)
                backup = os.path.join(backup_root, f"myhome-{int(time.time())}")
                os.replace(self.target, backup)
            os.replace(component_dir, self.target)
        except Exception:
            if backup and not os.path.exists(self.target) and os.path.isdir(backup):
                os.replace(backup, self.target)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        result = self.status()
        result.update({"installed": True, "restart_required": True, "backup": backup})
        return result


class BticinoCatalogStore:
    """Persistent, opt-in catalog for the two independent BTicino transports."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "integrations": {
                source: {"devices": {}, "last_sync": None}
                for source in INTEGRATIONS
            },
        }

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
                    return self.empty()
            except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
                return self.empty()
            integrations = data.setdefault("integrations", {})
            for source in INTEGRATIONS:
                integrations.setdefault(source, {"devices": {}, "last_sync": None})
                integrations[source].setdefault("devices", {})
            return data

    def save(self, data: dict[str, Any]) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".bticino-manager-", suffix=".json", dir=os.path.dirname(self.path) or ".")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def sync(
        self,
        source: str,
        registry: list[dict[str, Any]],
        states: dict[str, dict[str, Any]],
        device_registry: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if source not in INTEGRATIONS:
            raise ValueError("unsupported BTicino integration")
        domain_name = INTEGRATIONS[source]["domain"]
        devices_by_id = {
            str(item.get("id") or ""): item
            for item in (device_registry or [])
            if isinstance(item, dict)
        }
        with self._lock:
            data = self.load()
            bucket = data["integrations"][source]
            devices = bucket.setdefault("devices", {})
            seen: set[str] = set()
            added = updated = 0
            for entry in registry:
                if str(entry.get("platform") or "").lower() != domain_name:
                    continue
                entity_id = str(entry.get("entity_id") or "").strip().lower()
                domain = entity_id.partition(".")[0]
                if not entity_id or domain not in SUPPORTED_DOMAINS:
                    continue
                registry_id = str(entry.get("id") or entry.get("unique_id") or entity_id).strip()
                stable_id = "ha-" + sha256(f"{source}:{registry_id}".encode("utf-8")).hexdigest()[:20]
                seen.add(stable_id)
                state = states.get(entity_id) or {}
                attrs = state.get("attributes") if isinstance(state, dict) else {}
                attrs = attrs if isinstance(attrs, dict) else {}
                device = devices_by_id.get(str(entry.get("device_id") or ""), {})
                manufacturer = str(device.get("manufacturer") or attrs.get("manufacturer") or "").strip()
                model = str(device.get("model") or attrs.get("model") or "").strip()
                name = str(entry.get("name") or entry.get("original_name") or attrs.get("friendly_name") or entity_id).strip()
                old = devices.get(stable_id) or {}
                row = {
                    **old,
                    "device_id": stable_id,
                    "entity_id": entity_id,
                    "registry_id": registry_id,
                    "ha_device_id": str(entry.get("device_id") or ""),
                    "name": name,
                    "domain": domain,
                    "device_class": _device_class(domain, state),
                    "capabilities": _capabilities(domain, state),
                    "manufacturer": manufacturer,
                    "model": model,
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
            bucket["last_sync"] = time.time()
            self.save(data)
            return {
                "added": added,
                "updated": updated,
                "total": len(devices),
                "enabled": sum(bool(item.get("enabled")) for item in devices.values()),
                "orphaned": sum(bool(item.get("orphaned")) for item in devices.values()),
            }

    def update(self, source: str, device_id: str, *, enabled: bool | None = None, read_only: bool | None = None) -> dict[str, Any]:
        if source not in INTEGRATIONS:
            raise KeyError(source)
        with self._lock:
            data = self.load()
            row = data["integrations"][source]["devices"].get(device_id)
            if not isinstance(row, dict):
                raise KeyError(device_id)
            if enabled is not None:
                row["enabled"] = bool(enabled)
            if read_only is not None:
                row["read_only"] = bool(read_only)
            self.save(data)
            return deepcopy(row)

    def sync_direct_netatmo(self, modules: list[dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            bucket = data["integrations"]["home_plus_control"]
            devices = bucket.setdefault("devices", {})
            seen: set[str] = set()
            added = updated = 0
            for module in modules:
                native_id = str(module.get("id") or "").strip()
                if not native_id:
                    continue
                stable_id = "netatmo-" + sha256(native_id.encode("utf-8")).hexdigest()[:20]
                seen.add(stable_id)
                old = devices.get(stable_id) or {}
                module_type = str(module.get("type") or "module").lower()
                climate_types = {"natherm1", "nrv", "ots", "bns", "nsmarter"}
                sensor_types = {"namain", "namodule1", "namodule2", "namodule3", "namodule4", "nacamera", "nhc"}
                bridge_types = {"naplug"}
                is_cover = any(key in module for key in ("current_position", "target_position"))
                is_climate = module_type in climate_types or any(key in module for key in ("therm_measured_temperature", "setpoint", "therm_setpoint_temperature"))
                is_light = "brightness" in module or "light" in module_type
                is_sensor = module_type in sensor_types or "dashboard_data" in module
                is_bridge = module_type in bridge_types
                domain = "cover" if is_cover else "climate" if is_climate else "light" if is_light else "sensor" if is_sensor else "gateway" if is_bridge else "switch"
                capabilities = (["open", "close", "stop", "position"] if is_cover else
                                ["temperature", "target_temperature"] if is_climate else
                                ["on", "off", "level"] if is_light and "brightness" in module else ["on", "off"])
                if is_sensor or is_bridge:
                    capabilities = []
                state_value = module.get("on")
                attributes = deepcopy(module)
                if is_climate:
                    measured = module.get("therm_measured_temperature")
                    target = module.get("therm_setpoint_temperature")
                    if target is None and isinstance(module.get("setpoint"), dict):
                        target = module["setpoint"].get("setpoint_temp")
                    if measured is not None:
                        attributes["current_temperature"] = measured
                    if target is not None:
                        attributes["target_temperature"] = target
                    climate_state = measured if measured is not None else module.get("status")
                    if climate_state in (None, "", "unknown") and module.get("reachable") is True:
                        climate_state = "online"
                    state = {"state": str(climate_state or "unknown"), "attributes": attributes}
                else:
                    state = {"state": "ON" if state_value is True else "OFF" if state_value is False else str(module.get("status") or "unknown"), "attributes": attributes}
                row = {
                    **old, "device_id": stable_id, "native_id": native_id,
                    "home_id": str(module.get("home_id") or ""), "room_id": str(module.get("room_id") or ""),
                    "name": str(module.get("module_name") or module.get("name") or native_id),
                    "group": str(module.get("room_name") or module.get("home_name") or "Netatmo"),
                    "domain": domain, "device_class": domain, "capabilities": capabilities,
                    "manufacturer": "Netatmo / BTicino", "model": str(module.get("type") or ""),
                    "enabled": bool(old.get("enabled", False)), "read_only": bool(old.get("read_only", False) or is_sensor or is_bridge),
                    "orphaned": False, "direct": True, "state": state, "last_seen": time.time(),
                }
                added += int(not bool(old))
                updated += int(bool(old) and row != old)
                devices[stable_id] = row
            for stable_id, row in devices.items():
                if row.get("direct") and stable_id not in seen:
                    row["orphaned"] = True
            bucket["last_sync"] = time.time()
            self.save(data)
            return {"added": added, "updated": updated, "total": len(devices), "enabled": sum(bool(x.get("enabled")) for x in devices.values())}

    def catalog(self, source: str, states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        if source not in INTEGRATIONS:
            return []
        rows: list[dict[str, Any]] = []
        devices = self.load()["integrations"][source]["devices"]
        for row in devices.values():
            if not isinstance(row, dict) or not row.get("enabled"):
                continue
            state = deepcopy(row.get("state") or {}) if row.get("direct") else states.get(str(row.get("entity_id") or "")) or {}
            raw_state = state.get("state") if isinstance(state, dict) else None
            attributes = state.get("attributes") if isinstance(state, dict) and isinstance(state.get("attributes"), dict) else {}
            available = (bool(row.get("direct")) or raw_state not in {None, "unavailable", "unknown"}) and not row.get("orphaned")
            rows.append({
                "device_id": row.get("device_id"),
                "name": row.get("name"),
                "device_class": row.get("device_class"),
                "native_type": row.get("domain"),
                "native_id": row.get("native_id") or row.get("entity_id"),
                "home_id": row.get("home_id") or attributes.get("home_id"),
                "room_id": row.get("room_id") or attributes.get("room_id"),
                "home_assistant_entity_id": row.get("entity_id") if not row.get("direct") else None,
                "capabilities": list(row.get("capabilities") or []),
                "read_only": bool(row.get("read_only", True)),
                "available": available,
                "stale": not available,
                "state": deepcopy(state),
                "manufacturer": row.get("manufacturer"),
                "model": row.get("model"),
            })
        return rows

    def organization_catalog(self, source: str) -> list[dict[str, Any]]:
        """Return every detected device, including devices not enabled in e-Face yet."""
        if source not in INTEGRATIONS:
            return []
        return [
            {
                "device_id": row.get("device_id"),
                "name": row.get("name") or row.get("device_id"),
                "device_class": row.get("device_class") or row.get("domain") or "device",
            }
            for row in self.load()["integrations"][source]["devices"].values()
            if isinstance(row, dict) and not row.get("orphaned")
        ]


class BticinoManager:
    def __init__(self, path: str, token: str):
        self.store = BticinoCatalogStore(path)
        self.ws = HomeAssistantWebSocket(token) if token else None
        self.entries: dict[str, list[dict[str, Any]]] = {source: [] for source in INTEGRATIONS}
        self.errors: dict[str, str] = {source: "" for source in INTEGRATIONS}

    async def sync(self, source: str, states: list[dict[str, Any]]) -> dict[str, Any]:
        if source not in INTEGRATIONS:
            raise ValueError("unsupported BTicino integration")
        if self.ws is None:
            raise RuntimeError("SUPERVISOR_TOKEN missing")
        domain = INTEGRATIONS[source]["domain"]
        try:
            entries = await self.ws.command("config_entries/get", domain=domain)
            self.entries[source] = entries if isinstance(entries, list) else []
            if not self.entries[source]:
                raise RuntimeError(f"{INTEGRATIONS[source]['name']} is not configured")
            registry = await self.ws.command("config/entity_registry/list")
            devices = await self.ws.command("config/device_registry/list")
            by_entity = {
                str(item.get("entity_id") or "").strip().lower(): item
                for item in states
                if isinstance(item, dict) and str(item.get("entity_id") or "").strip()
            }
            result = self.store.sync(
                source,
                registry if isinstance(registry, list) else [],
                by_entity,
                devices if isinstance(devices, list) else [],
            )
            self.errors[source] = ""
            return result
        except Exception as exc:
            self.errors[source] = str(exc)
            raise

    def status(self, source: str) -> dict[str, Any]:
        if source not in INTEGRATIONS:
            raise ValueError("unsupported BTicino integration")
        bucket = self.store.load()["integrations"][source]
        devices = bucket.get("devices") or {}
        entries = self.entries.get(source) or []
        return {
            **INTEGRATIONS[source],
            "available": self.ws is not None,
            "configured": bool(entries),
            "connected": bool(entries) and not self.errors.get(source),
            "config_entries": len(entries),
            "devices": len(devices),
            "enabled": sum(bool(item.get("enabled")) for item in devices.values()),
            "orphaned": sum(bool(item.get("orphaned")) for item in devices.values()),
            "last_sync": bucket.get("last_sync"),
            "error": self.errors.get(source) or "",
            "setup_required": not bool(entries),
        }
