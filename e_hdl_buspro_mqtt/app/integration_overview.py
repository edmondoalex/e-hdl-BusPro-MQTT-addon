"""Build Info cards from registered providers, not from a fixed UI list."""
LABELS = {"hdl": "HDL BusPro", "ksenia": "Ksenia Smart Home", "ha": "Integrazioni esterne",
          "knx": "e-KNX Manager", "myhome_scs": "MyHOME SCS", "home_plus_control": "BTicino / Legrand · Netatmo (Home + Control)",
          "modbus": "Modbus", "esphome": "ESPHome", "nuki": "Nuki Smart Access", "mqtt": "MQTT"}


def overview(registered, devices, detected):
    registered = set(registered)
    sources = registered | {item.get("source") for item in devices if item.get("source")}
    result = []
    for source in sorted(sources, key=lambda s: (s not in LABELS, LABELS.get(s, s).casefold())):
        rows = [item for item in devices if item.get("source") == source]
        count = detected.get(source)
        result.append({"source": source, "name": LABELS.get(source, source), "registered": source in registered,
                       "detected": count, "exported": len(rows), "visible": sum(bool(row.get("visible", True)) for row in rows),
                       "available": sum(row.get("available") is True for row in rows),
                       "stale": sum(bool(row.get("stale")) for row in rows),
                       "unavailable_devices": [row.get("name") or row.get("device_id") or "Dispositivo senza nome"
                                               for row in rows if row.get("available") is False],
                       "unknown": sum(row.get("available") is None for row in rows),
                       "excluded": max(0, count-len(rows)) if count is not None else None})
    planned = {"tuya": "Tuya", "dali": "DALI", "zigbee": "Zigbee", "zwave": "Z-Wave",
               "shelly": "Shelly", "aqara": "Aqara", "lora": "LoRa", "yale": "Yale", "tado": "Tado",
               "sensibo": "Sensibo", "somfy": "Somfy", "ecowitt": "Ecowitt", "nice": "Nice", "faac": "FAAC"}
    return {"items": result, "planned": [name for source, name in planned.items() if source not in sources]}
