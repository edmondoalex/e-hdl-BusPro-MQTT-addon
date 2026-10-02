from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "e_hdl_buspro_mqtt" / "app" / "static" / "user" / "ksenia.html"


class KseniaIngressTests(unittest.TestCase):
    def test_api_and_assets_stay_inside_ingress_prefix(self):
        source = PAGE.read_text(encoding="utf-8")
        self.assertNotIn("../api/integrations/ksenia", source)
        self.assertNotIn('../static/hub/', source)
        self.assertIn("fetch('api/integrations/ksenia'", source)
        self.assertIn('href="static/hub/hub.css?v=0.1.472"', source)
        self.assertIn('src="static/hub/hub-nav.js?v=0.1.472"', source)

    def test_ksenia_page_is_allowed_on_user_port(self):
        main = (PAGE.parents[2] / "main.py").read_text(encoding="utf-8")
        self.assertIn('"/locks", "/ksenia")', main)
        self.assertIn('path == "/api/integrations/ksenia" and request.method.upper() == "GET"', main)
        self.assertIn('path.startswith("/api/integrations/ksenia/command/") and request.method.upper() == "POST"', main)

    def test_non_json_response_has_readable_error(self):
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn("async function readJson", source)
        self.assertIn("Risposta non valida dal server", source)

    def test_device_cards_present_human_readable_state(self):
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn("function stateInfo", source)
        self.assertIn("const actionLabels=", source)
        self.assertNotIn("JSON.stringify(v,null,2)", source)


if __name__ == "__main__":
    unittest.main()
