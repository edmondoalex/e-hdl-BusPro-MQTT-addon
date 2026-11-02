from __future__ import annotations

from copy import deepcopy
from typing import Any


def _device_class(domain: str, page: str, cap: dict[str, Any]) -> str:
    native = str(cap.get("device_class") or "").strip().lower()
    if domain == "lock":
        return "lock"
    if domain == "light":
        return "dimmer" if cap.get("dimmable") else "light"
    if domain == "cover":
        return {"garage": "garage_door", "gate": "gate", "shutter": "shutter"}.get(native, "cover")
    if domain == "switch":
        return "switch"
    if domain == "fan":
        return "fan"
    if domain == "climate":
        return "thermostat"
    if domain == "sensor":
        return {
            "temperature": "temperature_sensor",
            "humidity": "humidity_sensor",
            "illuminance": "illuminance_sensor",
        }.get(native, "sensor")
    return domain or "sensor"


def _capabilities(domain: str, cap: dict[str, Any]) -> list[str]:
    values: list[str] = []
    if domain in {"light", "switch", "fan"}:
        values = ["on", "off"]
    elif domain == "cover":
        values = ["open", "close", "stop"]
        if cap.get("use_position"):
            values.append("position")
    elif domain == "climate":
        values = ["temperature"]
    elif domain in {"scene", "button"}:
        values = ["execute"]
    elif domain == "lock":
        values = ["lock", "unlock"]
        if cap.get("open_supported"):
            values.append("open")
    if domain == "light" and cap.get("dimmable"):
        values.append("level")
    return values


def build_ha_catalog(
    configured: list[dict[str, Any]],
    states: dict[str, Any],
    caps: dict[str, Any],
    *,
    include_disabled: bool = False,
) -> list[dict[str, Any]]:
    """Adapt the existing e-Control HA selections to Smart Home v1.

    Lock-page items are included so presentation and permissions use the same
    multi-bus catalog as every other device family.
    """
    rows: list[dict[str, Any]] = []
    for item in configured:
        if item.get("enabled") is False and not include_disabled:
            continue
        entity_id = str(item.get("entity_id") or "").strip().lower()
        if not entity_id or "." not in entity_id:
            continue
        domain = str(item.get("domain") or entity_id.split(".", 1)[0]).strip().lower()
        page = str(item.get("page") or "").strip().lower() or ("covers" if domain == "cover" else "lights")
        cap = dict(caps.get(entity_id)) if isinstance(caps.get(entity_id), dict) else {}
        if item.get("open_supported") is not None:
            cap["open_supported"] = bool(item.get("open_supported"))
        state = deepcopy(states.get(entity_id))
        available = isinstance(state, dict) and str(state.get("state") or "").lower() not in {"", "unknown", "unavailable"}
        category = {"lights": "lights", "covers": "covers", "extra": "extra", "sensors": "sensors", "comfort": "comfort", "locks": "security"}.get(page, page)
        rows.append({
            "device_id": entity_id,
            "name": str(item.get("name") or cap.get("name") or entity_id),
            "device_class": _device_class(domain, page, cap),
            "native_type": domain,
            "native_id": entity_id,
            "home_assistant_entity_id": entity_id,
            "capabilities": _capabilities(domain, cap),
            "read_only": bool(item.get("read_only", False)),
            "available": available,
            "stale": not available,
            "state": state,
            "presentation_authoritative": False,
            "categories": [category] if category else [],
            "room_name": str(item.get("group") or "").strip(),
            "icon_override": str(item.get("icon") or cap.get("icon") or "").strip(),
        })
    return rows
