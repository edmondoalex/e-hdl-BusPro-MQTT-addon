import json
import threading
import unittest
from dataclasses import dataclass

from e_hdl_buspro_mqtt.app.ksenia_consumer import (
    CATALOG_TOPIC,
    MANIFEST_TOPIC,
    RESULT_FILTER,
    RESULT_PREFIX,
    ContractError,
    KseniaSmartHomeConsumer,
    validate_catalog,
)


@dataclass
class _Status:
    connected: bool = True
    last_error: str | None = None


class FakeMqtt:
    def __init__(self):
        self.subscriptions = set()
        self.published = []
        self.handler = None
        self.connect_handler = None
        self.connected = False
        self.auto_result = None

    def set_message_handler(self, handler): self.handler = handler
    def set_connect_handler(self, handler): self.connect_handler = handler
    def connect(self):
        self.connected = True
        if self.connect_handler: self.connect_handler()
    def disconnect(self): self.connected = False
    def subscribe(self, topic, qos=0): self.subscriptions.add(topic)
    def unsubscribe(self, topic): self.subscriptions.discard(topic)
    def status(self): return _Status(self.connected)
    def publish(self, topic, payload, retain=False, qos=0):
        self.published.append((topic, payload, retain, qos))
        if self.auto_result and isinstance(payload, dict):
            data = {
                "command_id": payload["command_id"],
                "correlation_id": payload["correlation_id"],
                "status": self.auto_result,
            }
            threading.Timer(0.01, lambda: self.handler(RESULT_PREFIX + payload["command_id"], json.dumps(data), False)).start()


def manifest():
    return {
        "schema_version": "1.0",
        "integration_id": "ksenia",
        "display_name": "Ksenia",
        "availability_topic": "e-safe/status",
        "mqtt_prefix": "e-safe",
        "capabilities": ["on", "off", "temperature"],
        "catalog_topic": CATALOG_TOPIC,
        "command_result_topic_template": RESULT_PREFIX + "{command_id}",
        "future_field": {"ignored": True},
    }


def catalog():
    return {
        "schema_version": "1.0",
        "devices": [
            {
                "device_id": "ksn_00000000000000000000000000000036",
                "native_type": "outputs",
                "native_id": "36",
                "name": "Luce ingresso",
                "class": "dimmer",
                "source": "ksenia",
                "capabilities": ["on", "off"],
                "state_topic": "e-safe/outputs/36",
                "command_topic": "e-safe/cmd/output/36",
                "payload_format": "legacy_or_ekonex_envelope_v1",
                "read_only": False,
                "enabled": True,
                "home_assistant_entity_id": "light.e_safe_out_36",
                "unknown_future_field": 42,
            },
            {
                "device_id": "ksn_00000000000000000000000000000001",
                "native_type": "domus",
                "native_id": "1",
                "name": "Temperatura sala",
                "class": "environment_sensor",
                "source": "ksenia",
                "capabilities": ["temperature", "humidity"],
                "state_topic": "e-safe/domus/1",
                "command_topic": None,
                "payload_format": "ksenia_json_state",
                "read_only": True,
                "enabled": True,
            },
        ],
    }


class ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.mqtt = FakeMqtt()
        self.consumer = KseniaSmartHomeConsumer(self.mqtt, command_timeout_s=0.05)
        self.consumer.start()

    def seed(self):
        self.consumer.handle_message(MANIFEST_TOPIC, json.dumps(manifest()), True)
        self.consumer.handle_message(CATALOG_TOPIC, json.dumps(catalog()), True)
        self.consumer.handle_message("e-safe/status", "online", True)

    def test_bootstrap_and_exact_catalog_subscriptions(self):
        self.seed()
        self.assertEqual(
            self.mqtt.subscriptions,
            {MANIFEST_TOPIC, CATALOG_TOPIC, RESULT_FILTER, "e-safe/status", "e-safe/outputs/36", "e-safe/domus/1"},
        )

    def test_retained_state_unknown_fields_and_dedupe(self):
        self.seed()
        self.consumer.handle_message("e-safe/outputs/36", json.dumps({"STA": "ON", "future": 1}), True)
        snap = self.consumer.snapshot()
        self.assertTrue(snap["compatible"])
        self.assertEqual(snap["devices"][0]["state"]["value"]["STA"], "ON")
        self.assertEqual(snap["ha_dedupe_entity_ids"], ["light.e_safe_out_36"])

    def test_command_uses_only_catalog_topic_and_requires_confirmed_ack(self):
        self.seed()
        self.mqtt.auto_result = "confirmed"
        result = self.consumer.execute("ksn_00000000000000000000000000000036", "on", timeout_s=1)
        self.assertTrue(result["ok"])
        topic, payload, retained, qos = self.mqtt.published[-1]
        self.assertEqual(topic, "e-safe/cmd/output/36")
        self.assertEqual(payload["payload"], "ON")
        self.assertFalse(retained)
        self.assertEqual(qos, 1)

    def test_timeout_is_not_success(self):
        self.seed()
        result = self.consumer.execute("ksn_00000000000000000000000000000036", "off", timeout_s=0.02)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "timeout")

    def test_thermostat_uses_exact_producer_command_topic(self):
        self.consumer.handle_message(MANIFEST_TOPIC, json.dumps(manifest()), True)
        thermostat = {
            "schema_version": "1.0",
            "devices": [{
                "device_id": "ksn_00000000000000000000000000000013",
                "native_type": "thermostats", "native_id": "13", "name": "Clima",
                "class": "thermostat", "capabilities": ["temperature", "mode", "preset"],
                "state_topic": "e-safe/thermostats/13",
                "command_topic": "e-safe/cmd/thermostat/13",
                "command_topics": {
                    "temperature": "e-safe/cmd/thermostat/13/temperature",
                    "mode": "e-safe/cmd/thermostat/13/mode",
                    "preset": "e-safe/cmd/thermostat/13/preset_mode",
                },
                "payload_format": "legacy_or_ekonex_envelope_v1",
                "read_only": False, "enabled": True, "source": "ksenia",
            }],
        }
        self.consumer.handle_message(CATALOG_TOPIC, json.dumps(thermostat), True)
        self.consumer.handle_message("e-safe/status", "online", True)
        self.mqtt.auto_result = "confirmed"
        result = self.consumer.execute("ksn_00000000000000000000000000000013", "temperature", 21.5, timeout_s=1)
        self.assertTrue(result["ok"])
        self.assertEqual(self.mqtt.published[-1][0], "e-safe/cmd/thermostat/13/temperature")
        self.assertEqual(self.mqtt.published[-1][1]["payload"], 21.5)

    def test_offline_blocks_publish(self):
        self.seed()
        self.consumer.handle_message("e-safe/status", "offline", False)
        with self.assertRaises(ContractError):
            self.consumer.execute("ksn_00000000000000000000000000000036", "on")
        self.assertEqual(self.mqtt.published, [])

    def test_missing_producer_is_non_blocking(self):
        snap = self.consumer.snapshot()
        self.assertFalse(snap["detected"])
        self.assertEqual(snap["devices"], [])

    def test_restart_rehydrates_from_retained_contract(self):
        self.seed()
        second_mqtt = FakeMqtt()
        second = KseniaSmartHomeConsumer(second_mqtt)
        second.start()
        second.handle_message(MANIFEST_TOPIC, json.dumps(manifest()), True)
        second.handle_message(CATALOG_TOPIC, json.dumps(catalog()), True)
        self.assertEqual(len(second.snapshot()["devices"]), 2)

    def test_catalog_refresh_unsubscribes_removed_state(self):
        self.seed()
        reduced = catalog()
        reduced["devices"] = reduced["devices"][:1]
        self.consumer.handle_message(CATALOG_TOPIC, json.dumps(reduced), True)
        self.assertNotIn("e-safe/domus/1", self.mqtt.subscriptions)

    def test_security_catalog_entries_are_hard_rejected(self):
        forbidden = catalog()
        forbidden["devices"] = [{
            "device_id": "ksn_00000000000000000000000000000099", "native_type": "partitions", "native_id": "1",
            "class": "switch", "source": "ksenia", "capabilities": ["arm"],
            "state_topic": "e-safe/partitions/1", "command_topic": "e-safe/cmd/partition/1",
            "payload_format": "legacy_or_ekonex_envelope_v1", "read_only": False, "enabled": True,
        }]
        with self.assertRaises(ContractError):
            validate_catalog(forbidden)

    def test_non_producer_family_is_rejected(self):
        zone = catalog()
        zone["devices"] = [{
            "device_id": "ksn_00000000000000000000000000000074", "native_type": "zones", "native_id": "74",
            "class": "environment_sensor", "source": "ksenia", "capabilities": ["temperature"],
            "state_topic": "e-safe/zones/74", "command_topic": None,
            "payload_format": "ksenia_json_state", "read_only": True, "enabled": True,
        }]
        with self.assertRaises(ContractError):
            validate_catalog(zone)


if __name__ == "__main__":
    unittest.main()
