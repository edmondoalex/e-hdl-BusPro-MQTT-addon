from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import time
from copy import deepcopy
from typing import Any


SCHEMA_VERSION = 1
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$", re.IGNORECASE)
_SOURCE_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$", re.IGNORECASE)
_MDI_RE = re.compile(r"^mdi:[a-z0-9][a-z0-9_-]{0,79}$", re.IGNORECASE)

ICON_DEFAULTS = {
    "light": "mdi:lightbulb",
    "dimmer": "mdi:brightness-6",
    "switch": "mdi:light-switch",
    "cover": "mdi:window-shutter",
    "shutter": "mdi:window-shutter",
    "awning": "mdi:awning-outline",
    "gate": "mdi:gate",
    "garage_door": "mdi:garage",
    "temperature_sensor": "mdi:thermometer",
    "temperature": "mdi:thermometer",
    "humidity_sensor": "mdi:water-percent",
    "humidity": "mdi:water-percent",
    "illuminance_sensor": "mdi:brightness-5",
    "illuminance": "mdi:brightness-5",
    "environment_sensor": "mdi:home-thermometer-outline",
    "air": "mdi:air-filter",
    "thermostat": "mdi:thermostat",
    "scenario": "mdi:play-circle-outline",
    "presence": "mdi:motion-sensor",
    "pir": "mdi:motion-sensor",
    "ultrasonic": "mdi:motion-sensor",
    "dry_contact": "mdi:electric-switch",
}

PRESENTATION_CATEGORIES = {"lights", "extra", "covers", "comfort", "sensors", "security", "scenarios"}
CATEGORY_DEFAULTS = {
    "light": ["lights"], "dimmer": ["lights"], "switch": ["extra"],
    "cover": ["covers"], "shutter": ["covers"], "awning": ["covers"],
    "gate": ["covers"], "garage_door": ["covers"], "thermostat": ["comfort"],
    "temperature_sensor": ["sensors"], "humidity_sensor": ["sensors"],
    "illuminance_sensor": ["sensors"], "environment_sensor": ["sensors"],
    "presence": ["sensors"], "dry_contact": ["sensors"], "scenario": ["scenarios"],
}


def _clean_id(value: Any, field: str) -> str:
    out = str(value or "").strip()
    if not out or not _ID_RE.fullmatch(out):
        raise ValueError(f"invalid {field}")
    return out


def _clean_name(value: Any, field: str) -> str:
    out = " ".join(str(value or "").strip().split())
    if not out or len(out) > 120 or any(ord(c) < 32 for c in out):
        raise ValueError(f"invalid {field}")
    return out


def _clean_optional_text(value: Any, field: str, limit: int) -> str:
    out = " ".join(str(value or "").strip().split())
    if len(out) > limit or any(ord(c) < 32 for c in out):
        raise ValueError(f"invalid {field}")
    return out


def _icon(value: Any, *, optional: bool = True) -> str:
    out = str(value or "").strip().lower()
    if not out and optional:
        return ""
    if not _MDI_RE.fullmatch(out):
        raise ValueError("icon must be mdi:<name>")
    return out


def canonical_key(source: Any, device_id: Any) -> str:
    clean_source = str(source or "").strip().lower()
    if not _SOURCE_RE.fullmatch(clean_source):
        raise ValueError("invalid source")
    return f"{clean_source}:{_clean_id(device_id, 'device_id')}"


def default_icon(device_class: Any) -> str:
    return ICON_DEFAULTS.get(str(device_class or "").strip().lower(), "mdi:devices")


def default_categories(device_class: Any) -> list[str]:
    return list(CATEGORY_DEFAULTS.get(str(device_class or "").strip().lower(), ["extra"]))


class OrganizationStore:
    """Versioned, driver-neutral organization persisted separately from driver catalogs."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "floors": [],
            "rooms": [],
            "groups": [],
            "devices": {},
            "migration": {"hdl_v1": False},
        }

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
                    raise ValueError("unsupported organization schema")
            except FileNotFoundError:
                return self.empty()
            except (json.JSONDecodeError, ValueError, TypeError):
                stamp = time.strftime("%Y%m%d-%H%M%S")
                try:
                    shutil.copy2(self.path, f"{self.path}.corrupt.{stamp}.bak")
                except OSError:
                    pass
                return self.empty()
            base = self.empty()
            for key in base:
                if key in data and isinstance(data[key], type(base[key])):
                    base[key] = data[key]
            return base

    def save(self, data: dict[str, Any], *, backup: bool = True) -> dict[str, Any]:
        cleaned = self.validate(data)
        with self._lock:
            folder = os.path.dirname(self.path) or "."
            os.makedirs(folder, exist_ok=True)
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    current = self.validate(json.load(handle))
                if current == cleaned:
                    return deepcopy(cleaned)
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                pass
            if backup and os.path.isfile(self.path):
                shutil.copy2(self.path, self.path + ".bak")
            fd, tmp = tempfile.mkstemp(prefix=".organization-", suffix=".json", dir=folder)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(cleaned, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        return deepcopy(cleaned)

    def validate(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("organization must be an object")
        out = self.empty()
        out["migration"] = deepcopy(data.get("migration") or {})
        known: dict[str, set[str]] = {}
        for collection in ("floors", "rooms", "groups"):
            rows = data.get(collection) or []
            if not isinstance(rows, list):
                raise ValueError(f"{collection} must be a list")
            ids: set[str] = set()
            clean_rows = []
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError(f"invalid {collection} row")
                rid = _clean_id(row.get("id"), f"{collection}.id")
                if rid in ids:
                    raise ValueError(f"duplicate {collection} id")
                item = {"id": rid, "name": _clean_name(row.get("name"), f"{collection}.name")}
                if collection == "rooms":
                    item["floor_id"] = _clean_id(row.get("floor_id"), "floor_id")
                if row.get("icon"):
                    item["icon"] = _icon(row.get("icon"))
                ids.add(rid)
                clean_rows.append(item)
            known[collection] = ids
            out[collection] = clean_rows
        if any(row["floor_id"] not in known["floors"] for row in out["rooms"]):
            raise ValueError("room references unknown floor")
        devices = data.get("devices") or {}
        if not isinstance(devices, dict):
            raise ValueError("devices must be an object")
        for key, raw in devices.items():
            if not isinstance(raw, dict):
                raise ValueError("invalid device record")
            source, sep, device_id = str(key).partition(":")
            canonical = canonical_key(source, device_id) if sep else ""
            if canonical != key:
                raise ValueError("non-canonical device key")
            floor_id = str(raw.get("floor_id") or "").strip()
            room_id = str(raw.get("room_id") or "").strip()
            group_ids = list(dict.fromkeys(str(v).strip() for v in (raw.get("group_ids") or []) if str(v).strip()))
            categories = list(dict.fromkeys(str(v).strip().lower() for v in (raw.get("categories") or default_categories(raw.get("device_class"))) if str(v).strip()))
            if not categories or any(v not in PRESENTATION_CATEGORIES for v in categories):
                raise ValueError("device has invalid categories")
            raw_orders = raw.get("orders") or {}
            if not isinstance(raw_orders, dict):
                raise ValueError("device.orders must be an object")
            orders: dict[str, int] = {}
            for category, value in raw_orders.items():
                clean_category = str(category).strip().lower()
                if clean_category not in PRESENTATION_CATEGORIES:
                    raise ValueError("device has invalid order category")
                try:
                    clean_value = int(value)
                except (TypeError, ValueError):
                    raise ValueError("device order must be an integer")
                if clean_value < 0:
                    raise ValueError("device order must be positive")
                orders[clean_category] = clean_value
            if floor_id and floor_id not in known["floors"]:
                raise ValueError("device references unknown floor")
            if room_id and room_id not in known["rooms"]:
                raise ValueError("device references unknown room")
            if any(v not in known["groups"] for v in group_ids):
                raise ValueError("device references unknown group")
            item = {
                "source": source,
                "device_id": device_id,
                "name": _clean_optional_text(raw.get("name"), "device.name", 160),
                "device_class": _clean_optional_text(raw.get("device_class"), "device.device_class", 80).lower(),
                "floor_id": floor_id,
                "room_id": room_id,
                "group_ids": group_ids,
                "categories": categories,
                "orders": orders,
                "visible": bool(raw.get("visible", True)),
                "favorite": bool(raw.get("favorite", False)),
                "shortcut": bool(raw.get("shortcut", False)),
                "icon_auto": _icon(raw.get("icon_auto") or default_icon(raw.get("device_class")), optional=False),
                "icon_override": _icon(raw.get("icon_override")),
                "orphaned": bool(raw.get("orphaned", False)),
            }
            out["devices"][key] = item
        return out

    def sync_devices(self, devices: list[dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            seen = set()
            for device in devices:
                key = canonical_key(device.get("source"), device.get("device_id"))
                seen.add(key)
                current = deepcopy(data["devices"].get(key) or {})
                device_class = _clean_optional_text(device.get("device_class"), "device.device_class", 80).lower()
                current.update({
                    "source": str(device.get("source")).lower(),
                    "device_id": str(device.get("device_id")),
                    "name": _clean_optional_text(device.get("name") or device.get("device_id"), "device.name", 160),
                    "device_class": device_class,
                    "icon_auto": default_icon(device_class),
                    "orphaned": False,
                })
                current.setdefault("floor_id", "")
                current.setdefault("room_id", "")
                current.setdefault("group_ids", [])
                current.setdefault("icon_override", "")
                current.setdefault("categories", default_categories(device_class))
                current.setdefault("orders", {})
                current.setdefault("visible", True)
                current.setdefault("favorite", False)
                current.setdefault("shortcut", False)
                data["devices"][key] = current
            for key, current in data["devices"].items():
                if key not in seen:
                    current["orphaned"] = True
            return self.save(data, backup=False)

    def migrate_hdl(self, hdl_devices: list[dict[str, Any]], group_order: list[str]) -> dict[str, Any]:
        with self._lock:
            return self._migrate_hdl_locked(hdl_devices, group_order)

    def _migrate_hdl_locked(self, hdl_devices: list[dict[str, Any]], group_order: list[str]) -> dict[str, Any]:
        data = self.load()
        if bool((data.get("migration") or {}).get("hdl_v1")):
            return data
        floor_by_name: dict[str, str] = {}
        room_by_name: dict[str, str] = {}
        current_floor = ""
        for raw in group_order or []:
            value = str(raw or "").strip()
            if not value:
                continue
            if value.startswith("#"):
                name = value[1:].split("|", 1)[0].strip()
                if name:
                    fid = "floor-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                    fid = fid or "floor-main"
                    existing_floor = next((x for x in data["floors"] if x["id"] == fid), None)
                    if existing_floor and existing_floor.get("name") != name:
                        raise ValueError(f"floor migration collision: {name}")
                    if not existing_floor:
                        data["floors"].append({"id": fid, "name": name})
                    floor_by_name[name.casefold()] = fid
                    current_floor = fid
                continue
            name = value
            if not current_floor:
                current_floor = "floor-main"
                if not data["floors"]:
                    data["floors"].append({"id": current_floor, "name": "Edificio"})
            rid = "room-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            existing_room = next((x for x in data["rooms"] if x["id"] == rid), None)
            if existing_room and (existing_room.get("floor_id") != current_floor or existing_room.get("name") != name):
                raise ValueError(f"room migration collision: {name}")
            if not existing_room:
                data["rooms"].append({"id": rid, "name": name, "floor_id": current_floor})
            room_by_name[name.casefold()] = rid
        for dev in hdl_devices:
            addr = str(dev.get("addr") or f"{dev.get('subnet_id')}.{dev.get('device_id')}.{dev.get('channel')}")
            group = str(dev.get("group") or "").strip()
            rid = room_by_name.get(group.casefold(), "")
            floor_id = next((r["floor_id"] for r in data["rooms"] if r["id"] == rid), "")
            key = canonical_key("hdl", addr)
            existing = data["devices"].get(key) or {}
            device_class = str(dev.get("type") or ("dimmer" if dev.get("dimmable") else "light"))
            legacy_icon = str(dev.get("icon") or "").strip().lower()
            if legacy_icon and not _MDI_RE.fullmatch(legacy_icon):
                legacy_icon = ""
            existing.update({
                "source": "hdl", "device_id": addr, "name": str(dev.get("name") or addr),
                "device_class": device_class, "floor_id": existing.get("floor_id") or floor_id,
                "room_id": existing.get("room_id") or rid, "group_ids": existing.get("group_ids") or [],
                "icon_auto": default_icon(device_class), "icon_override": existing.get("icon_override") or legacy_icon,
                "categories": existing.get("categories") or default_categories(device_class),
                "orders": existing.get("orders") or {}, "visible": existing.get("visible", True),
                "favorite": existing.get("favorite", False), "shortcut": existing.get("shortcut", False),
                "orphaned": False,
            })
            data["devices"][key] = existing
        data["migration"] = {**(data.get("migration") or {}), "hdl_v1": True, "migrated_at": int(time.time())}
        return self.save(data)

    def replace_structure(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            for key in ("floors", "rooms", "groups"):
                if key in payload:
                    data[key] = payload[key]
            return self.save(data)

    def validate_backup(self, data: dict[str, Any]) -> dict[str, Any]:
        return self.validate(data)

    def assign(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            key = canonical_key(payload.get("source"), payload.get("device_id"))
            if key not in data["devices"]:
                raise ValueError("unknown device")
            item = data["devices"][key]
            for field in ("floor_id", "room_id", "group_ids", "icon_override", "categories", "orders", "visible", "favorite", "shortcut"):
                if field in payload:
                    item[field] = payload[field]
            saved = self.save(data)
            return deepcopy(saved["devices"][key])

    def snapshot(self) -> dict[str, Any]:
        data = self.load()
        for item in data["devices"].values():
            item["icon"] = item.get("icon_override") or item.get("icon_auto") or "mdi:devices"
        return data
