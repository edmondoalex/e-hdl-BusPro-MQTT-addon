# e-hdl BusPro MQTT Add-on

Add-on Home Assistant (HAOS/Supervised) che collega gateway BusPro via UDP e crea entità in Home Assistant via MQTT Discovery.

## Stato attuale
- Web UI su `/` per gestire dispositivi light (nome + subnet/device/channel + dimmable).
- Pubblicazione MQTT Discovery (retain) ad avvio e ad ogni modifica della lista dispositivi.

## Sicurezza UI
Configura `auth.mode` in `config.json` / opzioni add-on:
- `none`: nessuna protezione
- `token`: richiede `Authorization: Bearer <token>` (oppure `?token=<token>`)
- `basic`: richiede user/password (Basic Auth)

## MQTT
Per ora viene pubblicata solo la discovery; lo stato/comandi via UDP verranno aggiunti nello step successivo.

### Note
- Robustezza MQTT: in caso di restart/disconnect del broker, l’add-on si riconnette e ripristina automaticamente le subscribe ai topic comandi.
