import asyncio
from e_hdl_buspro_mqtt.app.integration_overview import overview


def test_future_provider_appears_even_without_devices_and_no_inferred_status():
    result = overview({"nuki", "esphome", "future"}, [{"source": "nuki", "visible": False, "available": True}], {"nuki": 4, "esphome": 0, "future": None})
    items = {item["source"]: item for item in result["items"]}
    assert items["nuki"]["name"] == "Nuki Smart Access"
    assert items["nuki"]["detected"] == 4 and items["nuki"]["exported"] == 1
    assert items["nuki"]["visible"] == 0 and items["nuki"]["available"] == 1
    assert items["future"]["registered"] and items["future"]["detected"] is None
    assert "connected" not in items["future"]
    assert {"Tuya", "DALI", "Zigbee", "Z-Wave", "Shelly", "Aqara", "LoRa", "Yale", "Tado",
            "Sensibo", "Somfy", "Ecowitt", "Nice", "FAAC"} == set(result["planned"])


def test_registered_planned_bus_is_not_also_planned():
    planned = overview({"tuya", "shelly"}, [], {"tuya": 0})["planned"]
    assert "Tuya" not in planned and "Shelly" not in planned
    assert "DALI" in planned


def test_availability_is_distinct_from_state_freshness():
    rows = [{"source": "ksenia", "name": "Relay", "available": True, "stale": True},
            {"source": "ha", "name": "Offline sensor", "available": False, "stale": True},
            {"source": "ha", "name": "Online sensor", "available": True, "stale": False}]
    items = {item["source"]: item for item in overview({"ksenia", "ha"}, rows, {})["items"]}
    assert items["ksenia"]["available"] == 1 and items["ksenia"]["stale"] == 1
    assert items["ksenia"]["unavailable_devices"] == []
    assert items["ha"]["available"] == 1
    assert items["ha"]["unavailable_devices"] == ["Offline sensor"]


def test_brand_name_and_unknown_availability():
    items = overview({"home_plus_control"}, [{"source": "home_plus_control"}], {})["items"]
    assert all(brand in items[0]["name"] for brand in ("BTicino", "Legrand", "Netatmo", "Home + Control"))
    assert items[0]["unknown"] == 1 and items[0]["unavailable_devices"] == []


def test_endpoint_collects_new_provider_without_ui_change(tmp_path, monkeypatch):
    from e_hdl_buspro_mqtt.app.main import create_app
    monkeypatch.setenv("BUSPRO_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("ECONTROL_ORGANIZATION", str(tmp_path / "organization.json"))
    app = create_app()
    app.state.smart_home_sources["future"] = lambda: []
    route = next(route.endpoint for route in app.routes if getattr(route, "name", "") == "api_system_integrations")
    result = asyncio.run(route())
    assert {"nuki", "esphome", "future"}.issubset({item["source"] for item in result["items"]})
