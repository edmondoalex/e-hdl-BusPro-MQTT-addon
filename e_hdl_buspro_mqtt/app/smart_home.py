from __future__ import annotations

from copy import deepcopy
from typing import Any

from .organization import hdl_presentation_class


SCHEMA_VERSION = "1.0"
SECURITY_MARKERS = {"partition", "zone", "alarm", "arm", "disarm", "bypass", "pin", "panel", "sia", "tamper", "security"}
KSENIA_SMART_HOME_TYPES = {"outputs", "scenarios", "domus", "thermostats"}

VISUAL_CATEGORIES = {
    "light": "lights", "dimmer": "lights", "switch": "extra",
    "cover": "covers", "shutter": "covers", "awning": "covers", "gate": "covers", "garage_door": "covers",
    "thermostat": "comfort", "temperature_sensor": "sensors", "humidity_sensor": "sensors",
    "illuminance_sensor": "sensors", "environment_sensor": "sensors", "presence": "sensors", "dry_contact": "sensors",
    "scenario": "scenarios",
}


def command_descriptors(capabilities: list[str]) -> list[dict[str, Any]]:
    descriptors = []
    for action in capabilities:
        item: dict[str, Any] = {"action": str(action), "value_type": "none"}
        if action in {"level", "position"}:
            item.update({"value_type": "number", "minimum": 0, "maximum": 100})
        elif action == "temperature":
            item.update({"value_type": "number", "minimum": 5, "maximum": 35})
        elif action in {"mode", "preset"}:
            item["value_type"] = "string"
        descriptors.append(item)
    return descriptors


def _semantic_fields(device_class: str, capabilities: list[str], read_only: bool, available: bool, orphaned: bool, categories: list[str] | None = None) -> dict[str, Any]:
    return {
        "visual_category": (categories or [VISUAL_CATEGORIES.get(device_class, "extra")])[0],
        "commands": [] if read_only else command_descriptors(capabilities),
        "features": {
            "controllable": bool(capabilities and not read_only and available and not orphaned),
            "realtime": True,
            "scenario": device_class == "scenario" or "execute" in capabilities,
            "routine_trigger": True,
            "routine_action": bool(capabilities and not read_only),
        },
    }


def validate_command_request(item: dict[str, Any] | None, action: Any) -> str:
    if not item:
        raise ValueError("Smart Home device not catalogued")
    clean_action = str(action or "").strip().lower()
    if item.get("orphaned"):
        raise ValueError("Smart Home device is orphaned")
    if item.get("read_only"):
        raise ValueError("Smart Home device is read-only")
    if not item.get("available"):
        raise ValueError("Smart Home device source unavailable")
    if clean_action not in set(item.get("capabilities") or []):
        raise ValueError("capability not catalogued")
    return clean_action


def hdl_device_kind(device: dict[str, Any]) -> str:
    kind = str(device.get("type") or "").strip().lower()
    if kind:
        return kind
    return "switch" if str(device.get("category") or "").strip().casefold() == "switch" else "light"


def _hdl_class(device: dict[str, Any]) -> str:
    return hdl_presentation_class(device)


def _hdl_capabilities(device: dict[str, Any]) -> tuple[list[str], bool]:
    kind = hdl_device_kind(device)
    if kind in {"light", "switch"}:
        return (["on", "off", "level"] if device.get("dimmable") else ["on", "off"], False)
    if kind == "cover":
        caps = ["open", "close", "stop"]
        if device.get("use_position"):
            caps.append("position")
        return caps, False
    return [kind or "state"], True


def _organization_fields(record: dict[str, Any], floors: dict[str, str], rooms: dict[str, str], groups: dict[str, str], device_class: str = "") -> dict[str, Any]:
    floor_id = str(record.get("floor_id") or "")
    room_id = str(record.get("room_id") or "")
    group_ids = [str(x) for x in record.get("group_ids") or []]
    device_class = str(record.get("device_class") or device_class or "").strip().lower()
    categories = [str(x) for x in record.get("categories") or [VISUAL_CATEGORIES.get(device_class, "extra")]]
    return {
        "floor_id": floor_id, "floor_name": floors.get(floor_id, ""),
        "room_id": room_id, "room_name": rooms.get(room_id, ""),
        "group_ids": group_ids, "group_names": [groups[x] for x in group_ids if x in groups],
        "icon_auto": str(record.get("icon_auto") or "mdi:devices"),
        "icon_override": str(record.get("icon_override") or ""),
        "icon": str(record.get("icon_override") or record.get("icon_auto") or "mdi:devices"),
        "orphaned": bool(record.get("orphaned", False)),
        "categories": categories,
        "orders": deepcopy(record.get("orders") or {}),
        "visible": bool(record.get("visible", True)),
        "favorite": bool(record.get("favorite", False)),
        "shortcut": bool(record.get("shortcut", False)),
    }


def build_smart_home(
    *, hdl_devices: list[dict[str, Any]], ksenia_snapshot: dict[str, Any], organization: dict[str, Any],
    states: dict[str, Any], hdl_available: bool, additional_sources: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    floors_rows = deepcopy(organization.get("floors") or [])
    rooms_rows = deepcopy(organization.get("rooms") or [])
    groups_rows = deepcopy(organization.get("groups") or [])
    floors = {str(x.get("id")): str(x.get("name") or "") for x in floors_rows}
    rooms = {str(x.get("id")): str(x.get("name") or "") for x in rooms_rows}
    groups = {str(x.get("id")): str(x.get("name") or "") for x in groups_rows}
    records = organization.get("devices") or {}
    devices: list[dict[str, Any]] = []
    emitted: set[str] = set()
    state_keys = {
        "light": "states", "switch": "states", "cover": "cover_states", "temp": "temp_states", "temperature": "temp_states",
        "humidity": "humidity_states", "illuminance": "illuminance_states",
        "air": "air_quality_states", "dry_contact": "dry_contact_states",
        "pir": "pir_states", "ultrasonic": "ultrasonic_states",
    }
    for device in hdl_devices:
        if str(device.get("origin") or "hdl").lower() == "ha":
            continue
        device_id = str(device.get("addr") or f"{device.get('subnet_id')}.{device.get('device_id')}.{device.get('channel')}")
        kind = hdl_device_kind(device)
        capabilities, read_only = _hdl_capabilities(device)
        state = (states.get(state_keys.get(kind, "")) or {}).get(device_id)
        record = records.get(f"hdl:{device_id}") or {}
        row = {
            "id": f"hdl:{device_id}", "source": "hdl", "device_id": device_id,
            "name": str(device.get("name") or device_id), "device_class": _hdl_class(device),
            "native_type": kind, "native_id": device_id, "capabilities": capabilities,
            "read_only": read_only, "available": bool(hdl_available), "stale": state is None,
            "state": deepcopy(state),
        }
        row.update(_organization_fields(record, floors, rooms, groups, row["device_class"]))
        row.update(_semantic_fields(row["device_class"], capabilities, read_only, row["available"], row["orphaned"], row["categories"]))
        devices.append(row)
        emitted.add(row["id"])
    ksenia_available = str(ksenia_snapshot.get("availability") or "").lower() in {"online", "available", "connected", "ok"}
    for device in ksenia_snapshot.get("devices") or []:
        device_id = str(device.get("device_id") or "")
        native_type = str(device.get("native_type") or "").strip().lower()
        text = " ".join(str(device.get(k) or "").lower().replace("_", " ") for k in ("native_type", "device_class", "name"))
        if native_type not in KSENIA_SMART_HOME_TYPES or any(token.startswith(marker) for token in text.split() for marker in SECURITY_MARKERS):
            continue
        record = records.get(f"ksenia:{device_id}") or {}
        row = {
            "id": f"ksenia:{device_id}", "source": "ksenia", "device_id": device_id,
            "name": str(device.get("name") or device_id), "device_class": str(device.get("device_class") or ""),
            "native_type": native_type, "native_id": str(device.get("native_id") or ""),
            "capabilities": list(device.get("capabilities") or []), "read_only": bool(device.get("read_only")),
            "available": ksenia_available, "stale": bool(device.get("stale", True)),
            "state": deepcopy((device.get("state") or {}).get("value") if isinstance(device.get("state"), dict) else device.get("state")),
        }
        for field in ("home_assistant_entity_id", "home_assistant_entity_ids"):
            if device.get(field):
                row[field] = deepcopy(device[field])
        row.update(_organization_fields(record, floors, rooms, groups, row["device_class"]))
        row.update(_semantic_fields(row["device_class"], row["capabilities"], row["read_only"], row["available"], row["orphaned"], row["categories"]))
        devices.append(row)
        emitted.add(row["id"])
    for source, source_devices in (additional_sources or {}).items():
        clean_source = str(source or "").strip().lower()
        if clean_source in {"hdl", "ksenia"}:
            continue
        for device in source_devices or []:
            device_id = str(device.get("device_id") or "").strip()
            if not clean_source or not device_id:
                continue
            key = f"{clean_source}:{device_id}"
            capabilities = [str(x).strip().lower() for x in device.get("capabilities") or [] if str(x).strip()]
            device_class = str(device.get("device_class") or "").strip().lower()
            read_only = bool(device.get("read_only", not capabilities))
            available = bool(device.get("available", False))
            record = records.get(key) or {}
            row = {
                "id": key, "source": clean_source, "device_id": device_id,
                "name": str(device.get("name") or device_id), "device_class": device_class,
                "native_type": str(device.get("native_type") or ""), "native_id": str(device.get("native_id") or device_id),
                "capabilities": capabilities, "read_only": read_only, "available": available,
                "stale": bool(device.get("stale", device.get("state") is None)), "state": deepcopy(device.get("state")),
            }
            for field in ("home_assistant_entity_id", "home_assistant_entity_ids"):
                if device.get(field):
                    row[field] = deepcopy(device[field])
            row.update(_organization_fields(record, floors, rooms, groups, row["device_class"]))
            if bool(device.get("presentation_authoritative")):
                for field in ("categories", "room_name", "icon_override", "icon_auto"):
                    if device.get(field) not in (None, "", []):
                        row[field] = deepcopy(device[field])
                row["visual_category"] = (row.get("categories") or [""])[0]
                row["icon"] = row.get("icon_override") or row.get("icon_auto") or row.get("icon")
            row.update(_semantic_fields(device_class, capabilities, read_only, available, row["orphaned"], row["categories"]))
            devices.append(row)
            emitted.add(key)
    for key, record in records.items():
        if key in emitted or not bool(record.get("orphaned")):
            continue
        source, _, device_id = str(key).partition(":")
        text = " ".join(str(record.get(k) or "").lower().replace("_", " ") for k in ("device_class", "name"))
        if source == "ksenia" and any(marker in text.split() for marker in SECURITY_MARKERS):
            continue
        row = {
            "id": key, "source": source, "device_id": device_id,
            "name": str(record.get("name") or device_id), "device_class": str(record.get("device_class") or ""),
            "native_type": "", "native_id": "", "capabilities": [], "read_only": True,
            "available": False, "stale": True, "state": None,
        }
        row.update(_organization_fields(record, floors, rooms, groups, row["device_class"]))
        row["orphaned"] = True
        row.update(_semantic_fields(row["device_class"], [], True, False, True, row["categories"]))
        devices.append(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "capability_model_version": "1.0",
        "organization_schema_version": organization.get("schema_version"),
        "command_endpoint_template": "/api/user/smart-home/{source}/{device_id}/command",
        "realtime": {"mode": "snapshot", "supports_refresh": True},
        "features": {"organization": True, "commands": True, "scenarios": True, "routines": True},
        "floors": floors_rows, "rooms": rooms_rows, "groups": groups_rows, "devices": devices,
    }
