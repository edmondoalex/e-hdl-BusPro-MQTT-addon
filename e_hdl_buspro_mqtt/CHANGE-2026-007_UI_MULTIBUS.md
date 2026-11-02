# CHANGE-2026-007 — struttura UI multi-bus

La UI distingue funzioni globali, dispositivi trasversali e aree specifiche dei driver.

- Globali: Home, Scenari e automazioni.
- Trasversali: dispositivi aggregati per funzione, inizialmente Serrature.
- Driver: HDL BusPro attivo con Luci, Cover ed Extra; KNX, BTicino, Tuya, Modbus e DALI sono soltanto pianificati.
- Admin HDL: panoramica, dispositivi, sensori, esposizione UI, organizzazione, diagnostica e manutenzione.

La shell è additiva. Route, API, WebSocket, MQTT Discovery, identificativi e dati persistenti restano invariati. Le automazioni sono globali e non appartengono esclusivamente a HDL BusPro.
