import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from e_hdl_buspro_mqtt.app.netatmo_direct import NetatmoDirect


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"access_token": "access", "refresh_token": "refresh", "expires_in": 3600}).encode()


class NetatmoDirectTests(unittest.TestCase):
    def test_discovery_merges_topology_names_rooms_and_live_state(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = NetatmoDirect(str(Path(folder) / "netatmo.json"))
            topology = {"body": {"homes": [{
                "id": "home-1", "name": "Casa",
                "modules": [{"id": "09:00", "type": "NRV", "module_name": "Valvola cucina"}],
                "rooms": [{"id": "room-1", "name": "Cucina", "module_ids": ["09:00"]}],
            }]}}
            status = {"body": {"home": {
                "rooms": [{"id": "room-1", "therm_measured_temperature": 20.5, "therm_setpoint_temperature": 21.0}],
                "modules": [{"id": "09:00", "type": "NRV", "reachable": True}],
            }}}
            with patch.object(manager, "_api", side_effect=[topology, status]):
                rows = manager.discover()
            self.assertEqual("Valvola cucina", rows[0]["module_name"])
            self.assertEqual("Cucina", rows[0]["room_name"])
            self.assertEqual("room-1", rows[0]["room_id"])
            self.assertTrue(rows[0]["reachable"])
            self.assertEqual(20.5, rows[0]["therm_measured_temperature"])

    def test_set_room_temperature_uses_direct_netatmo_endpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = NetatmoDirect(str(Path(folder) / "netatmo.json"))
            with patch.object(manager, "_api", return_value={"status": "ok"}) as request:
                result = manager.set_room_temperature(home_id="home-1", room_id="room-1", temperature=21.5)
            self.assertEqual({"status": "ok"}, result)
            path, payload = request.call_args.args
            self.assertEqual("/api/setroomthermpoint", path)
            self.assertEqual("manual", payload["mode"])
            self.assertEqual(21.5, payload["temp"])
            with self.assertRaises(ValueError):
                manager.set_room_temperature(home_id="home-1", room_id="room-1", temperature=42)
    def test_direct_oauth_never_uses_external_engine_relay(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = NetatmoDirect(str(Path(folder) / "netatmo.json"))
            manager.save_credentials("client-123", "secret-123")
            callback = "http://192.168.3.24:8125/api/integrations/netatmo/oauth/callback"
            url = manager.begin(callback)
            self.assertIn("api.netatmo.com/oauth2/authorize", url)
            self.assertIn("192.168.3.24%3A8125", url)
            self.assertNotIn("home-assistant", url.lower())

    def test_callback_validates_state_and_persists_tokens(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = NetatmoDirect(str(Path(folder) / "netatmo.json"))
            manager.save_credentials("client-123", "secret-123")
            manager.begin("http://e-control.local/callback")
            state = manager._load()["oauth_state"]
            with patch("urllib.request.urlopen", return_value=_Response()):
                manager.complete(code="code", state=state)
            status = manager.status()
            self.assertTrue(status["connected"])
            self.assertLessEqual(status["authorized_at"], int(time.time()))

            with self.assertRaises(ValueError):
                manager.complete(code="code", state="wrong")


if __name__ == "__main__":
    unittest.main()
