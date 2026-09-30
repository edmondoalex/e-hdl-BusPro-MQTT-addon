from __future__ import annotations

import json
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol


MANIFEST_TOPIC = "ekonex/v1/integrations/ksenia/manifest"
CATALOG_TOPIC = "ekonex/v1/integrations/ksenia/devices"
RESULT_PREFIX = "ekonex/v1/integrations/ksenia/command_result/"
RESULT_FILTER = RESULT_PREFIX + "+"

ALLOWED_TYPES = {"outputs", "scenarios", "domus", "thermostats"}
ALLOWED_CLASSES = {
    "switch", "light", "dimmer", "cover", "gate", "garage_door", "awning", "shutter",
    "scenario", "environment_sensor", "temperature_sensor", "humidity_sensor",
    "illuminance_sensor", "thermostat",
}
ALLOWED_RESULTS = {"accepted", "confirmed", "failed", "timeout", "unavailable"}
FORBIDDEN_MARKERS = {
    "partition", "arm", "disarm", "alarm", "bypass", "account", "user", "pin",
    "panel", "reset", "sia", "tamper", "security",
}


class MqttTransport(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def subscribe(self, topic: str, *, qos: int = 0) -> None: ...
    def unsubscribe(self, topic: str) -> None: ...
    def publish(self, topic: str, payload: Any, *, retain: bool = False, qos: int = 0) -> None: ...
    def set_message_handler(self, handler) -> None: ...
    def set_connect_handler(self, handler) -> None: ...
    def status(self): ...


class ContractError(ValueError):
    pass


@dataclass
class PendingCommand:
    command_id: str
    correlation_id: str
    device_id: str
    action: str
    created_at: float
    status: str = "pending"
    error: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    event: threading.Event = field(default_factory=threading.Event, repr=False)


def _version_ok(value: Any) -> bool:
    return str(value or "").strip().startswith("1.")


def _topic(value: Any, field_name: str) -> str:
    topic = str(value or "").strip()
    if not topic or topic.startswith("/") or "#" in topic or "+" in topic or "\x00" in topic:
        raise ContractError(f"invalid {field_name}")
    return topic


def _contains_forbidden(*values: Any) -> bool:
    text = " ".join(str(value or "").lower().replace("_", " ").replace("/", " ") for value in values)
    return any(marker in text.split() for marker in FORBIDDEN_MARKERS)


def validate_manifest(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ContractError("manifest must be an object")
    if not _version_ok(raw.get("schema_version")):
        raise ContractError("unsupported manifest schema_version")
    if str(raw.get("integration_id") or "").strip().lower() != "ksenia":
        raise ContractError("manifest integration_id must be ksenia")
    out = deepcopy(raw)
    out["availability_topic"] = _topic(raw.get("availability_topic"), "availability_topic")
    if str(raw.get("catalog_topic") or "") != CATALOG_TOPIC:
        raise ContractError("unexpected catalog_topic")
    if str(raw.get("command_result_topic_template") or "") != RESULT_PREFIX + "{command_id}":
        raise ContractError("unexpected command_result_topic_template")
    return out


def _producer_commands(item: dict[str, Any], command_topic: str, capabilities: set[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    per_capability = item.get("command_topics") or {}
    if not isinstance(per_capability, dict):
        raise ContractError("command_topics must be an object")
    fixed = {"on": "ON", "off": "OFF", "toggle": "TOGGLE", "open": "OPEN", "close": "CLOSE", "stop": "STOP", "execute": "EXECUTE"}
    ranged = {"level": (0, 100), "position": (0, 100), "temperature": (5, 35)}
    for action in capabilities:
        if action in {"temperature", "mode", "preset"}:
            declared_topic = _topic(per_capability.get(action), f"command_topics.{action}")
        else:
            declared_topic = command_topic
        if not declared_topic:
            raise ContractError(f"command topic missing for {action}")
        if action in fixed:
            spec: dict[str, Any] = {"topic": declared_topic, "payload": fixed[action]}
        elif action in ranged:
            minimum, maximum = ranged[action]
            spec = {"topic": declared_topic, "payload": "{value}", "requires_value": True, "minimum": minimum, "maximum": maximum}
        elif action in {"mode", "preset"}:
            spec = {"topic": declared_topic, "payload": "{value}", "requires_value": True}
        else:
            raise ContractError(f"unsupported producer capability: {action}")
        out[action] = spec
    return out


def validate_catalog(raw: Any) -> tuple[str, list[dict[str, Any]]]:
    if isinstance(raw, list):
        schema_version, rows = "1.0", raw
    elif isinstance(raw, dict):
        schema_version = str(raw.get("schema_version") or "")
        rows = raw.get("devices")
    else:
        raise ContractError("catalog must be an object")
    if not _version_ok(schema_version) or not isinstance(rows, list):
        raise ContractError("unsupported catalog or devices missing")

    seen: set[str] = set()
    devices: list[dict[str, Any]] = []
    for raw_item in rows:
        if not isinstance(raw_item, dict) or not bool(raw_item.get("enabled", True)):
            continue
        item = deepcopy(raw_item)
        device_id = str(item.get("device_id") or "").strip()
        native_type = str(item.get("native_type") or "").strip().lower()
        native_id = str(item.get("native_id") or "").strip()
        device_class = str(item.get("device_class") or item.get("class") or "").strip().lower()
        source = str(item.get("source") or "ksenia").strip().lower()
        if not device_id or device_id in seen or not native_type or not native_id:
            raise ContractError("catalog device identity missing or duplicated")
        if source != "ksenia" or native_type not in ALLOWED_TYPES or device_class not in ALLOWED_CLASSES:
            raise ContractError(f"invalid source/class for {device_id}")
        if not device_id.startswith("ksn_") or len(device_id) != 36 or any(c not in "0123456789abcdef" for c in device_id[4:].lower()):
            raise ContractError(f"invalid device_id for {device_id}")
        caps_raw = item.get("capabilities") or []
        if not isinstance(caps_raw, list):
            raise ContractError(f"capabilities must be a list for {device_id}")
        capabilities = {str(x).strip().lower() for x in caps_raw if str(x).strip()}
        if not capabilities:
            raise ContractError(f"capabilities missing for {device_id}")
        state_topic = _topic(item.get("state_topic"), "state_topic")
        read_only = bool(item.get("read_only", False))
        command_topic = ""
        if item.get("command_topic"):
            command_topic = _topic(item.get("command_topic"), "command_topic")
        if str(item.get("payload_format") or "") not in {"legacy_or_ekonex_envelope_v1", "ksenia_json_state"}:
            raise ContractError(f"unsupported payload_format for {device_id}")
        if _contains_forbidden(device_class, *capabilities, state_topic, command_topic):
            raise ContractError(f"security resource rejected: {device_id}")
        commands = _producer_commands(item, command_topic, capabilities) if command_topic else {}
        if read_only and (command_topic or commands):
            raise ContractError(f"read-only resource declares commands: {device_id}")
        if not read_only and (not command_topic or not commands):
            raise ContractError(f"command payloads missing: {device_id}")
        item.update({
            "device_id": device_id,
            "native_type": native_type,
            "native_id": native_id,
            "device_class": device_class,
            "source": "ksenia",
            "capabilities": sorted(capabilities),
            "state_topic": state_topic,
            "command_topic": command_topic,
            "commands": commands,
            "read_only": read_only,
        })
        seen.add(device_id)
        devices.append(item)
    return schema_version, devices


def _render(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        if value == "{value}":
            return variables.get("value")
        out = value
        for key in ("command_id", "correlation_id", "value"):
            out = out.replace("{" + key + "}", str(variables.get(key, "")))
        return out
    if isinstance(value, list):
        return [_render(x, variables) for x in value]
    if isinstance(value, dict):
        return {str(k): _render(v, variables) for k, v in value.items()}
    return value


class KseniaSmartHomeConsumer:
    def __init__(self, mqtt: MqttTransport, *, stale_after_s: float = 120.0, command_timeout_s: float = 12.0):
        self._mqtt = mqtt
        self._stale_after_s = max(5.0, float(stale_after_s))
        self._command_timeout_s = max(1.0, float(command_timeout_s))
        self._lock = threading.RLock()
        self._manifest: dict[str, Any] | None = None
        self._catalog_version = ""
        self._devices: dict[str, dict[str, Any]] = {}
        self._states: dict[str, dict[str, Any]] = {}
        self._topic_to_device: dict[str, str] = {}
        self._dynamic_topics: set[str] = set()
        self._availability = "unknown"
        self._last_error = ""
        self._pending: dict[str, PendingCommand] = {}
        mqtt.set_message_handler(self.handle_message)
        mqtt.set_connect_handler(self._on_connect)

    def start(self) -> None:
        self._mqtt.connect()

    def stop(self) -> None:
        self._mqtt.disconnect()

    def _on_connect(self) -> None:
        self._mqtt.subscribe(MANIFEST_TOPIC, qos=1)
        self._mqtt.subscribe(CATALOG_TOPIC, qos=1)
        self._mqtt.subscribe(RESULT_FILTER, qos=1)
        with self._lock:
            topics = list(self._dynamic_topics)
        for topic in topics:
            self._mqtt.subscribe(topic, qos=1)

    def handle_message(self, topic: str, payload: str, retained: bool = False) -> None:
        try:
            data = json.loads(payload) if payload.strip().startswith(("{", "[")) else payload
            if topic == MANIFEST_TOPIC:
                manifest = validate_manifest(data)
                with self._lock:
                    self._manifest = manifest
                    self._last_error = ""
                self._replace_dynamic_topics(extra={manifest["availability_topic"]})
                return
            if topic == CATALOG_TOPIC:
                version, devices = validate_catalog(data)
                with self._lock:
                    self._catalog_version = version
                    self._devices = {x["device_id"]: x for x in devices}
                    self._topic_to_device = {x["state_topic"]: x["device_id"] for x in devices}
                    self._states = {k: v for k, v in self._states.items() if k in self._devices}
                    self._last_error = ""
                self._replace_dynamic_topics()
                return
            if topic.startswith(RESULT_PREFIX):
                self._handle_result(topic, data)
                return
            with self._lock:
                manifest = self._manifest or {}
                if topic == manifest.get("availability_topic"):
                    if isinstance(data, dict):
                        self._availability = str(data.get("status") or data.get("state") or "unknown").lower()
                    else:
                        self._availability = str(data or "unknown").lower()
                    return
                device_id = self._topic_to_device.get(topic)
                if device_id:
                    self._states[device_id] = {"value": data, "received_at": time.time(), "retained": bool(retained)}
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)

    def _replace_dynamic_topics(self, extra: set[str] | None = None) -> None:
        with self._lock:
            wanted = {x["state_topic"] for x in self._devices.values()}
            if self._manifest:
                wanted.add(self._manifest["availability_topic"])
            wanted.update(extra or set())
            old = set(self._dynamic_topics)
            self._dynamic_topics = wanted
        for topic in old - wanted:
            self._mqtt.unsubscribe(topic)
        for topic in wanted - old:
            self._mqtt.subscribe(topic, qos=1)

    def _handle_result(self, topic: str, data: Any) -> None:
        if not isinstance(data, dict):
            return
        command_id = str(data.get("command_id") or topic[len(RESULT_PREFIX):]).strip()
        status = str(data.get("status") or "").strip().lower()
        if not command_id or status not in ALLOWED_RESULTS:
            return
        with self._lock:
            pending = self._pending.get(command_id)
            if not pending:
                return
            if data.get("correlation_id") and str(data.get("correlation_id")) != pending.correlation_id:
                return
            pending.status = status
            pending.error = str(data.get("error") or data.get("error_code") or "")
            pending.result = deepcopy(data)
            if status in {"confirmed", "failed", "timeout", "unavailable"}:
                pending.event.set()

    def _command_payload(self, device: dict[str, Any], action: str, value: Any, command_id: str, correlation_id: str) -> tuple[str, Any]:
        spec = (device.get("commands") or {}).get(action)
        if not isinstance(spec, dict):
            raise ContractError("action not declared by producer")
        if "allowed_values" in spec and value not in spec.get("allowed_values", []):
            raise ContractError("value not allowed by producer")
        if value is not None and isinstance(value, (int, float)):
            if spec.get("minimum") is not None and value < float(spec["minimum"]):
                raise ContractError("value below producer minimum")
            if spec.get("maximum") is not None and value > float(spec["maximum"]):
                raise ContractError("value above producer maximum")
        variables = {"command_id": command_id, "correlation_id": correlation_id, "value": value}
        legacy_payload = _render(spec["payload"], variables)
        return str(spec["topic"]), {
            "command_id": command_id,
            "correlation_id": correlation_id,
            "payload": legacy_payload,
        }

    def execute(self, device_id: str, action: str, value: Any = None, *, timeout_s: float | None = None) -> dict[str, Any]:
        action = str(action or "").strip().lower()
        with self._lock:
            if self._availability not in {"online", "available", "connected", "ok"}:
                raise ContractError("ksenia unavailable")
            device = deepcopy(self._devices.get(str(device_id)) or {})
        if not device or device.get("read_only") or not device.get("command_topic"):
            raise ContractError("device is not commandable")
        if action not in set(device.get("capabilities") or []):
            raise ContractError("capability not declared")
        command_id = uuid.uuid4().hex
        correlation_id = uuid.uuid4().hex
        topic, payload = self._command_payload(device, action, value, command_id, correlation_id)
        allowed_topics = {str(device.get("command_topic") or "")}
        allowed_topics.update(str(v) for v in (device.get("command_topics") or {}).values())
        if topic not in allowed_topics:
            raise ContractError("command topic is not catalog allowlisted")
        pending = PendingCommand(command_id, correlation_id, str(device_id), action, time.time())
        with self._lock:
            self._pending[command_id] = pending
        self._mqtt.publish(topic, payload, retain=False, qos=1)
        wait_s = max(0.1, min(float(timeout_s or self._command_timeout_s), 30.0))
        pending.event.wait(wait_s)
        with self._lock:
            if not pending.event.is_set():
                pending.status = "timeout"
                pending.error = "command_result_timeout"
            result = self._pending.pop(command_id)
        return {
            "ok": result.status == "confirmed",
            "command_id": command_id,
            "correlation_id": correlation_id,
            "status": result.status,
            "error": result.error,
            "result": result.result,
        }

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            devices = []
            for item in self._devices.values():
                row = deepcopy(item)
                state = deepcopy(self._states.get(item["device_id"]))
                row["state"] = state
                row["stale"] = not state or now - float(state.get("received_at") or 0) > self._stale_after_s
                devices.append(row)
            status = self._mqtt.status()
            return {
                "detected": self._manifest is not None,
                "compatible": self._manifest is not None and bool(self._catalog_version),
                "availability": self._availability,
                "manifest": deepcopy(self._manifest),
                "catalog_schema_version": self._catalog_version,
                "devices": devices,
                "counts": {klass: sum(1 for x in devices if x.get("device_class") == klass) for klass in sorted(ALLOWED_CLASSES)},
                "ha_dedupe_entity_ids": sorted({str(x.get("home_assistant_entity_id") or x.get("ha_entity_id") or "").lower() for x in devices if x.get("home_assistant_entity_id") or x.get("ha_entity_id")}),
                "mqtt_connected": bool(getattr(status, "connected", False)),
                "last_error": self._last_error or str(getattr(status, "last_error", "") or ""),
            }
