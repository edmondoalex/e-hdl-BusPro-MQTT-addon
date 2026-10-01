import json
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from e_hdl_buspro_mqtt.app.smart_home import build_smart_home, validate_command_request
from e_hdl_buspro_mqtt.app.main import create_app


class SmartHomeProducerTests(unittest.TestCase):
    def organization(self):
        return {
            "schema_version": 1,
            "floors": [{"id":"floor-pt","name":"Piano terra"}],
            "rooms": [{"id":"room-sala","name":"Sala","floor_id":"floor-pt"}],
            "groups": [{"id":"group-sera","name":"Sera"}],
            "devices": {
                "hdl:1.2.3": {"floor_id":"floor-pt","room_id":"room-sala","group_ids":["group-sera"],"categories":["lights","extra"],"orders":{"lights":3,"extra":8},"visible":False,"favorite":True,"shortcut":True,"icon_auto":"mdi:lightbulb","icon_override":"mdi:ceiling-light","orphaned":False},
                "ksenia:1.2.3": {"floor_id":"floor-pt","room_id":"room-sala","group_ids":[],"categories":["covers"],"orders":{"covers":4},"visible":True,"favorite":False,"shortcut":False,"icon_auto":"mdi:window-shutter","icon_override":"","orphaned":False},
                "hdl:9.9.9": {"name":"Vecchio","device_class":"light","floor_id":"floor-pt","room_id":"room-sala","group_ids":[],"icon_auto":"mdi:lightbulb","icon_override":"","orphaned":True},
            },
        }

    def payload(self):
        return build_smart_home(
            hdl_devices=[{"type":"light","name":"Luce sala","addr":"1.2.3","dimmable":True}],
            ksenia_snapshot={"availability":"online","devices":[{
                "device_id":"1.2.3","name":"Tapparella","device_class":"cover","native_type":"outputs","native_id":"7",
                "capabilities":["open","close","stop"],"read_only":False,"stale":False,
                "state":{"value":{"state":"OPEN"}},"home_assistant_entity_id":"cover.tapparella",
            }]},
            organization=self.organization(),
            states={"states":{"1.2.3":{"state":"ON","brightness":128}}},
            hdl_available=True,
        )

    def test_complete_versioned_schema_and_organization(self):
        payload = self.payload()
        self.assertEqual("1.0", payload["schema_version"])
        self.assertEqual(1, payload["organization_schema_version"])
        hdl = next(x for x in payload["devices"] if x["id"] == "hdl:1.2.3")
        self.assertEqual("Sala", hdl["room_name"])
        self.assertEqual(["Sera"], hdl["group_names"])
        self.assertEqual("mdi:ceiling-light", hdl["icon"])
        self.assertEqual(["on","off","level"], hdl["capabilities"])
        self.assertEqual(["lights", "extra"], hdl["categories"])
        self.assertEqual({"lights":3, "extra":8}, hdl["orders"])
        self.assertFalse(hdl["visible"])
        self.assertTrue(hdl["favorite"])
        self.assertTrue(hdl["shortcut"])

    def test_same_native_id_across_sources_remains_distinct(self):
        ids = {x["id"] for x in self.payload()["devices"]}
        self.assertIn("hdl:1.2.3", ids)
        self.assertIn("ksenia:1.2.3", ids)

    def test_ksenia_authoritative_entity_id_and_state_are_preserved(self):
        item = next(x for x in self.payload()["devices"] if x["source"] == "ksenia")
        self.assertEqual("cover.tapparella", item["home_assistant_entity_id"])
        self.assertEqual({"state":"OPEN"}, item["state"])
        self.assertTrue(item["available"])

    def test_orphan_is_visible_but_read_only_and_unavailable(self):
        item = next(x for x in self.payload()["devices"] if x["id"] == "hdl:9.9.9")
        self.assertTrue(item["orphaned"])
        self.assertTrue(item["read_only"])
        self.assertFalse(item["available"])
        self.assertTrue(item["stale"])

    def test_security_ksenia_is_never_exposed(self):
        org = self.organization()
        payload = build_smart_home(
            hdl_devices=[],
            ksenia_snapshot={"availability":"online","devices":[{
                "device_id":"sec","name":"Alarm partition","device_class":"switch","native_type":"partitions",
                "native_id":"1","capabilities":["arm"],"read_only":False,
            }]},
            organization=org, states={}, hdl_available=False,
        )
        self.assertNotIn("ksenia:sec", {x["id"] for x in payload["devices"]})

    def test_read_only_and_unavailable_states_are_explicit(self):
        payload = build_smart_home(
            hdl_devices=[{"type":"temperature","name":"Temperatura","addr":"1.5.1"}],
            ksenia_snapshot={"availability":"offline","devices":[]},
            organization={"schema_version":1,"floors":[],"rooms":[],"groups":[],"devices":{}},
            states={}, hdl_available=False,
        )
        item = payload["devices"][0]
        self.assertTrue(item["read_only"])
        self.assertFalse(item["available"])
        self.assertTrue(item["stale"])

    def test_legacy_hdl_devices_without_type_keep_classification_and_state(self):
        payload = build_smart_home(
            hdl_devices=[
                {"name":"Luce storica","addr":"1.152.4","category":"Luci"},
                {"name":"Switch storico","addr":"1.152.5","category":"Switch"},
            ],
            ksenia_snapshot={"availability":"offline","devices":[]},
            organization={"schema_version":1,"floors":[],"rooms":[],"groups":[],"devices":{}},
            states={"states":{"1.152.4":{"state":"ON"},"1.152.5":{"state":"OFF"}}},
            hdl_available=True,
        )
        light, switch = payload["devices"]
        self.assertEqual(("light", ["lights"], {"state":"ON"}, False),
                         (light["device_class"], light["categories"], light["state"], light["stale"]))
        self.assertEqual(("switch", ["extra"], {"state":"OFF"}, False),
                         (switch["device_class"], switch["categories"], switch["state"], switch["stale"]))

    def test_command_validation_denies_read_only_unavailable_and_capability(self):
        base = {"orphaned":False,"read_only":False,"available":True,"capabilities":["on"]}
        self.assertEqual("on", validate_command_request(base, "ON"))
        for changed, message in (
            ({"read_only":True}, "read-only"),
            ({"available":False}, "unavailable"),
            ({"orphaned":True}, "orphaned"),
        ):
            with self.assertRaisesRegex(ValueError, message):
                validate_command_request({**base, **changed}, "on")
        with self.assertRaisesRegex(ValueError, "capability"):
            validate_command_request(base, "off")

    def test_driver_neutral_semantics_for_hdl_ksenia_and_future_driver(self):
        org = {"schema_version":1,"floors":[],"rooms":[],"groups":[],"devices":{
            source + ":same": {"name":source,"device_class":"dimmer","floor_id":"","room_id":"","group_ids":[],"categories":["lights","extra"],"orders":{"lights":7},"visible":True,"favorite":False,"shortcut":False,"icon_auto":"mdi:brightness-6","icon_override":"","orphaned":False}
            for source in ("hdl", "ksenia", "future")
        }}
        payload = build_smart_home(
            hdl_devices=[{"type":"light","name":"HDL","addr":"same","dimmable":True}],
            ksenia_snapshot={"availability":"online","devices":[{"device_id":"same","name":"Ksenia","device_class":"dimmer","native_type":"outputs","native_id":"1","capabilities":["on","off","level"],"read_only":False,"stale":False,"state":{"value":{"level":50}}}]},
            additional_sources={"future":[{"device_id":"same","name":"Future","device_class":"dimmer","native_type":"channel","capabilities":["on","off","level"],"read_only":False,"available":True,"stale":False,"state":{"level":50}}]},
            organization=org, states={"states":{"same":{"level":50}}}, hdl_available=True,
        )
        rows = {x["source"]:x for x in payload["devices"]}
        for source in ("ksenia", "future"):
            for field in ("device_class", "capabilities", "commands", "features", "categories", "orders", "visible"):
                self.assertEqual(rows["hdl"][field], rows[source][field], (source, field))

    def test_visual_category_never_authorizes_a_command(self):
        item = {"orphaned":False,"read_only":False,"available":True,"capabilities":["on"],"categories":["security"],"visual_category":"security"}
        with self.assertRaisesRegex(ValueError, "capability"):
            validate_command_request(item, "disarm")

    def test_contract_has_no_bus_transport_details(self):
        forbidden = {"command_topic", "state_topic", "mqtt_topic", "subnet_id", "channel"}
        for item in self.payload()["devices"]:
            self.assertFalse(forbidden.intersection(item), item)

    def test_published_schema_and_fixture_are_versioned(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "e_hdl_buspro_mqtt" / "docs" / "smart-home-v1.schema.json").read_text(encoding="utf-8"))
        fixture = json.loads((root / "tests" / "fixtures" / "smart_home_snapshot_v1.json").read_text(encoding="utf-8"))
        self.assertEqual("1.0", fixture["schema_version"])
        self.assertEqual("1.0", schema["properties"]["schema_version"]["const"])
        required = set(schema["$defs"]["device"]["required"])
        self.assertTrue(required.issubset(fixture["devices"][0]))

    def test_main_exposes_additive_snapshot_and_command_route(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "e_hdl_buspro_mqtt" / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn('payload["smart_home"]', source)
        self.assertIn('/api/user/smart-home/{source}/{device_id}/command', source)

    def test_hdl_command_route_uses_internal_catalog_identity(self):
        class Gateway:
            started = True
            last_error = ""
            calls = []
            def transport_ready(self): return True
            async def set_light(self, **kwargs): self.calls.append(kwargs)
            async def read_light_status(self, **kwargs): return None

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BUSPRO_STATE": str(Path(tmp) / "state.json"),
            "ECONTROL_ORGANIZATION": str(Path(tmp) / "organization.json"),
        }):
            app = create_app()
            app.state.store.add_device({"type":"light","name":"Luce","subnet_id":1,"device_id":2,"channel":3,"addr":"1.2.3","dimmable":True})
            gateway = Gateway()
            app.state.gateway = gateway
            endpoint = next(r.endpoint for r in app.routes if getattr(r, "name", "") == "control_smart_home")
            result = asyncio.run(endpoint("hdl", "1.2.3", {"action":"level","value":50}))
            self.assertTrue(result["ok"])
            self.assertEqual(128, gateway.calls[-1]["brightness255"])

    def test_ksenia_command_route_delegates_only_catalogued_device(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BUSPRO_STATE": str(Path(tmp) / "state.json"),
            "ECONTROL_ORGANIZATION": str(Path(tmp) / "organization.json"),
        }):
            app = create_app()
            consumer = app.state.ksenia
            device_id = "ksn_00000000000000000000000000000001"
            consumer._availability = "online"
            consumer._catalog_version = "1.0"
            consumer._devices = {device_id: {
                "device_id":device_id,"name":"Uscita","device_class":"switch","native_type":"outputs","native_id":"1",
                "capabilities":["on"],"read_only":False,"command_topic":"e-safe/cmd/output/1","commands":{"on":{}},
                "state_topic":"e-safe/outputs/1","source":"ksenia",
            }}
            called = []
            consumer.execute = lambda did, action, value=None: called.append((did, action, value)) or {"ok":True,"status":"confirmed"}
            endpoint = next(r.endpoint for r in app.routes if getattr(r, "name", "") == "control_smart_home")
            result = asyncio.run(endpoint("ksenia", device_id, {"action":"on"}))
            self.assertTrue(result["ok"])
            self.assertEqual([(device_id, "on", None)], called)

    def test_future_driver_registers_without_changing_core_route(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "BUSPRO_STATE": str(Path(tmp) / "state.json"),
            "ECONTROL_ORGANIZATION": str(Path(tmp) / "organization.json"),
        }):
            app = create_app()
            app.state.smart_home_sources["future"] = lambda: [{"device_id":"device-1","name":"Future light","device_class":"light","native_type":"channel","capabilities":["on"],"read_only":False,"available":True,"stale":False,"state":{"state":"OFF"}}]
            called = []
            async def handler(item, action, value):
                called.append((item["id"], action, value))
                return {"ok":True,"status":"confirmed"}
            app.state.smart_home_command_handlers["future"] = handler
            endpoint = next(r.endpoint for r in app.routes if getattr(r, "name", "") == "control_smart_home")
            result = asyncio.run(endpoint("future", "device-1", {"action":"on"}))
            self.assertTrue(result["ok"])
            self.assertEqual([("future:device-1", "on", None)], called)


if __name__ == "__main__":
    unittest.main()
