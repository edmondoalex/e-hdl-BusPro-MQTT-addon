from __future__ import annotations

from copy import deepcopy
from typing import Any


SCHEMA_VERSION = "1.0"
SECURITY_MARKERS = {"partition", "zone", "alarm", "arm", "disarm", "bypass", "pin", "panel", "sia", "tamper", "security"}
KSENIA_SMART_HOME_TYPES = {"outputs", "scenarios", "domus", "thermostats"}


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


def _hdl_class(device: dict[str, Any]) -> str:
    kind = str(device.get("type") or "").strip().lower()
    if kind == "light":
        return "dimmer" if bool(device.get("dimmable")) else "light"
    return {
        "temperature": "temperature_sensor", "humidity": "humidity_sensor",
        "illuminance": "illuminance_sensor", "air": "environment_sensor",
        "pir": "presence", "ultrasonic": "presence", "dry_contact": "dry_contact",
    }.get(kind, kind or "device")


def _hdl_capabilities(device: dict[str, Any]) -> tuple[list[str], bool]:
    kind = str(device.get("type") or "").strip().lower()
    if kind == "light":
        return (["on", "off", "level"] if device.get("dimmable") else ["on", "off"], False)
    if kind == "cover":
        caps = ["open", "close", "stop"]
        if device.get("use_position"):
            caps.append("position")
        return caps, False
    return [kind or "state"], True


def _organization_fields(record: dict[str, Any], floors: dict[str, str], rooms: dict[str, str], groups: dict[str, str]) -> dict[str, Any]:
    floor_id = str(record.get("floor_id") or "")
    room_id = str(record.get("room_id") or "")
    group_ids = [str(x) for x in record.get("group_ids") or []]
    return {
        "floor_id": floor_id, "floor_name": floors.get(floor_id, ""),
        "room_id": room_id, "room_name": rooms.get(room_id, ""),
        "group_ids": group_ids, "group_names": [groups[x] for x in group_ids if x in groups],
        "icon_auto": str(record.get("icon_auto") or "mdi:devices"),
        "icon_override": str(record.get("icon_override") or ""),
        "icon": str(record.get("icon_override") or record.get("icon_auto") or "mdi:devices"),
        "orphaned": bool(record.get("orphaned", False)),
    }


def build_smart_home(
    *, hdl_devices: list[dict[str, Any]], ksenia_snapshot: dict[str, Any], organization: dict[str, Any],
    states: dict[str, Any], hdl_available: bool,
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
        "light": "states", "cover": "cover_states", "temperature": "temp_states",
        "humidity": "humidity_states", "illuminance": "illuminance_states",
        "air": "air_quality_states", "dry_contact": "dry_contact_states",
        "pir": "pir_states", "ultrasonic": "ultrasonic_states",
    }
    for device in hdl_devices:
        if str(device.get("origin") or "hdl").lower() == "ha":
            continue
        device_id = str(device.get("addr") or f"{device.get('subnet_id')}.{device.get('device_id')}.{device.get('channel')}")
        kind = str(device.get("type") or "").lower()
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
        row.update(_organization_fields(record, floors, rooms, groups))
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
        row.update(_organization_fields(record, floors, rooms, groups))
        devices.append(row)
        emitted.add(row["id"])
    for key, record in records.items():
        if key in emitted or not bool(record.get("orphaned")):
            continue
        source, _, device_id = str(key).partition(":")
        if source not in {"hdl", "ksenia"}:
            continue
        text = " ".join(str(record.get(k) or "").lower().replace("_", " ") for k in ("device_class", "name"))
        if source == "ksenia" and any(marker in text.split() for marker in SECURITY_MARKERS):
            continue
        row = {
            "id": key, "source": source, "device_id": device_id,
            "name": str(record.get("name") or device_id), "device_class": str(record.get("device_class") or ""),
            "native_type": "", "native_id": "", "capabilities": [], "read_only": True,
            "available": False, "stale": True, "state": None,
        }
        row.update(_organization_fields(record, floors, rooms, groups))
        row["orphaned"] = True
        devices.append(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "organization_schema_version": organization.get("schema_version"),
        "floors": floors_rows, "rooms": rooms_rows, "groups": groups_rows, "devices": devices,
    }
