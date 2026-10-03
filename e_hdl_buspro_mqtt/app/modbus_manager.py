from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from copy import deepcopy
from hashlib import sha256
from typing import Any

from .knx_manager import HomeAssistantWebSocket, _capabilities, _device_class


SCHEMA_VERSION = 1
CONNECTION_TYPES = {"tcp", "udp", "rtuovertcp", "serial"}
REGISTER_TYPES = {"coil", "discrete_input", "holding", "input"}
DATA_TYPES = {"int16", "uint16", "int32", "uint32", "int64", "uint64", "float16", "float32", "float64", "string"}
ENTITY_TYPES = {"binary_sensor", "sensor", "switch"}


def ferroli_omnia_m32_profile(*, commands_enabled: bool = False) -> dict[str, Any]:
    """Conservative built-in profile from the verified OMNIA M 3.2 register excerpt.

    PLC register numbers are converted to zero-based protocol addresses. Until the
    complete manufacturer map is archived, only the three confirmed power words
    are included and they default to read-only sensors.
    """
    entity_type = "switch" if commands_enabled else "sensor"
    return {
        "id": "ferroli_omnia_m_3_2",
        "name": "Ferroli OMNIA M 3.2",
        "manufacturer": "Ferroli",
        "model": "OMNIA M 3.2",
        "category": "heat_pump",
        "version": 1,
        "registers": [
            {
                "key": key, "name": name, "entity_type": entity_type,
                "address": plc_address - 40001, "register_type": "holding",
                "data_type": "uint16", "scale": 1, "offset": 0,
                "scan_interval": 15, "unit": "", "device_class": "",
                "writable": commands_enabled, "min": 0, "max": 1,
                "swap": "none", "precision": 0,
            }
            for key, name, plc_address in (
                ("power_z2", "Alimentazione zona 2", 40015),
                ("power_z1", "Alimentazione zona 1", 40016),
                ("power_dhw", "Alimentazione ACS", 40017),
            )
        ],
    }


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if not clean:
        raise ValueError("name must contain letters or numbers")
    return clean[:64]


def _number(value: Any, name: str, minimum: float, maximum: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric")
    if result < minimum or result > maximum:
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")
    return result


def validate_connection(raw: dict[str, Any]) -> dict[str, Any]:
    kind = str(raw.get("type") or "tcp").strip().lower()
    if kind not in CONNECTION_TYPES:
        raise ValueError("unsupported connection type")
    name = str(raw.get("name") or "").strip()
    row: dict[str, Any] = {
        "id": _slug(raw.get("id") or name), "name": name, "type": kind,
        "timeout": int(_number(raw.get("timeout", 5), "timeout", 1, 60)),
        "delay": int(_number(raw.get("delay", 0), "delay", 0, 60)),
        "message_wait_milliseconds": int(_number(raw.get("message_wait_milliseconds", 30 if kind == "serial" else 0), "message wait", 0, 10000)),
        "enabled": bool(raw.get("enabled", True)),
    }
    if kind == "serial":
        port = str(raw.get("port") or "").strip()
        if not port.startswith("/dev/"):
            raise ValueError("serial port must be below /dev")
        row.update({
            "port": port, "baudrate": int(_number(raw.get("baudrate", 9600), "baudrate", 300, 921600)),
            "bytesize": int(raw.get("bytesize", 8)), "parity": str(raw.get("parity", "N")).upper(),
            "stopbits": int(raw.get("stopbits", 1)), "method": str(raw.get("method", "rtu")).lower(),
        })
        if row["bytesize"] not in {5, 6, 7, 8} or row["parity"] not in {"N", "E", "O"} or row["stopbits"] not in {1, 2} or row["method"] not in {"rtu", "ascii"}:
            raise ValueError("invalid serial framing")
    else:
        host = str(raw.get("host") or "").strip()
        if not host or any(ch.isspace() for ch in host):
            raise ValueError("host is required")
        row.update({"host": host, "port": int(_number(raw.get("port", 502), "port", 1, 65535))})
    return row


def validate_register(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name") or "").strip()
    entity_type = str(raw.get("entity_type") or "sensor").lower()
    register_type = str(raw.get("register_type") or "holding").lower()
    data_type = str(raw.get("data_type") or "int16").lower()
    if entity_type not in ENTITY_TYPES or register_type not in REGISTER_TYPES or data_type not in DATA_TYPES:
        raise ValueError("unsupported entity, register or data type")
    if entity_type == "sensor" and register_type not in {"holding", "input"}:
        raise ValueError("sensor requires a holding or input register")
    if entity_type == "switch" and register_type not in {"coil", "holding"}:
        raise ValueError("switch requires a coil or holding register")
    row = {
        "key": _slug(raw.get("key") or name), "name": name, "entity_type": entity_type,
        "address": int(_number(raw.get("address"), "address", 0, 65535)),
        "register_type": register_type, "data_type": data_type,
        "scale": _number(raw.get("scale", 1), "scale", -1000000, 1000000),
        "offset": _number(raw.get("offset", 0), "offset", -1000000, 1000000),
        "scan_interval": int(_number(raw.get("scan_interval", 15), "scan interval", 0, 86400)),
        "unit": str(raw.get("unit") or "").strip()[:32], "device_class": str(raw.get("device_class") or "").strip()[:64],
        "writable": bool(raw.get("writable", False)), "min": raw.get("min"), "max": raw.get("max"),
        "swap": str(raw.get("swap") or "none").lower(), "precision": int(_number(raw.get("precision", 1), "precision", 0, 6)),
    }
    if row["swap"] not in {"none", "byte", "word", "word_byte"}:
        raise ValueError("invalid byte/word swap")
    if row["min"] is not None and row["max"] is not None and float(row["min"]) >= float(row["max"]):
        raise ValueError("minimum must be lower than maximum")
    return row


class ModbusStore:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "connections": {}, "profiles": {}, "devices": {}, "catalog": {}, "last_sync": None, "last_apply": None}

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
                    return self.empty()
            except (FileNotFoundError, OSError, ValueError, TypeError):
                return self.empty()
            for key in ("connections", "profiles", "devices", "catalog"):
                data.setdefault(key, {})
            return data

    def save(self, data: dict[str, Any]) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".modbus-manager-", suffix=".json", dir=os.path.dirname(self.path) or ".")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
                    handle.flush(); os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)

    def put_connection(self, raw: dict[str, Any]) -> dict[str, Any]:
        row = validate_connection(raw)
        with self._lock:
            data = self.load(); data["connections"][row["id"]] = row; self.save(data)
        return deepcopy(row)

    def put_profile(self, raw: dict[str, Any]) -> dict[str, Any]:
        name = str(raw.get("name") or "").strip()
        registers = [validate_register(item) for item in (raw.get("registers") or [])]
        if not registers: raise ValueError("profile requires at least one register")
        keys = [item["key"] for item in registers]
        if len(keys) != len(set(keys)): raise ValueError("duplicate register key")
        row = {"id": _slug(raw.get("id") or name), "name": name, "manufacturer": str(raw.get("manufacturer") or "").strip()[:80], "model": str(raw.get("model") or "").strip()[:80], "category": str(raw.get("category") or "heat_pump").strip()[:40], "version": int(raw.get("version", 1)), "registers": registers}
        with self._lock:
            data = self.load(); data["profiles"][row["id"]] = row; self.save(data)
        return deepcopy(row)

    def put_device(self, raw: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            connection_id, profile_id = str(raw.get("connection_id") or ""), str(raw.get("profile_id") or "")
            if connection_id not in data["connections"]: raise ValueError("unknown connection")
            if profile_id not in data["profiles"]: raise ValueError("unknown profile")
            name = str(raw.get("name") or "").strip(); device_id = _slug(raw.get("id") or name)
            row = {"id": device_id, "name": name, "connection_id": connection_id, "profile_id": profile_id, "slave": int(_number(raw.get("slave", 1), "slave", 1, 247)), "enabled": bool(raw.get("enabled", True))}
            data["devices"][device_id] = row; self.save(data)
            return deepcopy(row)

    def provision_ferroli_omnia(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Create one gateway and one or two OMNIA units as a single transaction."""
        connection = validate_connection({
            "id": "ferroli_omnia_gateway",
            "name": "Gateway Ferroli OMNIA",
            "type": "tcp",
            "host": raw.get("host"),
            "port": raw.get("port", 502),
            "timeout": raw.get("timeout", 5),
            "message_wait_milliseconds": raw.get("message_wait_milliseconds", 30),
            "enabled": True,
        })
        pumps_raw = raw.get("pumps") or []
        if not isinstance(pumps_raw, list) or not 1 <= len(pumps_raw) <= 2:
            raise ValueError("configure one or two Ferroli pumps")
        pumps: list[dict[str, Any]] = []
        slaves: set[int] = set()
        for index, item in enumerate(pumps_raw, 1):
            if not isinstance(item, dict):
                raise ValueError("invalid Ferroli pump")
            slave = int(_number(item.get("slave", index), "slave", 1, 247))
            if slave in slaves:
                raise ValueError("Ferroli pumps require different slave IDs")
            slaves.add(slave)
            name = str(item.get("name") or f"Ferroli OMNIA {index}").strip()
            pumps.append({
                "id": _slug(item.get("id") or name), "name": name,
                "connection_id": connection["id"], "profile_id": "ferroli_omnia_m_3_2",
                "slave": slave, "enabled": True,
            })
        commands_enabled = bool(raw.get("commands_enabled", False))
        profile = {
            **ferroli_omnia_m32_profile(commands_enabled=commands_enabled),
            "commands_enabled": commands_enabled,
            "documentation_status": "partial_verified_registers",
        }
        profile["registers"] = [validate_register(item) for item in profile["registers"]]
        with self._lock:
            data = self.load()
            data["connections"][connection["id"]] = connection
            data["profiles"][profile["id"]] = profile
            for pump in pumps:
                data["devices"][pump["id"]] = pump
            self.save(data)
        return {
            "connection": deepcopy(connection), "profile": deepcopy(profile),
            "pumps": deepcopy(pumps), "commands_enabled": commands_enabled,
        }

    def sync_catalog(self, registry: list[dict[str, Any]], states: dict[str, dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            data = self.load(); catalog = data["catalog"]; seen = set()
            for entry in registry:
                if str(entry.get("platform") or "").lower() != "modbus": continue
                entity_id = str(entry.get("entity_id") or "").lower(); domain = entity_id.partition(".")[0]
                if domain not in ENTITY_TYPES: continue
                stable = "ha-" + sha256(str(entry.get("id") or entry.get("unique_id") or entity_id).encode()).hexdigest()[:20]
                seen.add(stable); old = catalog.get(stable) or {}; state = states.get(entity_id) or {}; attrs = state.get("attributes") or {}
                catalog[stable] = {**old, "device_id": stable, "entity_id": entity_id, "name": entry.get("name") or entry.get("original_name") or attrs.get("friendly_name") or entity_id, "domain": domain, "device_class": _device_class(domain, state), "capabilities": _capabilities(domain, state), "enabled": bool(old.get("enabled", False)), "read_only": bool(old.get("read_only", True)), "orphaned": False, "last_seen": time.time()}
            for key, row in catalog.items(): row["orphaned"] = key not in seen
            data["last_sync"] = time.time(); self.save(data)
            return {"total": len(catalog), "enabled": sum(bool(x.get("enabled")) for x in catalog.values()), "orphaned": sum(bool(x.get("orphaned")) for x in catalog.values())}

    def update_catalog(self, device_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self.load(); row = data["catalog"].get(device_id)
            if not row: raise KeyError(device_id)
            if "enabled" in payload: row["enabled"] = bool(payload["enabled"])
            if "read_only" in payload: row["read_only"] = bool(payload["read_only"])
            self.save(data); return deepcopy(row)

    def catalog(self, states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for row in self.load()["catalog"].values():
            if not row.get("enabled"): continue
            state = states.get(row["entity_id"]) or {}; available = state.get("state") not in {None, "unknown", "unavailable"} and not row.get("orphaned")
            result.append({"device_id": row["device_id"], "name": row["name"], "device_class": row["device_class"], "native_type": row["domain"], "native_id": row["entity_id"], "home_assistant_entity_id": row["entity_id"], "capabilities": row["capabilities"], "read_only": bool(row.get("read_only", True)), "available": available, "stale": not available, "state": deepcopy(state)})
        return result

    def organization_catalog(self) -> list[dict[str, Any]]:
        return [
            {"device_id": row.get("device_id"), "name": row.get("name") or row.get("device_id"), "device_class": row.get("device_class") or row.get("domain") or "device"}
            for row in self.load()["catalog"].values()
            if isinstance(row, dict) and not row.get("orphaned")
        ]

    def render_home_assistant(self) -> str:
        data = self.load(); lines = ["# Managed by e-Control Hub. Do not edit manually."]
        for connection in data["connections"].values():
            if not connection.get("enabled"): continue
            lines += [f"- name: {json.dumps(connection['id'])}", f"  type: {connection['type']}"]
            for key in ("host", "port", "baudrate", "bytesize", "method", "parity", "stopbits", "delay", "message_wait_milliseconds", "timeout"):
                if key in connection: lines.append(f"  {key}: {json.dumps(connection[key])}")
            grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
            for device in data["devices"].values():
                if not device.get("enabled") or device["connection_id"] != connection["id"]: continue
                profile = data["profiles"][device["profile_id"]]
                for register in profile["registers"]:
                    platform = {"sensor": "sensors", "binary_sensor": "binary_sensors", "switch": "switches"}[register["entity_type"]]
                    grouped.setdefault(platform, []).append((device, register))
            for platform, entries in grouped.items():
                lines.append(f"  {platform}:")
                for device, register in entries:
                    unique = f"econtrol_modbus_{device['id']}_{register['key']}"
                    access_key = "write_type" if register["entity_type"] == "switch" else "input_type"
                    lines += [f"    - name: {json.dumps(device['name'] + ' ' + register['name'])}", f"      unique_id: {json.dumps(unique)}", f"      slave: {device['slave']}", f"      address: {register['address']}", f"      {access_key}: {register['register_type']}", f"      scan_interval: {register['scan_interval']}"]
                    if register["entity_type"] == "sensor":
                        lines += [f"      data_type: {register['data_type']}", f"      scale: {register['scale']}", f"      offset: {register['offset']}", f"      precision: {register['precision']}"]
                        if register["unit"]: lines.append(f"      unit_of_measurement: {json.dumps(register['unit'])}")
                        if register["device_class"]: lines.append(f"      device_class: {json.dumps(register['device_class'])}")
                        if register["swap"] != "none": lines.append(f"      swap: {register['swap']}")
        return "\n".join(lines) + "\n"


class ModbusManager:
    def __init__(self, path: str, token: str, config_dir: str = "/config"):
        self.store = ModbusStore(path); self.ws = HomeAssistantWebSocket(token) if token else None
        self.config_dir = config_dir; self.error = ""; self.entries: list[dict[str, Any]] = []

    async def sync(self, states: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.ws: raise RuntimeError("SUPERVISOR_TOKEN missing")
        try:
            self.entries = await self.ws.command("config_entries/get", domain="modbus") or []
            registry = await self.ws.command("config/entity_registry/list")
            by_entity = {str(x.get("entity_id") or "").lower(): x for x in states if isinstance(x, dict)}
            result = self.store.sync_catalog(registry or [], by_entity); self.error = ""; return result
        except Exception as exc:
            self.error = str(exc); raise

    def apply(self) -> dict[str, Any]:
        target = os.path.join(self.config_dir, "modbus_econtrol.yaml"); content = self.store.render_home_assistant()
        os.makedirs(self.config_dir, exist_ok=True); fd, tmp = tempfile.mkstemp(prefix=".modbus-", suffix=".yaml", dir=self.config_dir)
        with os.fdopen(fd, "w", encoding="utf-8") as handle: handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, target)
        main_config = os.path.join(self.config_dir, "configuration.yaml")
        include = "modbus: !include modbus_econtrol.yaml"
        with open(main_config, "r", encoding="utf-8") as handle:
            main_content = handle.read()
        if include not in main_content:
            if re.search(r"(?m)^modbus\s*:", main_content):
                raise RuntimeError("configuration.yaml already contains a Modbus section; import or remove it before e-Control takes ownership")
            backup = main_config + f".econtrol-{int(time.time())}.bak"
            with open(backup, "w", encoding="utf-8") as handle:
                handle.write(main_content)
            fd, config_tmp = tempfile.mkstemp(prefix=".configuration-", suffix=".yaml", dir=self.config_dir)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(main_content.rstrip() + "\n\n# e-Control managed Modbus\n" + include + "\n")
                handle.flush(); os.fsync(handle.fileno())
            os.replace(config_tmp, main_config)
        data = self.store.load(); data["last_apply"] = time.time(); self.store.save(data)
        return {"path": target, "bytes": len(content.encode()), "sha256": sha256(content.encode()).hexdigest(), "include": include, "restart_required": True}

    def snapshot(self) -> dict[str, Any]:
        data = self.store.load(); catalog = data["catalog"]
        return {"status": {"available": self.ws is not None, "configured": bool(data["connections"]), "connected": bool(self.entries) and not self.error, "connections": len(data["connections"]), "profiles": len(data["profiles"]), "devices": len(data["devices"]), "entities": len(catalog), "enabled": sum(bool(x.get("enabled")) for x in catalog.values()), "last_sync": data.get("last_sync"), "last_apply": data.get("last_apply"), "error": self.error}, **deepcopy(data), "generated_yaml": self.store.render_home_assistant()}
