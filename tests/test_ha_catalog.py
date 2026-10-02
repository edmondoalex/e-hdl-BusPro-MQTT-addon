import unittest

from e_hdl_buspro_mqtt.app.ha_catalog import build_ha_catalog


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

    def test_lock_page_stays_on_existing_safety_path(self):
        rows = build_ha_catalog(
            [{"entity_id": "switch.gate", "page": "locks", "group": "Esterno"}],
            {"switch.gate": {"state": "OFF"}},
            {},
        )
        self.assertEqual([], rows)

    def test_unavailable_entity_remains_catalogued(self):
        rows = build_ha_catalog(
            [{"entity_id": "switch.heater", "page": "extra"}],
            {"switch.heater": {"state": "unavailable"}},
            {},
        )
        self.assertEqual(["extra"], rows[0]["categories"])
        self.assertFalse(rows[0]["available"])
        self.assertTrue(rows[0]["stale"])


if __name__ == "__main__":
    unittest.main()
