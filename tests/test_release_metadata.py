import json
import re
from pathlib import Path


def test_runtime_version_matches_addon_manifest():
    root = Path(__file__).resolve().parents[1]
    manifest_version = json.loads((root / "e_hdl_buspro_mqtt" / "config.json").read_text(encoding="utf-8-sig"))["version"]
    main_source = (root / "e_hdl_buspro_mqtt" / "app" / "main.py").read_text(encoding="utf-8")
    runtime_version = re.search(r'^ADDON_VERSION\s*=\s*"([^"]+)"', main_source, re.MULTILINE)
    assert runtime_version is not None
    assert runtime_version.group(1) == manifest_version
