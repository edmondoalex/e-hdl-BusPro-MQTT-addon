import tempfile
import unittest
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from e_hdl_buspro_mqtt.app.bticino_manager import BticinoCatalogStore, BticinoManager, MyHomeComponentInstaller


class BticinoCatalogStoreTests(unittest.TestCase):
    def test_direct_netatmo_uses_real_module_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = BticinoCatalogStore(str(Path(tmp) / "bticino.json"))
            store.sync_direct_netatmo([
                {"id": "bridge", "type": "NAPlug", "module_name": "Bridge casa"},
                {"id": "thermostat", "type": "NATherm1", "module_name": "Termostato sala", "room_name": "Sala"},
                {"id": "valve", "type": "NRV", "module_name": "Valvola cucina", "room_id": "room-kitchen", "room_name": "Cucina"},
                {"id": "weather", "type": "NAMain", "module_name": "Meteo esterno", "dashboard_data": {"Temperature": 18.2}},
            ])
            rows = {row["native_id"]: row for row in store.load()["integrations"]["home_plus_control"]["devices"].values()}
            self.assertEqual("gateway", rows["bridge"]["domain"])
            self.assertTrue(rows["bridge"]["read_only"])
            self.assertEqual("climate", rows["thermostat"]["domain"])
            self.assertEqual("climate", rows["valve"]["domain"])
            self.assertEqual("sensor", rows["weather"]["domain"])
            self.assertEqual("Valvola cucina", rows["valve"]["name"])
            self.assertEqual("Cucina", rows["valve"]["group"])
            self.assertEqual("room-kitchen", rows["valve"]["room_id"])
            store.update("home_plus_control", rows["valve"]["device_id"], enabled=True, read_only=False)
            valve = next(item for item in store.catalog("home_plus_control", {}) if item["native_id"] == "valve")
            self.assertEqual("room-kitchen", valve["room_id"])

    def test_direct_catalog_recovers_room_from_legacy_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = BticinoCatalogStore(str(Path(tmp) / "bticino.json"))
            store.sync_direct_netatmo([{"id": "valve", "type": "NRV", "home_id": "home", "room_id": "room", "module_name": "Valvola"}])
            data = store.load()
            device_id, row = next(iter(data["integrations"]["home_plus_control"]["devices"].items()))
            row.pop("room_id", None)
            row["state"]["attributes"]["room_id"] = "room"
            store.save(data)
            store.update("home_plus_control", device_id, enabled=True, read_only=False)
            self.assertEqual("room", store.catalog("home_plus_control", {})[0]["room_id"])

    def test_sources_are_independent_and_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = BticinoCatalogStore(str(Path(tmp) / "bticino.json"))
            states = {
                "light.scs_kitchen": {"state": "on", "attributes": {"friendly_name": "SCS Kitchen", "brightness": 128}},
                "switch.home_plus_plug": {"state": "off", "attributes": {"friendly_name": "Home+ Plug"}},
            }
            registry = [
                {"id": "scs-1", "entity_id": "light.scs_kitchen", "platform": "myhome", "device_id": "dev-scs"},
                {"id": "cloud-1", "entity_id": "switch.home_plus_plug", "platform": "netatmo", "device_id": "dev-cloud"},
                {"id": "other", "entity_id": "light.other", "platform": "hue"},
            ]
            devices = [
                {"id": "dev-scs", "manufacturer": "BTicino", "model": "F454"},
                {"id": "dev-cloud", "manufacturer": "Legrand", "model": "K4003C"},
            ]
            self.assertEqual(1, store.sync("myhome_scs", registry, states, devices)["total"])
            self.assertEqual(1, store.sync("home_plus_control", registry, states, devices)["total"])
            self.assertEqual([], store.catalog("myhome_scs", states))
            scs_id = next(iter(store.load()["integrations"]["myhome_scs"]["devices"]))
            store.update("myhome_scs", scs_id, enabled=True, read_only=False)
            row = store.catalog("myhome_scs", states)[0]
            self.assertEqual("BTicino", row["manufacturer"])
            self.assertEqual(["on", "off", "level"], row["capabilities"])
            self.assertFalse(row["read_only"])
            self.assertEqual([], store.catalog("home_plus_control", states))

    def test_identity_survives_entity_rename_and_missing_becomes_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = BticinoCatalogStore(str(Path(tmp) / "bticino.json"))
            registry = [{"id": "stable", "entity_id": "cover.old", "platform": "myhome"}]
            store.sync("myhome_scs", registry, {"cover.old": {"state": "closed", "attributes": {}}})
            device_id = next(iter(store.load()["integrations"]["myhome_scs"]["devices"]))
            registry[0]["entity_id"] = "cover.new"
            store.sync("myhome_scs", registry, {"cover.new": {"state": "open", "attributes": {}}})
            self.assertEqual("cover.new", store.load()["integrations"]["myhome_scs"]["devices"][device_id]["entity_id"])
            store.sync("myhome_scs", [], {})
            self.assertTrue(store.load()["integrations"]["myhome_scs"]["devices"][device_id]["orphaned"])


class _FakeWs:
    def __init__(self, replies):
        self.replies = replies

    async def command(self, command, **kwargs):
        value = self.replies[command]
        if callable(value):
            return value(kwargs)
        return value


class BticinoManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_uses_the_expected_home_assistant_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = BticinoManager(str(Path(tmp) / "bticino.json"), token="token")
            requested = []
            manager.ws = _FakeWs({
                "config_entries/get": lambda kwargs: requested.append(kwargs["domain"]) or [{"entry_id": "configured"}],
                "config/entity_registry/list": [],
                "config/device_registry/list": [],
            })
            await manager.sync("myhome_scs", [])
            await manager.sync("home_plus_control", [])
            self.assertEqual(["myhome", "netatmo"], requested)
            self.assertTrue(manager.status("myhome_scs")["configured"])
            self.assertTrue(manager.status("home_plus_control")["configured"])


class _ArchiveResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit):
        return self.content[:limit]


class MyHomeInstallerTests(unittest.TestCase):
    @staticmethod
    def _archive():
        target = io.BytesIO()
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr(
                "MyHOME-0.9.4/custom_components/myhome/manifest.json",
                json.dumps({"domain": "myhome", "version": "0.9.4"}),
            )
            archive.writestr("MyHOME-0.9.4/custom_components/myhome/__init__.py", "")
        return target.getvalue()

    def test_verified_component_install(self):
        content = self._archive()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "e_hdl_buspro_mqtt.app.bticino_manager.MYHOME_ARCHIVE_SHA256",
            __import__("hashlib").sha256(content).hexdigest(),
        ), patch(
            "e_hdl_buspro_mqtt.app.bticino_manager.urllib.request.urlopen",
            return_value=_ArchiveResponse(content),
        ):
            installer = MyHomeComponentInstaller(tmp)
            self.assertFalse(installer.status()["installed"])
            result = installer.install()
            self.assertTrue(result["installed"])
            self.assertTrue(result["restart_required"])
            self.assertEqual("myhome", result["domain"])
            self.assertTrue((Path(tmp) / "custom_components" / "myhome" / "__init__.py").exists())

    def test_integrity_failure_does_not_install(self):
        content = self._archive()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "e_hdl_buspro_mqtt.app.bticino_manager.urllib.request.urlopen",
            return_value=_ArchiveResponse(content),
        ):
            installer = MyHomeComponentInstaller(tmp)
            with self.assertRaisesRegex(RuntimeError, "integrity"):
                installer.install()
            self.assertFalse(installer.status()["installed"])


if __name__ == "__main__":
    unittest.main()
