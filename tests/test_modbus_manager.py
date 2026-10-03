import json
import tempfile
import unittest
from pathlib import Path

from e_hdl_buspro_mqtt.app.modbus_manager import ModbusManager, ModbusStore, ferroli_omnia_m32_profile, validate_connection, validate_register


class ModbusValidationTests(unittest.TestCase):
    def test_ferroli_ui_adds_pumps_and_selects_gateway_mode(self):
        index = (Path(__file__).resolve().parents[1] / "e_hdl_buspro_mqtt" / "app" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="ferroliAddPump"', index)
        self.assertIn('value="same">Stesso gateway della prima pompa', index)
        self.assertIn('value="different">Gateway differente', index)
        self.assertIn("hydrateFerroliForm()", index)

    def test_connection_types_and_serial_safety(self):
        self.assertEqual(502, validate_connection({"name": "PDC", "type": "tcp", "host": "192.168.1.4"})["port"])
        serial = validate_connection({"name": "RS485", "type": "serial", "port": "/dev/ttyUSB0", "baudrate": 19200, "parity": "E"})
        self.assertEqual("serial", serial["type"])
        with self.assertRaises(ValueError):
            validate_connection({"name": "Bad", "type": "serial", "port": "COM1"})

    def test_register_bounds_and_write_limits(self):
        row = validate_register({"name": "Mandata", "address": 100, "data_type": "int16", "scale": 0.1, "min": 5, "max": 60})
        self.assertEqual(0.1, row["scale"])
        with self.assertRaises(ValueError):
            validate_register({"name": "Bad", "address": 70000})
        with self.assertRaises(ValueError):
            validate_register({"name": "Bad", "address": 1, "min": 60, "max": 5})
        with self.assertRaises(ValueError):
            validate_register({"name": "Bad sensor", "address": 1, "entity_type": "sensor", "register_type": "coil"})


class ModbusStoreTests(unittest.TestCase):
    def _configured(self, tmp):
        store = ModbusStore(str(Path(tmp) / "modbus.json"))
        store.put_connection({"name": "PDC LAN", "type": "tcp", "host": "192.168.1.50"})
        store.put_profile({"name": "PDC Test", "manufacturer": "Ekonex", "model": "Lab", "registers": [
            {"name": "Mandata", "entity_type": "sensor", "address": 10, "register_type": "input", "data_type": "int16", "scale": 0.1, "unit": "°C", "device_class": "temperature"},
            {"name": "Consenso", "entity_type": "switch", "address": 20, "register_type": "coil", "data_type": "uint16", "writable": True},
        ]})
        store.put_device({"name": "Pompa 1", "connection_id": "pdc_lan", "profile_id": "pdc_test", "slave": 3})
        return store

    def test_profile_renders_deterministic_home_assistant_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml = self._configured(tmp).render_home_assistant()
            self.assertIn('type: tcp', yaml)
            self.assertIn('slave: 3', yaml)
            self.assertIn('unique_id: "econtrol_modbus_pompa_1_mandata"', yaml)
            self.assertIn('scale: 0.1', yaml)
            self.assertIn('write_type: coil', yaml)

    def test_registry_catalog_is_opt_in_and_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._configured(tmp)
            states = {"sensor.pompa_1_mandata": {"state": "35.2", "attributes": {"device_class": "temperature"}}}
            registry = [{"id": "stable", "platform": "modbus", "entity_id": "sensor.pompa_1_mandata", "name": "Mandata"}]
            self.assertEqual(1, store.sync_catalog(registry, states)["total"])
            self.assertEqual([], store.catalog(states))
            device_id = next(iter(store.load()["catalog"]))
            store.update_catalog(device_id, {"enabled": True})
            self.assertEqual("temperature_sensor", store.catalog(states)[0]["device_class"])
            registry[0]["entity_id"] = "sensor.mandata_rinominata"
            store.sync_catalog(registry, {"sensor.mandata_rinominata": states["sensor.pompa_1_mandata"]})
            self.assertIn(device_id, store.load()["catalog"])

    def test_apply_adds_include_once_and_refuses_existing_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._configured(tmp)
            Path(tmp, "configuration.yaml").write_text("default_config:\n", encoding="utf-8")
            manager = ModbusManager(store.path, token="", config_dir=tmp)
            first = manager.apply(); manager.apply()
            content = Path(tmp, "configuration.yaml").read_text(encoding="utf-8")
            self.assertEqual(1, content.count(first["include"]))
            self.assertTrue(Path(tmp, "modbus_econtrol.yaml").exists())
        with tempfile.TemporaryDirectory() as tmp:
            store = self._configured(tmp)
            Path(tmp, "configuration.yaml").write_text("modbus:\n  - name: legacy\n", encoding="utf-8")
            manager = ModbusManager(store.path, token="", config_dir=tmp)
            with self.assertRaisesRegex(RuntimeError, "already contains"):
                manager.apply()

    def test_backup_document_is_json_roundtrip_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._configured(tmp).load()
            self.assertEqual(data, json.loads(json.dumps(data)))

    def test_ferroli_omnia_profile_defaults_to_safe_read_only_addresses(self):
        profile = ferroli_omnia_m32_profile()
        self.assertEqual([14, 15, 16], [row["address"] for row in profile["registers"]])
        self.assertTrue(all(row["entity_type"] == "sensor" for row in profile["registers"]))
        self.assertTrue(all(not row["writable"] for row in profile["registers"]))

    def test_ferroli_omnia_provisions_two_unique_slaves(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ModbusStore(str(Path(tmp) / "modbus.json"))
            result = store.provision_ferroli_omnia({
                "host": "192.168.1.60", "port": 502,
                "pumps": [{"name": "OMNIA 1", "slave": 1}, {"name": "OMNIA 2", "slave": 2}],
            })
            self.assertFalse(result["commands_enabled"])
            self.assertEqual({1, 2}, {row["slave"] for row in result["pumps"]})
            yaml = store.render_home_assistant()
            self.assertIn('host: "192.168.1.60"', yaml)
            self.assertIn("address: 14", yaml)
            self.assertIn("input_type: holding", yaml)
            self.assertEqual(1, yaml.count("  sensors:"))
            with self.assertRaisesRegex(ValueError, "different slave IDs"):
                store.provision_ferroli_omnia({
                    "host": "192.168.1.60",
                    "pumps": [{"name": "A", "slave": 1}, {"name": "B", "slave": 1}],
                })

    def test_ferroli_omnia_supports_added_pumps_on_different_gateways(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ModbusStore(str(Path(tmp) / "modbus.json"))
            result = store.provision_ferroli_omnia({
                "host": "192.168.1.60", "port": 502,
                "pumps": [
                    {"name": "OMNIA Casa", "slave": 1, "gateway_mode": "primary"},
                    {"name": "OMNIA Uffici", "slave": 2, "gateway_mode": "same"},
                    {"name": "OMNIA Magazzino", "slave": 1, "gateway_mode": "different", "host": "192.168.1.61", "port": 1502},
                ],
            })
            self.assertEqual(2, len(result["connections"]))
            self.assertEqual(
                ["ferroli_omnia_gateway", "ferroli_omnia_gateway", "ferroli_omnia_gateway_2"],
                [pump["connection_id"] for pump in result["pumps"]],
            )
            yaml = store.render_home_assistant()
            self.assertIn('host: "192.168.1.60"', yaml)
            self.assertIn('host: "192.168.1.61"', yaml)
            self.assertIn("port: 1502", yaml)

    def test_ferroli_omnia_allows_same_slave_on_different_gateways(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ModbusStore(str(Path(tmp) / "modbus.json"))
            result = store.provision_ferroli_omnia({
                "host": "192.168.1.60",
                "pumps": [
                    {"name": "OMNIA 1", "slave": 1},
                    {"name": "OMNIA 2", "slave": 1, "gateway_mode": "different", "host": "192.168.1.61"},
                ],
            })
            self.assertEqual(2, len(result["connections"]))

    def test_ferroli_omnia_rejects_missing_second_gateway_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ModbusStore(str(Path(tmp) / "modbus.json"))
            with self.assertRaisesRegex(ValueError, "host is required"):
                store.provision_ferroli_omnia({
                    "host": "192.168.1.60",
                    "pumps": [{"name": "A", "slave": 1}, {"name": "B", "slave": 1, "gateway_mode": "different"}],
                })
            with self.assertRaisesRegex(ValueError, "different names"):
                store.provision_ferroli_omnia({
                    "host": "192.168.1.60",
                    "pumps": [{"name": "OMNIA", "slave": 1}, {"name": "OMNIA", "slave": 2}],
                })

    def test_ferroli_omnia_configuration_survives_restart_and_replaces_removed_pumps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "modbus.json")
            store = ModbusStore(path)
            store.provision_ferroli_omnia({
                "host": "192.168.1.60", "commands_enabled": True,
                "pumps": [
                    {"name": "OMNIA Casa", "slave": 1},
                    {"name": "OMNIA Uffici", "slave": 1, "gateway_mode": "different", "host": "192.168.1.61"},
                ],
            })
            restarted = ModbusStore(path)
            saved = restarted.load()["ferroli_omnia"]
            self.assertEqual("192.168.1.60", saved["host"])
            self.assertTrue(saved["commands_enabled"])
            self.assertEqual("different", saved["pumps"][1]["gateway_mode"])
            self.assertEqual("192.168.1.61", saved["pumps"][1]["host"])

            restarted.provision_ferroli_omnia({
                "host": "192.168.1.60",
                "pumps": [{"name": "OMNIA Casa", "slave": 4}],
            })
            current = ModbusStore(path).load()
            self.assertEqual(["OMNIA Casa"], [row["name"] for row in current["devices"].values() if row["profile_id"] == "ferroli_omnia_m_3_2"])
            self.assertNotIn("ferroli_omnia_gateway_2", current["connections"])
            self.assertEqual(4, current["ferroli_omnia"]["pumps"][0]["slave"])

    def test_ferroli_omnia_commands_require_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ModbusStore(str(Path(tmp) / "modbus.json"))
            store.provision_ferroli_omnia({
                "host": "192.168.1.60", "commands_enabled": True,
                "pumps": [{"name": "OMNIA", "slave": 7}],
            })
            profile = store.load()["profiles"]["ferroli_omnia_m_3_2"]
            self.assertTrue(profile["commands_enabled"])
            self.assertTrue(all(row["entity_type"] == "switch" for row in profile["registers"]))
            yaml = store.render_home_assistant()
            self.assertIn("write_type: holding", yaml)
            self.assertIn("  switches:", yaml)
            self.assertNotIn("  switchs:", yaml)


if __name__ == "__main__":
    unittest.main()
