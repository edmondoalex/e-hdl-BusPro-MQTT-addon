import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from e_hdl_buspro_mqtt.app.organization import OrganizationStore, canonical_key, default_icon


class OrganizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "organization.json")
        self.store = OrganizationStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def hdl(self):
        return [
            {"name": "Luce cucina", "addr": "1.10.1", "group": "CUCINA", "type": "light"},
            {"name": "Dimmer sala", "addr": "1.11.2", "group": "SALA", "type": "dimmer"},
        ]

    def test_hdl_migration_is_idempotent_and_keeps_stable_keys(self):
        first = self.store.migrate_hdl(self.hdl(), ["# PIANO TERRA", "CUCINA", "SALA"])
        second = self.store.migrate_hdl(self.hdl(), ["# PIANO TERRA", "CUCINA", "SALA"])
        self.assertEqual(first, second)
        self.assertIn("hdl:1.10.1", second["devices"])
        self.assertEqual("room-cucina", second["devices"]["hdl:1.10.1"]["room_id"])

    def test_same_native_id_is_unambiguous_across_sources(self):
        data = self.store.sync_devices([
            {"source": "hdl", "device_id": "1", "name": "HDL", "device_class": "switch"},
            {"source": "ksenia", "device_id": "1", "name": "Ksenia", "device_class": "switch"},
        ])
        self.assertIn("hdl:1", data["devices"])
        self.assertIn("ksenia:1", data["devices"])

    def test_ksenia_survives_rename_restart_refresh_and_offline(self):
        device_id = "ksn_00000000000000000000000000000001"
        self.store.sync_devices([{"source":"ksenia","device_id":device_id,"name":"Prima","device_class":"light"}])
        restarted = OrganizationStore(self.path)
        renamed = restarted.sync_devices([{"source":"ksenia","device_id":device_id,"name":"Dopo","device_class":"light"}])
        self.assertEqual("Dopo", renamed["devices"][canonical_key("ksenia", device_id)]["name"])
        offline = restarted.sync_devices([])
        self.assertTrue(offline["devices"][canonical_key("ksenia", device_id)]["orphaned"])
        online = restarted.sync_devices([{"source":"ksenia","device_id":device_id,"name":"Dopo","device_class":"light"}])
        self.assertFalse(online["devices"][canonical_key("ksenia", device_id)]["orphaned"])

    def test_assignments_and_valid_icon_override_persist(self):
        self.store.sync_devices([{"source":"hdl","device_id":"1.2.3","name":"Luce","device_class":"light"}])
        self.store.replace_structure({
            "floors":[{"id":"floor-pt","name":"Piano terra"}],
            "rooms":[{"id":"room-cucina","name":"Cucina","floor_id":"floor-pt"}],
            "groups":[{"id":"group-sera","name":"Sera"}],
        })
        item = self.store.assign({"source":"hdl","device_id":"1.2.3","floor_id":"floor-pt","room_id":"room-cucina","group_ids":["group-sera"],"icon_override":"mdi:ceiling-light"})
        self.assertEqual("mdi:ceiling-light", item["icon_override"])
        self.assertEqual("mdi:ceiling-light", self.store.snapshot()["devices"]["hdl:1.2.3"]["icon"])

    def test_invalid_icon_and_references_are_rejected(self):
        self.store.sync_devices([{"source":"hdl","device_id":"1.2.3","name":"Luce","device_class":"light"}])
        with self.assertRaises(ValueError):
            self.store.assign({"source":"hdl","device_id":"1.2.3","icon_override":"javascript:bad"})
        with self.assertRaises(ValueError):
            self.store.assign({"source":"hdl","device_id":"1.2.3","floor_id":"missing"})

    def test_default_icons(self):
        self.assertEqual("mdi:lightbulb", default_icon("light"))
        self.assertEqual("mdi:window-shutter", default_icon("cover"))
        self.assertEqual("mdi:devices", default_icon("future_class"))

    def test_atomic_write_backup_and_corrupt_recovery(self):
        self.store.save(self.store.empty())
        data = self.store.load()
        data["floors"] = [{"id":"floor-main","name":"Main"}]
        self.store.save(data)
        self.assertTrue(os.path.isfile(self.path + ".bak"))
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{broken")
        recovered = self.store.load()
        self.assertEqual(1, recovered["schema_version"])
        self.assertTrue(any(".corrupt." in name for name in os.listdir(self.temp.name)))

    def test_removed_device_is_preserved_as_orphan(self):
        self.store.sync_devices([{"source":"hdl","device_id":"1.2.3","name":"Luce","device_class":"light"}])
        data = self.store.sync_devices([])
        self.assertIn("hdl:1.2.3", data["devices"])
        self.assertTrue(data["devices"]["hdl:1.2.3"]["orphaned"])

    def test_migration_collision_is_reported(self):
        with self.assertRaises(ValueError):
            self.store.migrate_hdl([], ["# TERRA", "SALA", "# PRIMO", "SALA"])

    def test_identical_sync_does_not_rewrite_persistent_file(self):
        devices = [{"source":"hdl","device_id":"1.2.3","name":"Luce","device_class":"light"}]
        self.store.sync_devices(devices)
        before = os.stat(self.path).st_mtime_ns
        time.sleep(0.01)
        self.store.sync_devices(devices)
        self.assertEqual(before, os.stat(self.path).st_mtime_ns)

    def test_concurrent_assignments_do_not_lose_updates(self):
        self.store.sync_devices([
            {"source":"hdl","device_id":"1.2.3","name":"Uno","device_class":"light"},
            {"source":"ksenia","device_id":"ksn_1","name":"Due","device_class":"switch"},
        ])
        self.store.replace_structure({"groups":[{"id":"group-a","name":"A"},{"id":"group-b","name":"B"}]})
        barrier = threading.Barrier(3)
        errors = []
        def assign(source, device_id, group_id):
            try:
                barrier.wait()
                self.store.assign({"source":source,"device_id":device_id,"group_ids":[group_id]})
            except Exception as exc:
                errors.append(exc)
        threads = [
            threading.Thread(target=assign, args=("hdl","1.2.3","group-a")),
            threading.Thread(target=assign, args=("ksenia","ksn_1","group-b")),
        ]
        for thread in threads: thread.start()
        barrier.wait()
        for thread in threads: thread.join()
        self.assertEqual([], errors)
        data = self.store.load()
        self.assertEqual(["group-a"], data["devices"]["hdl:1.2.3"]["group_ids"])
        self.assertEqual(["group-b"], data["devices"]["ksenia:ksn_1"]["group_ids"])

    def test_slug_collisions_and_invalid_device_metadata_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.migrate_hdl([], ["# Piano A", "# Piano-A"])
        with self.assertRaises(ValueError):
            self.store.sync_devices([{"source":"hdl","device_id":"1","name":"bad\u0001name","device_class":"light"}])

    def test_admin_ui_is_responsive_and_uses_organization_api(self):
        root = Path(__file__).resolve().parents[1]
        index = (root / "e_hdl_buspro_mqtt" / "app" / "static" / "index.html").read_text(encoding="utf-8")
        script = (root / "e_hdl_buspro_mqtt" / "app" / "static" / "hub" / "organization.js").read_text(encoding="utf-8")
        self.assertIn('static/hub/organization.js', index)
        self.assertIn("api/organization", script)
        self.assertIn("@media(max-width:850px)", script)
        self.assertIn("data-field=", script)


if __name__ == "__main__":
    unittest.main()
