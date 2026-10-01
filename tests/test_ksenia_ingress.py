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
        self.assertIn('href="static/hub/hub.css?v=0.1.466"', source)
        self.assertIn('src="static/hub/hub-nav.js?v=0.1.466"', source)

    def test_non_json_response_has_readable_error(self):
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn("async function readJson", source)
        self.assertIn("Risposta non valida dal server", source)


if __name__ == "__main__":
    unittest.main()
