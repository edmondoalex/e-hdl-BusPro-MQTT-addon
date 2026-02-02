from __future__ import annotations

import re
from typing import Any


def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9_\- ]+", "", s)
    s = re.sub(r"[\s\-]+", "_", s)
    return s or "device"


def node_id(gateway_host: str, gateway_port: int) -> str:
    return f"buspro_{gateway_host.replace('.', '_')}_{gateway_port}"


def light_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])
    dimmable = bool(device.get("dimmable", True))
    name = str(device.get("name") or f"Light {subnet}.{dev}.{ch}")

    nid = node_id(gateway_host, gateway_port)
    # IMPORTANT: keep discovery topic stable across renames (otherwise HA creates new entities)
    oid = f"light_{subnet}_{dev}_{ch}"
    uid = f"{nid}_light_{subnet}_{dev}_{ch}"

    state_topic = f"{base_topic}/state/light/{subnet}/{dev}/{ch}"
    cmd_topic = f"{base_topic}/cmd/light/{subnet}/{dev}/{ch}"
    availability_topic = f"{base_topic}/availability"

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "schema": "json",
        "state_topic": state_topic,
        "command_topic": cmd_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": {
            # Category device: group lights by user-defined category (defaults to "Luci")
            "identifiers": [f"buspro:category:{slugify(str(device.get('category') or 'Luci'))}"],
            "name": f"BusPro {str(device.get('category') or 'Luci')}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    if dimmable:
        payload["brightness"] = True
        payload["brightness_scale"] = 255

    topic = f"{discovery_prefix}/light/{nid}/{oid}/config"
    return topic, payload


def cover_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])
    name = str(device.get("name") or f"Cover {subnet}.{dev}.{ch}")

    nid = node_id(gateway_host, gateway_port)
    # IMPORTANT: keep discovery topic stable across renames (otherwise HA creates new entities)
    oid = f"cover_{subnet}_{dev}_{ch}"
    uid = f"{nid}_cover_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/cover_state/{subnet}/{dev}/{ch}"
    position_topic = f"{base_topic}/state/cover_pos/{subnet}/{dev}/{ch}"
    cmd_topic = f"{base_topic}/cmd/cover/{subnet}/{dev}/{ch}"
    set_pos_topic = f"{base_topic}/cmd/cover_pos/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Cover")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "command_topic": cmd_topic,
        "state_topic": state_topic,
        "position_topic": position_topic,
        "set_position_topic": set_pos_topic,
        "payload_open": "OPEN",
        "payload_close": "CLOSE",
        "payload_stop": "STOP",
        "state_open": "OPEN",
        "state_closed": "CLOSED",
        "state_opening": "OPENING",
        "state_closing": "CLOSING",
        "state_stopped": "STOP",
        "position_open": 100,
        "position_closed": 0,
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/cover/{nid}/{oid}/config"
    return topic, payload


def cover_no_pct_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Clone cover entity for HA: open/stop/close only (no position, optimistic)."""
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])
    name = str(device.get("name") or f"Cover {subnet}.{dev}.{ch}") + " no%"

    nid = node_id(gateway_host, gateway_port)
    oid = f"cover_{subnet}_{dev}_{ch}_no_pct"
    uid = f"{nid}_cover_{subnet}_{dev}_{ch}_no_pct"

    availability_topic = f"{base_topic}/availability"
    # Use raw command topic to bypass position/auto-stop logic in the gateway.
    cmd_topic = f"{base_topic}/cmd/cover_raw/{subnet}/{dev}/{ch}"

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "command_topic": cmd_topic,
        "payload_open": "OPEN",
        "payload_close": "CLOSE",
        "payload_stop": "STOP",
        "optimistic": True,
        # Show up/down controls even if HA thinks it's already open/closed.
        "assumed_state": True,
        "device": {
            "identifiers": [f"buspro:cover_no_pct:{nid}"],
            "name": "BusPro Cover no %",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/cover/{nid}/{oid}/config"
    return topic, payload


def cover_group_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    group: dict[str, Any],
    category: str = "Cover",
) -> tuple[str, dict[str, Any]]:
    name = str(group.get("name") or "").strip() or "Cover Group"
    nid = node_id(gateway_host, gateway_port)
    gid = str(group.get("id") or "").strip() or slugify(name)
    oid = f"group_{gid}"
    uid = f"{nid}_cover_group_{gid}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/cover_group_state/{gid}"
    position_topic = f"{base_topic}/state/cover_group_pos/{gid}"
    cmd_topic = f"{base_topic}/cmd/cover_group/{gid}"
    set_pos_topic = f"{base_topic}/cmd/cover_group_pos/{gid}"

    cat_slug = slugify(str(category or "Cover"))

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "command_topic": cmd_topic,
        "state_topic": state_topic,
        "position_topic": position_topic,
        "set_position_topic": set_pos_topic,
        "payload_open": "OPEN",
        "payload_close": "CLOSE",
        "payload_stop": "STOP",
        "state_open": "OPEN",
        "state_closed": "CLOSED",
        "state_opening": "OPENING",
        "state_closing": "CLOSING",
        "state_stopped": "STOP",
        "position_open": 100,
        "position_closed": 0,
        "device": {
            # "assieme al gruppo cover": usa lo stesso device category delle cover
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = group.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/cover/{nid}/{oid}/config"
    return topic, payload


def cover_group_no_pct_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    group: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Clone group cover entity for HA: open/stop/close only (no position, optimistic)."""
    name0 = str(group.get("name") or "").strip() or "Cover Group"
    name = name0 + " no%"
    nid = node_id(gateway_host, gateway_port)
    gid = str(group.get("id") or "").strip() or slugify(name0)
    oid = f"group_{gid}_no_pct"
    uid = f"{nid}_cover_group_{gid}_no_pct"

    availability_topic = f"{base_topic}/availability"
    # Use raw command topic to bypass position/auto-stop logic in the gateway.
    cmd_topic = f"{base_topic}/cmd/cover_group_raw/{gid}"

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "command_topic": cmd_topic,
        "payload_open": "OPEN",
        "payload_close": "CLOSE",
        "payload_stop": "STOP",
        "optimistic": True,
        # Show up/down controls even if HA thinks it's already open/closed.
        "assumed_state": True,
        "device": {
            "identifiers": [f"buspro:cover_no_pct:{nid}"],
            "name": "BusPro Cover no %",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = group.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/cover/{nid}/{oid}/config"
    return topic, payload


def temperature_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # sensor id
    name = str(device.get("name") or f"Temperature {subnet}.{dev}.{ch}")

    nid = node_id(gateway_host, gateway_port)
    oid = f"temp_{subnet}_{dev}_{ch}"
    uid = f"{nid}_temp_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/temp/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Temperature")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device_class": "temperature",
        "state_class": "measurement",
        "unit_of_measurement": "°C",
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/sensor/{nid}/{oid}/config"
    return topic, payload


def dry_contact_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # input id
    name = str(device.get("name") or f"Dry contact {subnet}.{dev}.{ch}")

    nid = node_id(gateway_host, gateway_port)
    oid = f"dry_contact_{subnet}_{dev}_{ch}"
    uid = f"{nid}_dry_contact_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/dry_contact/{subnet}/{dev}/{ch}"
    attrs_topic = f"{base_topic}/state/dry_contact_attr/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Dry contact")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "json_attributes_topic": attrs_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    device_class = str(device.get("device_class") or "").strip()
    if device_class and device_class.lower() not in ("none", "null", "undefined"):
        payload["device_class"] = device_class

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/binary_sensor/{nid}/{oid}/config"
    return topic, payload


def pir_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # sensor id / slot
    base_name = str(device.get("name") or f"Presence {subnet}.{dev}.{ch}")
    name = f"{base_name} - PIR"

    nid = node_id(gateway_host, gateway_port)
    oid = f"pir_{subnet}_{dev}_{ch}"
    uid = f"{nid}_pir_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/pir/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Presence")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device_class": "motion",
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/binary_sensor/{nid}/{oid}/config"
    return topic, payload


def ultrasonic_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # sensor id / slot
    base_name = str(device.get("name") or f"Presence {subnet}.{dev}.{ch}")
    name = f"{base_name} - Ultrasonic"

    nid = node_id(gateway_host, gateway_port)
    oid = f"ultrasonic_{subnet}_{dev}_{ch}"
    uid = f"{nid}_ultrasonic_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/ultrasonic/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Presence")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device_class": "occupancy",
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/binary_sensor/{nid}/{oid}/config"
    return topic, payload


def humidity_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # sensor id / slot
    name = str(device.get("name") or f"Humidity {subnet}.{dev}.{ch}")

    nid = node_id(gateway_host, gateway_port)
    oid = f"humidity_{subnet}_{dev}_{ch}"
    uid = f"{nid}_humidity_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/humidity/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Humidity")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device_class": "humidity",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/sensor/{nid}/{oid}/config"
    return topic, payload


def illuminance_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # sensor id / slot
    name = str(device.get("name") or f"Illuminance {subnet}.{dev}.{ch}")

    nid = node_id(gateway_host, gateway_port)
    oid = f"illuminance_{subnet}_{dev}_{ch}"
    uid = f"{nid}_illuminance_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/illuminance/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Illuminance")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device_class": "illuminance",
        "state_class": "measurement",
        "unit_of_measurement": "lx",
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/sensor/{nid}/{oid}/config"
    return topic, payload


def air_quality_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # sensor id / slot
    base_name = str(device.get("name") or f"Air {subnet}.{dev}.{ch}")
    name = f"{base_name} - AIR"

    nid = node_id(gateway_host, gateway_port)
    oid = f"air_quality_{subnet}_{dev}_{ch}"
    uid = f"{nid}_air_quality_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/air_quality/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Air")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        # String state: clean/mild/moderate/severe
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    icon = device.get("icon")
    if icon:
        payload["icon"] = str(icon)

    topic = f"{discovery_prefix}/sensor/{nid}/{oid}/config"
    return topic, payload


def gas_percent_discovery(
    *,
    discovery_prefix: str,
    base_topic: str,
    gateway_host: str,
    gateway_port: int,
    device: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    subnet = int(device["subnet_id"])
    dev = int(device["device_id"])
    ch = int(device["channel"])  # sensor id / slot
    base_name = str(device.get("name") or f"Air {subnet}.{dev}.{ch}")
    name = f"{base_name} - Gas"

    nid = node_id(gateway_host, gateway_port)
    oid = f"gas_percent_{subnet}_{dev}_{ch}"
    uid = f"{nid}_gas_percent_{subnet}_{dev}_{ch}"

    availability_topic = f"{base_topic}/availability"
    state_topic = f"{base_topic}/state/gas_percent/{subnet}/{dev}/{ch}"

    category = str(device.get("category") or "Air")
    cat_slug = slugify(category)

    payload: dict[str, Any] = {
        "name": name,
        "unique_id": uid,
        "state_topic": state_topic,
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "device": {
            "identifiers": [f"buspro:category:{cat_slug}"],
            "name": f"BusPro {category}",
            "manufacturer": "HDL",
            "model": "BusPro",
        },
    }

    # Allow separate icon (optional)
    icon2 = device.get("gas_icon")
    if icon2:
        payload["icon"] = str(icon2)

    topic = f"{discovery_prefix}/sensor/{nid}/{oid}/config"
    return topic, payload
