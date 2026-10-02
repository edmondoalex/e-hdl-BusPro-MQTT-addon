from __future__ import annotations

from copy import deepcopy
from typing import Any


def _device_class(domain: str, page: str, cap: dict[str, Any]) -> str:
    native = str(cap.get("device_class") or "").strip().lower()
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
    if domain == "light" and cap.get("dimmable"):
        values.append("level")
    return values


def build_ha_catalog(
    configured: list[dict[str, Any]],
    states: dict[str, Any],
    caps: dict[str, Any],
) -> list[dict[str, Any]]:
    """Adapt the existing e-Control HA selections to Smart Home v1.

    Lock-page items deliberately stay on the established legacy security path in
    e-Face, where their confirmation and safety semantics already exist.
    """
    rows: list[dict[str, Any]] = []
    for item in configured:
        entity_id = str(item.get("entity_id") or "").strip().lower()
        if not entity_id or "." not in entity_id:
            continue
        domain = str(item.get("domain") or entity_id.split(".", 1)[0]).strip().lower()
        page = str(item.get("page") or "").strip().lower() or ("covers" if domain == "cover" else "lights")
        if page == "locks":
            continue
        cap = caps.get(entity_id) if isinstance(caps.get(entity_id), dict) else {}
        state = deepcopy(states.get(entity_id))
        available = isinstance(state, dict) and str(state.get("state") or "").lower() not in {"", "unknown", "unavailable"}
        category = {"lights": "lights", "covers": "covers", "extra": "extra", "sensors": "sensors", "comfort": "comfort"}.get(page, page)
        rows.append({
            "device_id": entity_id,
            "name": str(item.get("name") or cap.get("name") or entity_id),
            "device_class": _device_class(domain, page, cap),
            "native_type": domain,
            "native_id": entity_id,
            "home_assistant_entity_id": entity_id,
            "capabilities": _capabilities(domain, cap),
            "read_only": False,
            "available": available,
            "stale": not available,
            "state": state,
            "presentation_authoritative": True,
            "categories": [category] if category else [],
            "room_name": str(item.get("group") or "").strip(),
            "icon_override": str(item.get("icon") or cap.get("icon") or "").strip(),
        })
    return rows
