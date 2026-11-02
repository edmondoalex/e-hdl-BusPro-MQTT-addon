from pathlib import Path
import sys


INDEX = (
    Path(__file__).resolve().parents[1]
    / "e_hdl_buspro_mqtt"
    / "app"
    / "static"
    / "index.html"
)
APP = INDEX.parents[1]
sys.path.insert(0, str(APP))

from store import StateStore


def test_valid_json_is_applied_to_visual_draft_before_controls_can_reserialize_it():
    source = INDEX.read_text(encoding="utf-8")

    helper = source.index("function applyScenarioConfigJsonToDraft")
    input_listener = source.index("qs('scCfgJson').addEventListener('input'")
    validate_handler = source.index("qs('btnScCfgValidate').addEventListener")
    save_handler = source.index("qs('btnScCfgSave').addEventListener")

    assert helper < input_listener < validate_handler < save_handler
    assert "scenarioConfigDraft = next;" in source[helper:input_listener]
    assert "item.state = 'OFF';\n            item.brightness = null;" in source[helper:input_listener]
    assert "applyScenarioConfigJsonToDraft();\n          syncScenarioConfigJson();" in source[
        validate_handler:save_handler
    ]
    assert "const parsed = applyScenarioConfigJsonToDraft();" in source[save_handler:]


def test_backend_round_trip_preserves_off_and_clears_brightness():
    cleaned = StateStore._normalize_light_scenario_payload(
        {
            "name": "ALL Castle Light OFF",
            "items": [
                {
                    "subnet_id": 1,
                    "device_id": 150,
                    "channel": 1,
                    "state": "OFF",
                    "brightness": 255,
                }
            ],
        },
        require_name=True,
    )

    assert cleaned["items"] == [
        {
            "subnet_id": 1,
            "device_id": 150,
            "channel": 1,
            "state": "OFF",
            "brightness": None,
        }
    ]

