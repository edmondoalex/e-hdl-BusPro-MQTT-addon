import unittest
import tempfile
from pathlib import Path

from e_hdl_buspro_mqtt.app.ha_catalog import build_ha_catalog
from e_hdl_buspro_mqtt.app.store import StateStore


class HomeAssistantCatalogTests(unittest.TestCase):
    def test_existing_selection_keeps_page_group_icon_and_commands(self):
        rows = build_ha_catalog(
            [{"entity_id": "light.sala", "name": "Lampada Sala", "page": "lights", "group": "Zona giorno", "icon": "mdi:floor-lamp"}],
            {"light.sala": {"state": "ON", "brightness": 120}},
            {"light.sala": {"dimmable": True}},
        )
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("light.sala", row["device_id"])
        self.assertEqual(["lights"], row["categories"])
        self.assertEqual("Zona giorno", row["room_name"])
        self.assertEqual("mdi:floor-lamp", row["icon_override"])
        self.assertEqual(["on", "off", "level"], row["capabilities"])
        self.assertTrue(row["available"])
        self.assertFalse(row["presentation_authoritative"])

    def test_lock_page_is_available_in_multibus_organization(self):
        rows = build_ha_catalog(
            [{"entity_id": "lock.gate", "page": "locks", "group": "Esterno"}],
            {"lock.gate": {"state": "locked"}},
            {"lock.gate": {"open_supported": True}},
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("lock", rows[0]["device_class"])
        self.assertEqual(["security"], rows[0]["categories"])
        self.assertEqual(["lock", "unlock", "open"], rows[0]["capabilities"])

    def test_legacy_security_switch_and_cover_keep_native_semantics(self):
        rows = build_ha_catalog(
            [
                {"entity_id": "switch.gate_pulse", "page": "locks", "name": "Cancello"},
                {"entity_id": "cover.garage", "domain": "cover", "page": "locks", "name": "Portone"},
            ],
            {"switch.gate_pulse": {"state": "off"}, "cover.garage": {"state": "closed"}},
            {},
        )
        self.assertEqual("switch", rows[0]["device_class"])
        self.assertEqual(["on", "off"], rows[0]["capabilities"])
        self.assertEqual("cover", rows[1]["device_class"])
        self.assertEqual(["open", "close", "stop"], rows[1]["capabilities"])
        self.assertEqual([["security"], ["security"]], [row["categories"] for row in rows])

    def test_unavailable_entity_remains_catalogued(self):
        rows = build_ha_catalog(
            [{"entity_id": "switch.heater", "page": "extra"}],
            {"switch.heater": {"state": "unavailable"}},
            {},
        )
        self.assertEqual(["extra"], rows[0]["categories"])
        self.assertFalse(rows[0]["available"])
        self.assertTrue(rows[0]["stale"])

    def test_external_policy_controls_exposure_and_commands(self):
        configured = [{"entity_id": "cover.gate", "page": "locks", "enabled": False, "read_only": True}]
        self.assertEqual([], build_ha_catalog(configured, {"cover.gate": {"state": "closed"}}, {}))
        organization = build_ha_catalog(configured, {}, {}, include_disabled=True)
        self.assertEqual(1, len(organization))
        self.assertTrue(organization[0]["read_only"])

    def test_read_only_external_device_keeps_state_but_not_command_permission(self):
        rows = build_ha_catalog(
            [{"entity_id": "lock.office", "page": "locks", "enabled": True, "read_only": True}],
            {"lock.office": {"state": "locked"}},
            {},
        )
        self.assertEqual(["lock", "unlock"], rows[0]["capabilities"])
        self.assertTrue(rows[0]["read_only"])

    def test_external_exposure_and_command_policies_are_independent_and_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(str(Path(tmp) / "state.json"))
            store.add_ha_device({"entity_id": "lock.office", "page": "locks", "name": "Porta ufficio"})
            updated = store.update_ha_device_policy("lock.office", enabled=False, read_only=False)
            self.assertFalse(updated["enabled"])
            self.assertFalse(updated["read_only"])
            restarted = StateStore(str(Path(tmp) / "state.json")).list_ha_devices()[0]
            self.assertFalse(restarted["enabled"])
            self.assertFalse(restarted["read_only"])


if __name__ == "__main__":
    unittest.main()
