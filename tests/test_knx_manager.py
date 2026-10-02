import tempfile
import unittest
from pathlib import Path

from e_hdl_buspro_mqtt.app.knx_manager import KnxCatalogStore


class KnxCatalogStoreTests(unittest.TestCase):
    def test_sync_only_imports_knx_and_preserves_stable_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnxCatalogStore(str(Path(tmp) / "knx.json"))
            states = {
                "light.kitchen": {"state": "on", "attributes": {"friendly_name": "Kitchen", "brightness": 128}},
                "light.other": {"state": "off", "attributes": {}},
            }
            registry = [
                {"id": "registry-stable", "entity_id": "light.kitchen", "platform": "knx"},
                {"id": "other", "entity_id": "light.other", "platform": "hue"},
            ]
            result = store.sync(registry, states, {"name": "House"})
            self.assertEqual(1, result["total"])
            first = next(iter(store.load()["devices"].values()))
            self.assertEqual("dimmer", first["device_class"])
            self.assertEqual(["on", "off", "level"], first["capabilities"])
            self.assertFalse(first["enabled"])
            stable_id = first["device_id"]

            registry[0]["entity_id"] = "light.renamed"
            states["light.renamed"] = states.pop("light.kitchen")
            store.sync(registry, states)
            second = store.load()["devices"][stable_id]
            self.assertEqual("light.renamed", second["entity_id"])

    def test_catalog_is_opt_in_and_read_only_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnxCatalogStore(str(Path(tmp) / "knx.json"))
            state = {"entity_id": "cover.office", "state": "closed", "attributes": {"supported_features": 4}}
            store.sync([{"id": "cover-id", "entity_id": "cover.office", "platform": "knx"}], {"cover.office": state})
            self.assertEqual([], store.catalog({"cover.office": state}))
            device_id = next(iter(store.load()["devices"]))
            store.update(device_id, enabled=True)
            row = store.catalog({"cover.office": state})[0]
            self.assertTrue(row["read_only"])
            self.assertEqual(["open", "close", "stop", "position"], row["capabilities"])

    def test_missing_entity_becomes_orphan_without_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = KnxCatalogStore(str(Path(tmp) / "knx.json"))
            store.sync([{"id": "one", "entity_id": "sensor.temp", "platform": "knx"}], {"sensor.temp": {"state": "20", "attributes": {"device_class": "temperature"}}})
            device_id = next(iter(store.load()["devices"]))
            store.sync([], {})
            self.assertTrue(store.load()["devices"][device_id]["orphaned"])


if __name__ == "__main__":
    unittest.main()
