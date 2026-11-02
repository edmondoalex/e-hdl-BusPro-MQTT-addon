from __future__ import annotations

from typing import Any


def _labels(row: dict[str, Any] | None) -> set[str]:
    values = (row or {}).get("labels") or []
    return {str(value).strip() for value in values if str(value).strip()}


def discover_labeled_entities(
    *,
    label_name: str,
    labels: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    devices: list[dict[str, Any]],
    states: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return HA entities carrying the configured label, directly or via their device."""
    wanted = str(label_name or "").strip().casefold()
    if not wanted:
        return []
    label_ids = {
        str(row.get("label_id") or row.get("id") or "").strip()
        for row in labels
        if isinstance(row, dict)
        and str(row.get("name") or "").strip().casefold() == wanted
    }
    # Also accept the label id itself, useful with older HA registry payloads.
    label_ids.add(str(label_name).strip())
    label_ids.discard("")
    device_labels = {
        str(row.get("id") or "").strip(): _labels(row)
        for row in devices
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    state_by_id = {
        str(row.get("entity_id") or "").strip().lower(): row
        for row in states
        if isinstance(row, dict)
    }
    found: list[dict[str, Any]] = []
    for row in entities:
        if not isinstance(row, dict):
            continue
        entity_id = str(row.get("entity_id") or "").strip().lower()
        if not entity_id or "." not in entity_id:
            continue
        inherited = device_labels.get(str(row.get("device_id") or "").strip(), set())
        if not ((_labels(row) | inherited) & label_ids):
            continue
        domain = entity_id.split(".", 1)[0]
        state = state_by_id.get(entity_id) or {}
        attrs = state.get("attributes") if isinstance(state.get("attributes"), dict) else {}
        name = str(row.get("name") or row.get("original_name") or attrs.get("friendly_name") or "").strip()
        found.append({
            "entity_id": entity_id,
            "domain": domain,
            "name": name,
            "page": "covers" if domain == "cover" else ("locks" if domain == "lock" else ("lights" if domain == "light" else "extra")),
            "eface_only": domain not in {"light", "switch", "cover", "lock"},
            "read_only": domain not in {"light", "switch", "cover", "lock"},
        })
    return found
