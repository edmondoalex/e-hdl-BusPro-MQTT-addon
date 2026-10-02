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
