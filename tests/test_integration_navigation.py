from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "e_hdl_buspro_mqtt" / "app" / "static" / "hub"


def test_all_requested_brands_have_local_assets_and_planned_state():
    source = (ROOT / "hub-nav.js").read_text(encoding="utf-8")
    planned = source.split("const planned=", 1)[1].split(".map(", 1)[0]
    pairs = dict(re.findall(r"\['([^']+)','([^']+)'\]", planned))
    for name in ("Zigbee", "Z-Wave", "Shelly", "Aqara", "LoRa", "Yale", "Tado", "Sensibo", "Somfy", "Ecowitt", "Nice", "FAAC"):
        assert name in pairs
        assert (ROOT / "brands" / pairs[name]).stat().st_size > 100
    assert '>PREVISTA</span>' in source
    assert "busBrand('MQTT','mqtt.png'" in source
    assert "fetch(url('api/integrations/mqtt/client-status')" in source
    assert "setInterval(refreshMqtt,10000)" in source
    assert "if(document.hidden||mqttLoading)return" in source
    assert source.index('>UI</div>') < source.index("tree('Anteprima interfacce utente'") < source.index('>Sistema</div>')


def test_diagnostics_keep_freshness_and_missing_devices_distinct():
    source = (ROOT / "system-info.js").read_text(encoding="utf-8")
    assert "item.stale" in source and "non significa disconnessione" in source
    assert "item.unavailable_devices" in source
    assert "DISPONIBILITÀ NON NOTA" in source
    assert "row.textContent=label" in source
