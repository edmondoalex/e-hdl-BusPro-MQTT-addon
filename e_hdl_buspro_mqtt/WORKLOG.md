# WORKLOG

## 2026-01-19
- Creato scheletro add-on (Dockerfile, config.json, backend FastAPI placeholder).
- Prossimo: UI web + auth + persistenza devices + MQTT discovery.

## 2026-01-19 (continuazione)
- Aggiunta UI web iniziale (CRUD dispositivi) su `/`.
- Aggiunto client MQTT + endpoint `/api/mqtt/status` e ripubblicazione discovery.
- La discovery (retain) viene pubblicata su avvio e ad ogni modifica dei devices.

- Version bump: 0.1.0 → 0.1.1 (policy: bump ad ogni modifica).


## 2026-01-19 (fix Supervisor discovery)
- Rimosso `repository.yaml` (Supervisor lo interpretava come repository, quindi l’add-on non compariva).
- Aggiunto `build_from` e cambiato `image` per build locale.
- Version bump: 0.1.1 → 0.1.2.

## 2026-01-19 (rename)
- Rinominata cartella add-on per combaciare con `slug`: `e-hdl_buspro_addon` → `e_hdl_buspro_mqtt`.
- Version bump: 0.1.2 → 0.1.3.

- Fix: rimosso UTF-8 BOM da config.json (Supervisor non lo parsava).
- Version bump: 0.1.3 → 0.1.4.


- Fix: webui placeholder valido per Supervisor (PORT placeholder).
- Version bump: 0.1.4 → 0.1.5.


- Fix: rimosso campo 'image' per forzare build locale da Dockerfile (evita pull 404).
- Version bump: 0.1.5 → 0.1.6.


## 2026-01-19 (build fix)
- Fix build: uso venv in `/opt/venv` per evitare errore PEP 668 (externally-managed-environment).
- Aggiornato `run.sh` per usare il python del venv.
- Version bump: 0.1.6 → 0.1.7.

- Tweaks: pip upgraded inside venv (safe) + removed no-op install.
- Version bump: 0.1.7 → 0.1.8.


## 2026-01-19 (runtime fix)
- Fix: rimosso BOM da `run.sh` (shebang rotto) + aggiunto `cd /app`.
- Fix: aggiunto `PYTHONPATH=/app` nel Dockerfile per risolvere `No module named app.main`.
- Version bump: 0.1.8 → 0.1.9.

## 2026-01-19 (sidebar/ingress)
- Aggiunto Ingress + panel (Mostra nella barra laterale) in `config.json`.
- UI ora usa fetch relativi per funzionare sia su porta web sia via Ingress.
- Porta interna fissata a 8124; la porta esterna si cambia dalla sezione Network dell’add-on.
- Version bump: 0.1.9 → 0.1.10.

## 2026-01-19 (dockerfile fix)
- Fix: riscritto Dockerfile (ENV line continuations corrette; rimosse sequenze `\\` accidentali).
- Version bump: 0.1.10 → 0.1.11.

## 2026-01-19 (auth defaults)
- Default auth impostata a `none` (evita lockout con token vuoto).
- Fallback automatico a `none` se `token` o credenziali basic mancanti.
- Version bump: 0.1.11 → 0.1.12.

## 2026-01-19 (ingress fix)
- Fix: disabilitato `host_network` per far funzionare Ingress/sidebar (503).
- Version bump: 0.1.12 → 0.1.13.

## 2026-01-19 (mqtt callback fix)
- Fix: callback `on_disconnect` compatibile con Paho MQTT v2 (aggiunto parametro `disconnect_flags`).
- Version bump: 0.1.13 → 0.1.14.

## 2026-01-19 (ingress auth bypass)
- Fix: bypass auth interna quando richiesto via Home Assistant Ingress (header ingress), per evitare 503 e usare l’autenticazione di HA.
- Version bump: 0.1.14 → 0.1.15.

## 2026-01-19 (ingress routing)
- Fix UI: chiamate API relative (`./api/...`) per funzionare dietro Ingress.
- Aggiunto endpoint alias `/ingress` → `/`.
- Pulita formattazione `auth_middleware`.
- Version bump: 0.1.15 → 0.1.16.

## 2026-01-19 (ingress basepath)
- Fix: middleware che stripppa il prefisso `x-ingress-path` (o `/local_*`) per far funzionare routing/API dietro Ingress.
- Version bump: 0.1.16 → 0.1.17.

## 2026-01-19 (ingress fallback)
- Fix: aggiunto `X-Forwarded-Prefix` come base path Ingress.
- Fix: route fallback SPA per servire l’UI anche su path non previsti dietro proxy.
- Version bump: 0.1.17 → 0.1.18.

## 2026-01-19 (playbook)
- Creato `ADDON_BUILD_PLAYBOOK.md` con i passaggi e bugfix per replicare il processo su add-on futuri.
- Version bump: 0.1.18 → 0.1.19.

## 2026-01-19 (realtime control)
- Vendorizzato `pybuspro` dentro l’add-on.
- Aggiunto gateway UDP + cache stato + comandi luce.
- Aggiunta UI realtime: WebSocket + comandi (toggle/slider) sui device creati.
- MQTT: publish stati su `buspro/state/...` e subscribe comandi su `buspro/cmd/...`.
- Version bump: 0.1.19 → 0.1.20.

- Cleanup: rimosso telegram callback extra (duplicato) in buspro_gateway.
- Version bump: 0.1.20 → 0.1.21.


## 2026-01-19 (persistence)
- Persistenza: salvato ultimo stato device in `/data/state.json` (sezione `states`).
- MQTT: stati pubblicati retained + ripubblicati all’avvio.
- UI: snapshot websocket include gli ultimi stati persistiti.
- Version bump: 0.1.21 → 0.1.22.

## 2026-01-19 (hotfix syntax)
- Fix: corretto `buspro_gateway.py` (rimosso testo letterale `\\n` che rompeva la sintassi Python).
- Version bump: 0.1.22 → 0.1.23.

- Fix2: sostituito literal \\n con newline reale in buspro_gateway.
- Version bump: 0.1.23 → 0.1.24.


## 2026-01-19 (pybuspro HA-deps fix)
- Fix: `pybuspro/devices/__init__.py` non importa piu `cover` (dipendenza da `homeassistant`).
- Fix: `pybuspro/__init__.py` riscritto senza BOM.
- Fix: `pybuspro/devices/cover.py` ora ha fallback se `homeassistant` non esiste.
- Version bump: 0.1.24 -> 0.1.25.

- Fix: riscritto pybuspro/__init__.py rimuovendo literal \\n che rompeva Python.
- Version bump: 0.1.25 → 0.1.26.


## 2026-01-19 (startup fixes)
- Fix: corretto `_republish_discovery()` (publish dentro al loop; rimossa riga errata con variabili non definite).
- Fix: rimossa chiamata duplicata a `_republish_discovery()` in startup.
- Version bump: 0.1.26 → 0.1.27.

- Fix: rimossa seconda chiamata duplicata a _republish_discovery() in startup.
- Version bump: 0.1.27 → 0.1.28.


- Fix: rimossa chiamata duplicata _republish_discovery() (regex CRLF).
- Version bump: 0.1.28 → 0.1.29.


- Fix: corretto indent della comment line dopo _republish_discovery (evita IndentationError).
- Version bump: 0.1.29 → 0.1.30.


## 2026-01-19 (remove device)
- Aggiunto endpoint remove singolo device light: `DELETE /api/devices/light/{subnet}/{device}/{channel}`.
- Store: rimozione anche dello stato persistito per quel device.
- Version bump: 0.1.30 → 0.1.31.

## 2026-01-19 (ui remove)
- UI: aggiunto pulsante Rimuovi per device (chiama `DELETE /api/devices/light/...`).
- Version bump: 0.1.31 → 0.1.32.

## 2026-01-19 (indent fix)
- Fix: corretto indent di `@api.delete("/api/devices")` (evitava IndentationError).
- Version bump: 0.1.32 → 0.1.33.

## 2026-01-19 (hotfix store)
- Fix: rimosso literal `\\n` da `store.py` (SyntaxError su avvio).
- Version bump: 0.1.33 → 0.1.34.

## 2026-01-19 (build guard)
- Fix: rimosso literal `\\n` residuo in `store.py`.
- Dockerfile: aggiunto `python -m compileall` in build per fallire subito se ci sono SyntaxError/IndentationError.
- Version bump: 0.1.34 → 0.1.35.

## 2026-01-20 (build fix cover)
- Fix: corretto `pybuspro/devices/cover.py` (rimosse sequenze `\\n` letterali nel try/except).
- Version bump: 0.1.35 → 0.1.36.

## 2026-01-20 (realtime devices)
- Realtime: broadcast lista dispositivi su WebSocket dopo add/remove/clear.
- Version bump: 0.1.36 → 0.1.37.

## 2026-01-20 (ui devices event)
- UI: gestione evento WebSocket `devices` per aggiornare la tabella senza refresh.
- Version bump: 0.1.37 → 0.1.38.

## 2026-01-20 (commands debug)
- Aggiunto `/api/buspro/status` per diagnosticare host/porta e stato UDP transport.
- Aggiunto polling `read_status` ogni 20s per aggiornare stati senza azioni manuali.
- `control_light` ora ritorna 503 se il transport UDP non è pronto.
- Version bump: 0.1.39 → 0.1.40.

- Fix: corretto newline mancante tra _broadcast_devices e _republish_discovery (SyntaxError).
- Version bump: 0.1.40 → 0.1.41.


- Fix: rimosse sequenze \\n letterali in shutdown (poll_task cancel) in main.py.
- Version bump: 0.1.41 → 0.1.42.


- Fix: shutdown poll_task line replaced properly (no literal \\n).

## 2026-01-20 (ui live refresh + controls)
- Fix: `POST/DELETE /api/devices` ora fanno broadcast WebSocket `devices` (prima serviva refresh).
- Fix: non cancellare piu `poll_task` su `buspro_status` / `control_light` / `add_device` (lo stato continua ad aggiornarsi).

## 2026-01-24 (temperature sensors)
- Aggiunti sensori temperatura manuali (device `type=temp`) con `sensor_id` (channel), `decimals`, `min_value`/`max_value`.
- Decode telegram `OperateCode.BroadcastTemperatureResponse` (float32 little-endian) e publish MQTT retained su `.../state/temp/<sub>/<dev>/<sensor>`.
- MQTT Discovery Home Assistant per `sensor` (device_class temperature, unit °C).
- Admin UI: CRUD sensori temperatura + valore live via WebSocket (`temp_value`) e snapshot `temp_states`.
- Fix decode: i 4 byte float sono `payload[2:6]` (non `payload[1:5]`).
- Version bump: 0.1.171 -> 0.1.173.
- Sensori temperatura: supporto formato corto a 2 byte (`payload=[sensor_id,value]`) per moduli 12-in-1, con `temp_format` e override `temp_scale`/`temp_offset`.
- Admin UI: aggiunta scelta formato + scale/offset per eliminare il valore `?` quando il device non invia float32.
- Version bump: 0.1.173 -> 0.1.174.

## 2026-01-24 (sniffer raw operate_code)
- Sniffer: aggiunti `operate_code_raw_hex` e `operate_code_raw_int` (2 byte raw a offset 21) per analizzare telegrammi con `operate_code` non riconosciuto.
- UI Sniffer: mostra `raw:0x....` quando `operate_code` e' vuoto.
- Version bump: 0.1.174 -> 0.1.175.
- UI: rimossa sequenza `\\n` letterale nel submit; fallback `GET /api/devices` dopo add; clear svuota tabella; pill `UDP` + messaggi errore; update ottimistico dopo comando.
- Version bump: 0.1.43 -> 0.1.44.

## 2026-01-20 (command guard)
- API: `control_light` ritorna 503 se il transport UDP non e' pronto (errore esplicito invece di comando "silenzioso").
- Version bump: 0.1.44 -> 0.1.45.

## 2026-01-20 (ingress basepath)
- UI: le chiamate API/WS ora calcolano un basepath stabile (funziona anche su URL ingress senza trailing slash, che lasciava i pill a '?').
- Version bump: 0.1.45 -> 0.1.46.

## 2026-01-20 (ui version)
- API: aggiunto `GET /api/meta` con versione add-on.
- UI: mostra versione in header (utile per capire se e' aggiornato).
- Version bump: 0.1.46 -> 0.1.47.

## 2026-01-20 (ingress basepath hotfix)
- UI: `basePrefix()` ora rimuove `/ingress` dal path (fix per pill a '?' e comandi non funzionanti in Ingress).
- Version bump: 0.1.47 -> 0.1.48.

## 2026-01-20 (tx auto + initial states)
- BusPro: auto-imposta la destinazione TX usando l'IP/porta dell'ultimo pacchetto RX (comandi UI funzionano anche se `gateway_host` e' sbagliato).
- WS snapshot: include gli stati persistiti, cosi la UI non parte con `?` dopo reboot.
- Version bump: 0.1.48 -> 0.1.49.

## 2026-01-20 (tx host only)
- BusPro: auto TX ora usa solo l'host dall'ultimo RX e mantiene la porta configurata (alcuni gateway inviano da porta sorgente non-6000).
- UI: mostra `tx` e `rx` in pill UDP per debug rapido.
- Version bump: 0.1.49 -> 0.1.50.

## 2026-01-20 (tx NAT guard)
- BusPro: non usare l'host RX per auto-TX se coincide col default gateway del container (RX NATato tipo `172.x`); mantiene il `gateway_host` configurato.
- Version bump: 0.1.50 -> 0.1.51.

## 2026-01-20 (dimmer button)
- UI: tasto Accendi/Spegni per dimmerabili non invia piu `brightness` quando spegne; quando accende forza un valore valido se lo slider e' a 0/non valido.
- BusPro: mapping brightness 0..255 -> percentuale usa round e minimo 1% quando brightness > 0 (evita che 1/255 diventi 0%).
- Version bump: 0.1.51 -> 0.1.52.

## 2026-01-20 (dimmer default)
- UI: tasto Accendi per dimmer usa l'ultima brightness nota (se presente), altrimenti non invia brightness (backend -> 100%).
- UI: slider default a 255 quando stato sconosciuto; non forza a 1 quando la luce e' OFF.
- Version bump: 0.1.52 -> 0.1.53.

## 2026-01-20 (slider sync)
- UI: quando la luce va OFF, lo slider torna al minimo (1 ~= 0%) per riflettere lo stato reale.
- Version bump: 0.1.53 -> 0.1.54.

## 2026-01-20 (slider refresh)
- UI: su refresh, se lo stato e' OFF lo slider parte dal minimo (non piu' al max).
- Version bump: 0.1.54 -> 0.1.55.

## 2026-01-20 (ui highlight)
- UI: righe luci ON evidenziate in giallo; per dimmerabili evidenziazione proporzionale e badge percentuale.
- Version bump: 0.1.55 -> 0.1.56.

## 2026-01-20 (mqtt category + icon)
- MQTT Discovery: tutte le luci ora sono raggruppate sotto un unico device "BusPro Luci" (category device).
- UI/API: aggiunto campo `icon` (mdi) opzionale per forzare l'icona in Home Assistant.
- Version bump: 0.1.56 -> 0.1.57.

## 2026-01-20 (edit + category)
- UI: aggiunti `categoria` (gruppo HA) e `Modifica` per cambiare nome/dimmable/categoria/icona senza cancellare.
- API: aggiunto `PATCH /api/devices/light/{subnet}/{device}/{channel}`.
- MQTT Discovery: device raggruppato per `categoria` (es. "BusPro Luci", "BusPro Cover"...).
- Version bump: 0.1.57 -> 0.1.58.

## 2026-01-20 (category dropdown)
- UI: `Categoria` ora e' un menu a tendina con preset (Luci, Switch, Curtain, Cover, Sensori, ...), con opzione "Altro" custom.
- Version bump: 0.1.58 -> 0.1.59.

## 2026-01-20 (covers)
- BusPro: aggiunti device cover con comandi open/close/stop/set_position e broadcast realtime `cover_state`.
- MQTT: aggiunta discovery + topic state/command per cover (posizione + stato) e subscribe ai comandi.
- UI: form + tabella cover con controlli e slider posizione.
- Store: persistenza stato cover (state + position).
- Version bump: 0.1.59 -> 0.1.60.

## 2026-01-20 (cover up/down + calibrazione)
- Cover: supporto tempi separati salita/discesa (`opening_time_up`, `opening_time_down`).
- UI: form cover con tempi salita/discesa e pulsanti calibrazione "Calibra Su/Giu" (premi una volta per partire, poi di nuovo per salvare i secondi).
- API: `PATCH /api/devices/cover/{subnet}/{device}/{channel}` per aggiornare i tempi.
- Version bump: 0.1.60 -> 0.1.62.

## 2026-01-20 (cover bidirezionale)
- Cover: parsing dei telegrammi `CurtainSwitch*Response` per aggiornare stato/posizione stimata anche quando i comandi partono da HDL.
- Version bump: 0.1.62 -> 0.1.63.

## 2026-01-20 (calibra fix + edit tempi)
- Calibrazione cover: ora usa comandi raw OPEN/CLOSE senza auto-stop, quindi non si ferma a meta'.
- UI: aggiunto `Modifica` per cover e visualizzazione tempi `su/giu` nella tabella; salva via `PATCH /api/devices/cover/...`.
- Version bump: 0.1.63 -> 0.1.65.

## 2026-01-20 (cover stop robust)
- Cover: STOP ora viene inviato due volte + read_status (fix per casi in cui lo stop singolo non ferma se il movimento parte da HDL).
- Version bump: 0.1.65 -> 0.1.66.

## 2026-01-20 (calibrazione no popup)
- UI: calibrazione cover senza alert/confirm; stato e istruzioni mostrati in pagina con timer sul bottone.
- Version bump: 0.1.66 -> 0.1.67.

## 2026-01-20 (cover edit UX)
- UI: in modifica cover mostra bottone `Salva` + `Annulla` (prima non era chiaro come salvare).
- Version bump: 0.1.67 -> 0.1.68.

## 2026-01-20 (cover stop from HDL)
- Cover: se arriva una risposta senza status ma la cover era in movimento, congela la posizione stimata (fix per STOP premuto da HDL che prima faceva continuare fino a 0/100 in UI).
- Version bump: 0.1.68 -> 0.1.69.
- Version bump: 0.1.42 -> 0.1.43.

## 2026-01-20 (debug + stop affidabile)
- Add-on: aggiunta opzione `debug` in configurazione per log verbosi (utile per diagnosticare comandi/telegrammi).
- Cover: polling `read_status` mentre e' in movimento + freeze su status inatteso (STOP da HDL piu' affidabile).
- Version bump: 0.1.69 -> 0.1.70.

## 2026-01-20 (cover stop anti-fantasma)
- Cover: evita che `CurtainSwitchStatusResponse` con valore 1/2 riavvii la corsa dopo uno STOP; solo i `ControlResponse` avviano un movimento.
- Version bump: 0.1.70 -> 0.1.71.

## 2026-01-20 (cover start da HDL + stop debounce)
- Cover: `StatusResponse` 1/2 ora può avviare il movimento quando il comando parte da HDL, ma viene ignorato per ~1.5s dopo uno STOP per evitare ripartenze fantasma.
- Version bump: 0.1.71 -> 0.1.72.

## 2026-01-20 (cover status=0 + debug telegram)
- Cover: `CurtainSwitchStatusResponse` con `status=0` non viene piu' interpretato come STOP (su alcuni gateway significa "no info"); avvio/stop movimento usa `CurtainSwitchControl`/`ControlResponse`.
- Add-on: aggiunto toggle `debug_telegram` per attivare/disattivare i log rumorosi `buspro.telegram`/`buspro.log`.
- Version bump: 0.1.72 -> 0.1.73.

## 2026-01-20 (cover realtime ticker)
- Cover: aggiunto ticker interno per aggiornare la posizione in realtime durante OPENING/CLOSING anche se il bus non invia stati; finalizza la posizione quando il tempo stimato e' scaduto.
- Cover: ignora comandi ripetuti nella stessa direzione (evita reset continui della stima).
- Version bump: 0.1.73 -> 0.1.74.

## 2026-01-20 (cover status=0 non-stop)
- Cover: `CurtainSwitchStatusResponse status=0` ora viene ignorato (sul tuo gateway equivale a "no info") per evitare che lo stato passi a STOP durante il movimento.
- Version bump: 0.1.74 -> 0.1.75.

## 2026-01-20 (cover calib tempi persistenti)
- Gateway: `ensure_cover()` non sovrascrive piu' `opening_time_up/down` con il default (20s) quando il device esiste; i comandi da UI rispettano i tempi calibrati.
- Version bump: 0.1.75 -> 0.1.76.

## 2026-01-20 (user dashboard)
- UI: aggiunta vista `User` (dashboard) separata dalla vista `Admin`, con tab per tipo (Tutti/Luci/Cover), card moderne, raggruppamento per categoria e controlli realtime.
- Version bump: 0.1.76 -> 0.1.77.

## 2026-01-20 (porte separate user/admin)
- Add-on: aggiunta porta Admin `8125/tcp` (oltre alla User `8124/tcp`).
- UI User: pagine separate `/lights` e `/covers` senza header (porta 8124).
- Gate: sulla porta User sono esposti solo User UI + comandi e WS; le API/admin UI restano accessibili solo sulla porta Admin.
- Auth: aggiunto `user_auth` separato da `auth` (admin).
- Version bump: 0.1.77 -> 0.1.78.

## 2026-01-20 (user background)
- UI User: aggiornato lo sfondo con radial-gradient.
- Version bump: 0.1.78 -> 0.1.79.

## 2026-01-20 (user ingress urls)
- UI User: fix URL per ingress (websocket `/ws` e chiamate API relative al path corrente) così luci/cover caricano correttamente anche da Home Assistant.
- Version bump: 0.1.79 -> 0.1.80.

## 2026-01-20 (user syntax fix)
- UI User: fix `escapeHtml()` (SyntaxError in browser per escaping errato).
- Version bump: 0.1.80 -> 0.1.81.

## 2026-01-20 (user js compat)
- UI User: rimosso uso di `??` e `replaceAll` per maggiore compatibilita' con WebView/browser vecchi (fix SyntaxError su pagina cover).
- Version bump: 0.1.81 -> 0.1.82.

## 2026-01-20 (user pages link + admin cleanup)
- UI Admin: rimosso routing interno alla vista User (resta solo Admin).
- UI Admin: link "User" ora apre le pagine reali User su `:8124/lights` (accesso separato dalla Admin `:8125`).
- UI User: title reso ASCII (`BusPro - ...`) per evitare caratteri "strani" su alcuni browser.
- Version bump: 0.1.82 -> 0.1.83.

## 2026-01-20 (user centered list)
- UI User: elenco dispositivi centrato e in lista (card con larghezza max, centrata nella pagina).
- Version bump: 0.1.83 -> 0.1.84.

## 2026-01-20 (user light feedback)
- UI User (Luci): quando accesa, la card cambia colore con intensita' proporzionale alla % (dimmer) / 100% (non-dimmer).
- Version bump: 0.1.84 -> 0.1.85.

## 2026-01-20 (user compact cards)
- UI User: schede device piu' compatte (meno padding/altezza; controlli piu' piccoli).
- Version bump: 0.1.85 -> 0.1.86.

## 2026-01-20 (user background colors)
- UI User: base background aggiornata a `#05070b` (gradient: `#1a2230` -> `#05070b` -> `#000`).
- Version bump: 0.1.86 -> 0.1.87.

## 2026-01-20 (user card theme)
- UI User: schede con palette piu' scura/grigio-nera coerente con lo sfondo (meno blu) e contrasto leggero.
- Version bump: 0.1.87 -> 0.1.88.

## 2026-01-20 (user hide ids)
- UI User: rimossa visualizzazione dell'ID/indirizzo dispositivo (es. `1.100.2`) dalle card.
- Version bump: 0.1.88 -> 0.1.89.

## 2026-01-20 (mdi icon cache + lights redesign)
- Add-on: cache locale icone `mdi:*` (download on-demand e serve via `/api/icons/mdi/<name>.svg`, fallback placeholder se offline).
- Add-on: sync icone su boot e quando modifichi/aggiungi device; endpoint admin `POST /api/icons/sync`.
- UI User (Luci): redesign stile "lista" con sezioni per categoria, icone e slider in stile app.
- Version bump: 0.1.89 -> 0.1.90.

## 2026-01-20 (user api gate fix)
- Gate porta User: consentito `GET /api/devices` (necessario alla pagina Luci) e consentite solo icone `GET /api/icons/mdi/*` (bloccato `POST /api/icons/sync`).
- Version bump: 0.1.90 -> 0.1.91.

## 2026-01-20 (state store robust)
- Fix: `StateStore.read_raw()` ora gestisce JSON corrotto rinominando il file in `state.json.corrupt.<timestamp>` e ripartendo da vuoto (evita 500 su `/api/devices`).
- Version bump: 0.1.91 -> 0.1.92.

## 2026-01-20 (user lights tap targets)
- UI User (Luci): toggle anche su tap dell'icona (oltre al nome) per rendere il comando piu' usabile.
- Version bump: 0.1.92 -> 0.1.93.

## 2026-01-20 (user lights polish)
- UI User (Luci): tutta la riga e' touch per toggle (slider escluso); rimossa label ON/OFF; nascosta sezione "Luci"; icona visibile bianca da OFF e gialla da ON.
- Version bump: 0.1.93 -> 0.1.94.

## 2026-01-20 (user darker background)
- UI User: gradient reso piu' "nero" (meno blu) regolando posizione/alpha del blu.
- Version bump: 0.1.94 -> 0.1.95.

## 2026-01-20 (user typography tune)
- UI User: testi meno "bianchi" e meno bold; icone meno abbaglianti (bianco soft in OFF, giallo soft in ON).
- Version bump: 0.1.95 -> 0.1.96.

## 2026-01-20 (user icon intensity)
- UI User (Luci): icona ON ora scala di intensita' (giallo/glow) in base alla % dimmer.
- Version bump: 0.1.96 -> 0.1.97.

## 2026-01-20 (mdi icon yellow)
- UI User (Luci): icona MDI renderizzata come maschera (no filter), cosi' diventa davvero bianca in OFF e gialla in ON (intensita' da dimmer).
- Version bump: 0.1.97 -> 0.1.98.

## 2026-01-20 (user slider white)
- UI User (Luci): slider dimmer reso bianco (coerente con testi).
- Version bump: 0.1.98 -> 0.1.99.

## 2026-01-20 (user covers popup + icons)
- UI User (Cover): layout lista stile app, bottoni Apri/Stop/Chiudi a icona, tap sulla riga apre popup con regolazione % (slider + preview).
- Version bump: 0.1.99 -> 0.1.100.

## 2026-01-20 (cover slider tint)
- UI User (Cover): slider reso "bianco sporco" (meno saturo).
- Version bump: 0.1.100 -> 0.1.101.

## 2026-01-20 (fixed background)
- UI User (Luci/Cover): background centrato e fisso durante lo scroll (overlay `body::before`).
- Version bump: 0.1.101 -> 0.1.102.

## 2026-01-20 (background centered)
- UI User (Luci/Cover): centro del radial-gradient allineato a `50% 50%` (centrato in altezza e larghezza).
- Version bump: 0.1.102 -> 0.1.103.

## 2026-01-20 (vertical centering)
- UI User (Luci/Cover): se ci sono pochi dispositivi, la lista viene centrata verticalmente (se supera l'altezza, resta scroll normale).
- Version bump: 0.1.103 -> 0.1.104.

## 2026-01-20 (cover icon + popup refine)
- UI User (Cover): icona stato da bianco->blu in base alla % apertura; nel popup percentuale sopra il titolo e regolazione con drag sul "pill" (rimosso slider sotto).
- Version bump: 0.1.104 -> 0.1.105.

## 2026-01-20 (cover light fill)
- UI User (Cover): nel popup il riempimento del "pill" non e' viola: ora simula la "luce che entra" (gradiente chiaro/caldo proporzionale alla %).
- Version bump: 0.1.105 -> 0.1.106.

## 2026-01-20 (cover sky fill)
- UI User (Cover): popup pill fill "cielo azzurro" con intensita' che cresce con la % (molto tenue a bassa apertura).
- Version bump: 0.1.106 -> 0.1.107.

## 2026-01-20 (cover sky contrast)
- UI User (Cover): aumentato contrasto del pill e intensita' del cielo azzurro (stacco piu' leggibile anche a basse %).
- Version bump: 0.1.107 -> 0.1.108.

## 2026-01-20 (cover color alignment)
- UI User (Cover): allineata la curva/tonalita' del colore tra icona stato e fill del popup (stessa "linea" di dimmerazione).
- Version bump: 0.1.108 -> 0.1.109.

## 2026-01-20 (cover reverse icon)
- Admin: aggiunta opzione cover `reverse_icon` (inverti indicatore colore per oscuranti).
- UI User (Cover): icona e fill del popup usano curva invertita quando `reverse_icon=true`.
- Version bump: 0.1.109 -> 0.1.110.

## 2026-01-20 (ui font weights)
- UI: ridotti i font-weight (meno "grassetto") su pagine User (Luci/Cover) e Admin.
- Version bump: 0.1.110 -> 0.1.111.

## 2026-01-20 (cover reverse popup)
- UI User (Cover): nel popup, fill/handle e drag sono invertiti quando `reverse_icon=true` (0% mostra il colore “invertito”).
- Version bump: 0.1.111 -> 0.1.112.

## 2026-01-20 (groups + manual order)
- Admin: campo `group` opzionale per device (senza # obbligatorio) + configurazione ordine gruppi (uno per riga).
- User UI (Luci/Cover): raggruppamento per `group` e ordinamento secondo `group_order` (aggiornabile anche via realtime).
- API: aggiunti `GET/PUT /api/ui` e `group_order` in `GET /api/meta`.
- Version bump: 0.1.112 -> 0.1.113.

## 2026-01-20 (groups drag & drop)
- Admin: lista gruppi rilevati dai dispositivi + drag&drop per riordinare (sincronizzata col textarea).
- Version bump: 0.1.113 -> 0.1.114.

## 2026-01-20 (backup text)
- Admin: aggiunti backup/ripristino in formato testo (copia/incolla) + API `GET /api/backup` e `POST /api/restore` (crea anche un `.bak` del file stato).
- Version bump: 0.1.114 -> 0.1.115.

## 2026-01-20 (user extra)
- User UI: aggiunta pagina `EXTRA` (`/extra`) per dispositivi categoria `Switch`/`Extra` (toggle-only).
- Version bump: 0.1.115 -> 0.1.116.

## 2026-01-20 (backup download + admin links)
- Admin: backup scaricabile (`GET /api/backup/file`) + import da file (riempie textarea per ripristino).
- Admin: link diretti alle pagine User `Luci`/`Cover`/`EXTRA` (porta `8124`).
- Version bump: 0.1.116 -> 0.1.117.

## 2026-01-20 (extra only)
- User UI: i dispositivi `Switch/Extra` non compaiono piu' nella pagina Luci (solo in `EXTRA`).
- Version bump: 0.1.117 -> 0.1.118.

## 2026-01-20 (mdi suggestions)
- Admin: suggerimenti icone MDI basati sulle icone gia' usate (endpoint `GET /api/icons/used` + datalist negli input).
- Version bump: 0.1.118 -> 0.1.119.

## 2026-01-20 (group suggestions)
- Admin: tendina/suggerimenti per `group` basata sui gruppi gia' presenti nei dispositivi.
- Version bump: 0.1.119 -> 0.1.120.

## 2026-01-20 (group dropdown)
- Admin: `group` ora usa una vera tendina (select) + campo custom, invece di `datalist` (piu' compatibile).
- Version bump: 0.1.120 -> 0.1.121.

## 2026-01-20 (restore robustness)
- Backup: ripristino piu' tollerante (BOM/paste) + mostra errore reale in UI Admin.
- Version bump: 0.1.121 -> 0.1.122.

## 2026-01-20 (dedupe devices)
- Admin: bottone `Rimuovi duplicati` e endpoint `POST /api/devices/dedupe` (tiene l'ultima definizione).
- API: blocco creazione device con stesso indirizzo (HTTP 409).
- Version bump: 0.1.122 -> 0.1.123.

## 2026-01-20 (edit address)
- Admin: possibile modificare `Subnet/Device/Channel` in modifica tramite checkbox "Modifica indirizzo".
- API/Store: supporto cambio indirizzo (migra anche lo stato salvato) con controllo duplicati (409).
- Version bump: 0.1.123 -> 0.1.124.

## 2026-01-20 (edit address ui fix)
- Admin: fix checkbox "Modifica indirizzo" (abilita correttamente i campi anche con CSS width input).
- Version bump: 0.1.124 -> 0.1.125.

## 2026-01-20 (active-only filter)
- User UI (Luci/Cover/EXTRA): aggiunto toggle (icona 3 linee) per mostrare solo dispositivi attivi; giallo = filtro attivo.
- Version bump: 0.1.125 -> 0.1.126.

## 2026-01-20 (filter button position)
- User UI (Luci/Cover/EXTRA): icona filtro centrata in basso.
- Version bump: 0.1.126 -> 0.1.127.

## 2026-01-20 (filter button position top)
- User UI (Luci/Cover/EXTRA): icona filtro centrata in alto.
- Version bump: 0.1.127 -> 0.1.128.

## 2026-01-20 (double safety checks)
- Admin UI: "Svuota" richiede conferma doppia (confirm + parola `SVUOTA`).
- Admin UI: "Rimuovi duplicati" richiede conferma doppia (confirm + parola `DEDUPE`).
- Version bump: 0.1.128 -> 0.1.129.

## 2026-01-20 (ui fixes + confirm hints)
- User UI (Luci/Cover/EXTRA): fix click effect sul filtro (evita shift mantenendo `translateX(-50%)` anche su `:active`).
- Admin UI: promemoria visibile e tooltip con parole di conferma `SVUOTA` / `DEDUPE`.
- Version bump: 0.1.129 -> 0.1.130.

## 2026-01-20 (realtime dedupe)
- Backend: evita publish/broadcast realtime quando lo stato non cambia (cache in memoria inizializzata dal file stato).
- Riduce carico CPU/rete sui client (Chrome "scheda rallenta").
- Version bump: 0.1.130 -> 0.1.131.

## 2026-01-20 (collapsible groups default)
- User UI (Luci/Cover/EXTRA): gruppi collassati di default alla prima apertura (preferenza salvata in localStorage).
- User UI: toggle globale per collassare/espandere tutto resta disponibile.
- Version bump: 0.1.131 -> 0.1.132.

## 2026-01-20 (collapsible groups default expanded)
- User UI (Luci/Cover/EXTRA): default ripristinato a gruppi espansi alla prima apertura (non forza il collasso).
- Version bump: 0.1.132 -> 0.1.133.

## 2026-01-20 (cover start delay fix)
- Cover: la simulazione posizione non parte subito al comando (evita sfasamenti se il motore parte in ritardo).
- Cover: inizia quando arriva la conferma OPEN/CLOSE dal bus; fallback dopo 1s se non arriva.
- Version bump: 0.1.133 -> 0.1.134.

## 2026-01-21 (addon icon)
- Add-on: impostata icona/Logo usando `www/e-control nobg.png` -> `icon.png` e `logo.png`.
- Version bump: 0.1.134 -> 0.1.135.

## 2026-01-21 (admin header logo)
- Admin UI: aggiunto logo in alto a sinistra (usa `app/static/logo.png`).
- Version bump: 0.1.135 -> 0.1.136.

## 2026-01-21 (admin logo size)
- Admin UI: logo in header ingrandito (3x).
- Version bump: 0.1.136 -> 0.1.137.

## 2026-01-21 (admin header title)
- Admin UI: titolo header aggiornato con prefisso “e-hdl”.
- Version bump: 0.1.137 -> 0.1.138.

## 2026-01-21 (lights watermark)
- User UI (Luci): aggiunto watermark centrale (trasparente) usando `app/static/user/e-light-addon.png`.
- Version bump: 0.1.138 -> 0.1.139.

## 2026-01-21 (lights watermark size)
- User UI (Luci): watermark ridotto a metà dimensione.
- Version bump: 0.1.139 -> 0.1.140.

## 2026-01-21 (lights watermark opacity)
- User UI (Luci): watermark meno trasparente (più evidente).
- Version bump: 0.1.140 -> 0.1.141.

## 2026-01-21 (lights watermark opacity 2)
- User UI (Luci): watermark ancora più evidente (opacità aumentata).
- Version bump: 0.1.141 -> 0.1.142.

## 2026-01-21 (lights watermark opacity 3)
- User UI (Luci): watermark ancora più evidente (opacità aumentata).
- Version bump: 0.1.142 -> 0.1.143.

## 2026-01-21 (lights watermark color)
- User UI (Luci): watermark usa i colori originali (rimosso grayscale).
- Version bump: 0.1.143 -> 0.1.144.

## 2026-01-21 (lights watermark opacity 4)
- User UI (Luci): watermark ancora più evidente (opacità aumentata).
- Version bump: 0.1.144 -> 0.1.145.

## 2026-01-21 (lights watermark opacity 5)
- User UI (Luci): watermark ancora più evidente (opacità aumentata).
- Version bump: 0.1.145 -> 0.1.146.

## 2026-01-21 (lights watermark opacity off)
- User UI (Luci): watermark senza trasparenza (`opacity: 1`).
- Version bump: 0.1.146 -> 0.1.147.

## 2026-01-21 (lights cards transparency)
- User UI (Luci): card/lista e righe più trasparenti (background rgba ridotti).
- Version bump: 0.1.147 -> 0.1.148.

## 2026-01-21 (lights cards transparency 2)
- User UI (Luci): ulteriore aumento trasparenza card/lista e righe.
- Version bump: 0.1.148 -> 0.1.149.

## 2026-01-21 (cover/extra watermark + transparency)
- User UI (Cover): watermark centrale `app/static/user/e-cover-addon.png` + card/lista più trasparenti.
- User UI (EXTRA): watermark centrale `app/static/user/e-extra-addon.png` + card/lista più trasparenti.
- Version bump: 0.1.149 -> 0.1.150.

## 2026-01-21 (lights watermark swap)
- User UI (Luci): watermark aggiornato a `app/static/user/e-light-addon2.png`.
- Version bump: 0.1.150 -> 0.1.151.

## 2026-01-21 (cover slider timing)
- Cover: `SET_POSITION` usa l'istante di invio comando come start_time (non quando arriva conferma/fallback) per evitare sfasamenti.
- Cover: STOP schedulato più affidabile (invia STOP 2 volte).
- Version bump: 0.1.151 -> 0.1.152.

## 2026-01-21 (cover slider timing 2)
- Cover: STOP schedulato usa il tempo rimanente quando la conferma del bus arriva in ritardo (compensa il lag di start).
- Version bump: 0.1.152 -> 0.1.153.

## 2026-01-21 (cover popup handle)
- User UI (Cover): handle del popup posizionato correttamente sulla percentuale (aggiornato dopo layout).
- Version bump: 0.1.153 -> 0.1.154.

## 2026-01-21 (user UI performance)
- User UI (Cover/Luci/EXTRA): niente piu' re-render completo ad ogni `*_state` via WebSocket; aggiorna solo la riga interessata per ridurre lag e click in ritardo.
- User UI (Cover/Luci/EXTRA): conteggio `attivi/totale` aggiornato in modo throttled.
- Backend: aggiunto log DEBUG con timing su `/api/control/cover/...` per verificare la latenza server-side.
- Version bump: 0.1.154 -> 0.1.155.

## 2026-01-21 (cover stop accuracy)
- Cover: ridotto polling `read_status` durante il movimento (2.0s) e sospeso vicino allo stop programmato per evitare ritardi nell'esecuzione del comando STOP.
- Version bump: 0.1.155 -> 0.1.156.

## 2026-01-21 (cover slider sync)
- Cover: per `SET_POSITION` avvia l'interpolazione e lo stop automatico solo quando il movimento viene rilevato (StatusResponse 1/2) oppure dopo un fallback piu' lungo (2.5s), per evitare desync quando il motore parte in ritardo.
- Cover: a fine stop non forza piu' la posizione a quella richiesta; usa la stima basata sul tempo (con snap +/-2%) così la UI non "mente" e permette nuovi comandi.
- Version bump: 0.1.156 -> 0.1.157.

## 2026-01-21 (multi-cover stability)
- Gateway: scheduler comandi cover con pacing (~180ms) + coalescing per cover (evita flood UDP quando muovi fino a ~12 tapparelle insieme da UI/HA).
- Cover: dopo STOP fa un `read_status` best-effort per ridurre stati stuck.
- Version bump: 0.1.157 -> 0.1.158.

## 2026-01-21 (covers UI separator)
- User UI (Cover): fix carattere separatore nello stato (usa `&#183;`/`\\u00B7` per evitare glitch encoding tipo "Â·").
- Version bump: 0.1.158 -> 0.1.159.

## 2026-01-21 (cover flood protection)
- Cover: pacing globale dei telegrammi (inclusi STOP programmati) per evitare perdita comandi quando muovi molte tapparelle insieme (8-12).
- Version bump: 0.1.159 -> 0.1.160.

## 2026-01-22 (cover groups / group blind)
- Aggiunti gruppi cover persistenti (`ui.cover_groups`) con CRUD via `GET/POST/DELETE /api/cover_groups`.
- MQTT discovery: pubblicate entita' cover di gruppo con topic `cmd/cover_group/+` e `cmd/cover_group_pos/+` + stati `state/cover_group_*` (retain).
- Cleanup: quando un gruppo viene rimosso, viene svuotata la discovery e gli stati retain del gruppo.
- Admin UI: sezione "Gruppi Cover (Group blind)" per creare/modificare/eliminare gruppi e selezionare i membri.
- Version bump: 0.1.160 -> 0.1.161.

## 2026-01-22 (user UI cover groups)
- User UI (Cover): mostra i gruppi cover (group blind) in alto, con comandi Apri/Stop/Chiudi e popup posizione che invia `SET_POSITION` al gruppo.
- Backend: `GET /api/cover_groups` consentito anche su porta user.
- Version bump: 0.1.161 -> 0.1.162.

## 2026-01-22 (cover groups stable id)
- Gruppi cover: aggiunto campo `id` persistente e univoco (stabile anche se rinomini il gruppo) per evitare collisioni e gruppi "rotti".
- Admin UI: usa `id` nascosto quando modifichi/elimini un gruppo.
- User UI (Cover): usa `id` per comandi/stato dei gruppi.
- Version bump: 0.1.162 -> 0.1.163.

## 2026-01-22 (cover group custom icon)
- Gruppi cover: aggiunto campo `icon` opzionale (mdi) ai gruppi (salvato e restituito da `/api/cover_groups`).
- MQTT discovery: pubblica `icon` anche per le entita' cover di gruppo.
- Admin UI: campo "Icona gruppo (mdi)" per i gruppi cover.
- User UI (Cover): icona del gruppo usa la tua mdi (fallback: `mdi:blinds-group`).
- Version bump: 0.1.163 -> 0.1.164.

## 2026-01-22 (cover group icon realtime)
- WebSocket snapshot include `cover_groups` e broadcast `cover_groups` dopo save/delete per aggiornare la user UI senza refresh.
- Version bump: 0.1.164 -> 0.1.165.

## 2026-01-23 (cover group icon cache)
- Fix: cache/download icone MDI anche per i Cover Group (UI user mostrava placeholder).
- `GET /api/icons/used` ora include anche le icone usate dai gruppi.
- Version bump: 0.1.165 -> 0.1.166.

## 2026-01-23 (cover command reliability)
- Fix affidabilita': coda comandi cover resa thread-safe con lock e STOP prioritario (stile Control4).
- Cover groups: invio comandi ai membri in sequenza (evita flood UDP e race con molti dispositivi).
- Version bump: 0.1.166 -> 0.1.167.

## 2026-01-23 (cover start delay)
- Cover: aggiunto `start_delay_s` (ritardo avvio) per riallineare UI/STOP quando il motore parte in ritardo.
- Admin UI: campo "Ritardo avvio (s)" per device cover; viene applicato anche nei gruppi.
- Version bump: 0.1.167 -> 0.1.168.

## 2026-01-23 (cover sync + discovery stable id)
- Cover: fix pacing telegram (lock copre davvero `send()`), anche `read_status()` passa dal lock per evitare flood/ritardi con molte cover.
- Cover: StatusResponse ora aggiorna correttamente start/stop anche da comandi HDL (bidirezionale) e avvio pending confermato ignora `start_delay_s` (parte subito quando il bus conferma).
- Cover: aggiunto "probe" leggero (pochi `read_status`) durante pending + fallback dinamico basato su `start_delay_s`.
- MQTT discovery: topic `object_id` stabile per luci/cover (non dipende dal nome) per evitare entita' duplicate quando rinomini.
- Nota: eventuali entita' vecchie create con topic basato sul nome vanno rimosse manualmente una sola volta da Home Assistant.
- Version bump: 0.1.168 -> 0.1.169.

## 2026-01-26 (mqtt reconnect re-subscribe)
- Fix: dopo restart/disconnect del broker MQTT, il client ora si riconnette e ripristina automaticamente le subscribe ai topic `cmd/*` (evita HA che non comanda finché non riavvii l’add-on).
- Version bump: 0.1.182 -> 0.1.183.

## 2026-01-26 (dry contact / binary_sensor)
- Admin UI: aggiunta sezione "Dry contact" (accordion) per creare ingressi digitali.
- MQTT discovery: pubblicate entità `binary_sensor` + stato su `buspro/state/dry_contact/...` (ON/OFF).
- Listener telegrammi: decodifica `ControlPanelACResponse` (0xE3D9) e aggiornamento realtime + retain.
- Version bump: 0.1.183 -> 0.1.184.

## 2026-01-26 (mqtt availability after reconnect)
- Fix: su ogni (re)connect MQTT ripubblica `buspro/availability` e la discovery (utile se il broker perde i retained dopo restart / persistence off).
- Version bump: 0.1.184 -> 0.1.185.

## 2026-01-26 (dry contact ui note)
- UI: aggiunta nota su telegramma UDP ascoltato per i Dry contact (ControlPanelACResponse / 0xE3D9).
- Version bump: 0.1.185 -> 0.1.186.

## 2026-01-26 (dry contact payload variant)
- Fix: per `ControlPanelACResponse` (0xE3D9) l’ID device viene sempre preso da `source_address`; il primo byte del payload può variare (es. 18) quindi non viene più usato come check.
- Version bump: 0.1.186 -> 0.1.187.

## 2026-01-26 (dry contact trace payload x)
- Dry contact: salva e mostra il primo byte del payload (`x`, es. 18/29) e lo pubblica come attributo MQTT (`buspro/state/dry_contact_attr/...`) via `json_attributes_topic`.
- Version bump: 0.1.187 -> 0.1.188.

## 2026-01-26 (user hub page + links)
- User UI: aggiunta pagina `home` (landing) con pulsanti Luci/Cover/Extra e link aggiuntivi configurabili.
- Admin UI: sezione "Home (hub) links" per creare/ordinare link (titolo, URL, icona mdi, show, nuova scheda).
- Icone mdi: sync anche per le icone dei link hub.
- Version bump: 0.1.188 -> 0.1.189.

## 2026-01-26 (hub fixed buttons icons)
- Admin UI: configurazione icone pulsanti fissi Home (Luci/Cover/Extra).
- User UI: Home usa le icone configurate via `api/meta.hub_icons`.
- Version bump: 0.1.189 -> 0.1.190.

## 2026-01-26 (hub fixed buttons visibility)
- Admin UI: opzioni per nascondere i pulsanti fissi Home (Luci/Cover/Extra).
- User UI: Home rispetta `api/meta.hub_show` per mostrare/nascondere.
- Version bump: 0.1.190 -> 0.1.191.

## 2026-01-26 (home2 tile UI)
- User UI: aggiunta pagina `home2` stile “tile” (tipo screenshot) con logo ekonex in alto (`/www/ekonex.png`) e senza scritte/sottotitoli.
- Server: esposta directory repo `www/` su route `/www` (accessibile anche su USER_PORT).
- Admin: aggiunto link rapido “Home2”.
- Version bump: 0.1.191 -> 0.1.192.

## 2026-01-26 (home2 responsive tiles + ekonex logo)
- User UI: Home2 ora usa tile staccate e responsive (grid) per smartphone.
- Logo: prova automaticamente `www/logo_ekonex.png` (e fallback) e lo nasconde se non presente.
- Version bump: 0.1.192 -> 0.1.193.

## 2026-01-26 (home2 tweaks)
- User UI: rimosso riquadro contenitore grande; tile sempre “staccate” e responsive.
- Logo: usa path assoluto `/www/logo_ekonex.png` + fallback.
- UI: cerchi icone +15%.
- Version bump: 0.1.193 -> 0.1.194.

## 2026-01-26 (home2 centered rows + ingress-safe logo)
- User UI: Home2 centra le righe (layout flex-wrap) per avere 3+3 quando ci sono 6 tile.
- Logo: path relativo `www/logo_ekonex.png` (più compatibile con Ingress).
- Version bump: 0.1.194 -> 0.1.195.

## 2026-01-26 (www assets fix + home2 layout)
- Fix: `/www/*` ora servito via endpoint dedicato (evita 500) e aggiunto `/favicon.ico` (204).
- User UI: Home2 layout 4-3 (desktop) e 2-2-2-1 (smartphone).
- Version bump: 0.1.195 -> 0.1.196.

## 2026-01-26 (www dir auto-detect)
- Fix: `/www/*` ora cerca automaticamente la cartella `www` (repo root / percorsi container / override `BUSPRO_WWW`) per evitare 404 quando la directory non è dove ci si aspetta.
- Version bump: 0.1.196 -> 0.1.197.

## 2026-01-26 (docker include www)
- Fix: il build Docker ora copia `www/` dentro l’immagine (`/app/www`) così `GET /www/logo_ekonex.png` funziona anche in Home Assistant.
- Version bump: 0.1.197 -> 0.1.198.

## 2026-01-26 (logo ekonex in static)
- UI: copiato `www/logo_ekonex.png` in `app/static/logo_ekonex.png` e Home2 ora lo carica da `/static/...` (più affidabile, niente 404).
- Version bump: 0.1.198 -> 0.1.199.

## 2026-01-26 (home2 logo x4)
- UI: logo ekonex ingrandito ~4x su Home2 (responsive).
- Version bump: 0.1.199 -> 0.1.200.

## 2026-01-26 (home2 vertical centering)
- UI: Home2 ora centra verticalmente logo + pulsanti nella pagina.
- Version bump: 0.1.200 -> 0.1.201.

## 2026-01-26 (home2 logo +15%)
- UI: logo ekonex aumentato ~15% (responsive).
- Version bump: 0.1.201 -> 0.1.202.

## 2026-01-26 (home2 logo +15% again)
- UI: logo ekonex aumentato ancora ~15% (responsive).
- Version bump: 0.1.202 -> 0.1.203.

## 2026-01-26 (home2 mobile 2 columns)
- UI: su viewport stretti Home2 forza layout 2 colonne (2-2-2-2...) invece di una lista verticale.
- Version bump: 0.1.203 -> 0.1.204.

## 2026-01-26 (home2 mobile grid)
- UI: su smartphone Home2 usa grid 2 colonne (più robusto di flex) per evitare layout a lista.
- Version bump: 0.1.204 -> 0.1.205.

## 2026-01-26 (home2 transparent tiles)
- UI: Home2 pulsanti più “puliti” (tile trasparenti, focus su icona + testo).
- Version bump: 0.1.205 -> 0.1.206.

## 2026-01-26 (home2 square semi-transparent tiles)
- UI: ripristinati tile con background (più chiari) ma ora quadrati (senza smussature) e con gradiente trasparente.
- Version bump: 0.1.206 -> 0.1.207.

## 2026-01-26 (home2 logo +15% again again)
- UI: logo ekonex aumentato ancora ~15% (responsive).
- Version bump: 0.1.207 -> 0.1.208.

## 2026-01-26 (hidden back gesture)
- User UI: long-press angolo in alto a sinistra per tornare indietro (fallback a `home2` se non c’è history).
- Version bump: 0.1.208 -> 0.1.209.

## 2026-01-26 (proxy external links)
- Admin UI: gestione target proxy (name + base URL) e lista.
- Server: aggiunta route `/ext/<name>/...` (reverse proxy) con rewrite best-effort per HTML/CSS, Location e cookie Path (per mantenere navigazione dentro l’add-on e avere back/gesture).
- Version bump: 0.1.209 -> 0.1.210.

## 2026-01-26 (proxy websockets)
- Proxy: aggiunta route WebSocket `/extws/<name>/...` + script injected nelle pagine proxate per riscrivere `fetch`/XHR/WebSocket verso `/ext` e `/extws`.
- Version bump: 0.1.210 -> 0.1.211.

## 2026-01-26 (proxy assets + stream)
- Proxy: aggiunti fallback `/assets/*` e `/api/stream` (streaming) usando il target corrente da Referer/cookie, per pagine che fanno richieste assolute.
- Version bump: 0.1.211 -> 0.1.212.

## 2026-01-26 (proxy back gesture)
- Proxy: iniezione gesture “long-press angolo alto-sinistra” anche nelle pagine proxate (`/ext/...`) con fallback a `/home2`.
- Version bump: 0.1.212 -> 0.1.213.

## 2026-01-26 (proxy rewrite absolute api)
- Proxy: migliorata riscrittura `fetch`/XHR anche per URL assoluti su stessa origin (`http://<addon>/api/...`) così le app legacy (porta 1977) non chiamano più `/api/...` diretto ma passano da `/ext/<name>/...`.
- Version bump: 0.1.213 -> 0.1.214.

## 2026-01-26 (proxy eventsource content-type)
- Proxy: `/api/stream` ora forza `Content-Type: text/event-stream` (EventSource) e streaming line-based per evitare warning MIME type.
- Version bump: 0.1.214 -> 0.1.215.

## 2026-01-26 (ingress open web ui)
- Fix: quando l’add-on è aperto via Ingress (pulsante “Apri interfaccia utente web”), la route `/` serve sempre la User UI (Home2) per evitare pagina Admin con errori `{"detail":"Not Found"}`.
- Version bump: 0.1.215 -> 0.1.216.

## 2026-01-26 (ingress double-slash)
- Fix: normalizza path con `//` su Ingress (es. `.../hassio_ingress/<token>//`) per evitare 404 e far matchare correttamente `/`.
- Version bump: 0.1.216 -> 0.1.217.

## 2026-01-26 (ingress to admin)
- Config: Ingress ora punta alla Admin UI (porta 8125) invece della User UI.
- Version bump: 0.1.217 -> 0.1.218.

## 2026-01-26 (ingress admin via user port)
- Fix: Ingress rimane su porta 8124, ma se arriva da Ingress mostra Admin UI e sblocca i path admin sul USER_PORT (solo via header Ingress).
- Version bump: 0.1.218 -> 0.1.219.

## 2026-01-26 (ingress entry index.html)
- Fix: `ingress_entry` ora punta a `index.html` (evita URL `.../hassio_ingress/<token>//` che in alcune versioni di HA può dare 404).
- Server: aggiunta route `GET /index.html` che serve l’Admin UI.
- Version bump: 0.1.219 -> 0.1.220.

## 2026-01-26 (ingress admin cookie)
- Fix: set cookie `buspro_ingress=1` quando aperto via Ingress, così le chiamate API della pagina Admin non vengono bloccate su USER_PORT anche se HA non inoltra gli header Ingress su tutte le richieste.
- Version bump: 0.1.220 -> 0.1.221.

## 2026-01-26 (admin ingress basePrefix)
- Fix: Admin UI ora gestisce Ingress entry `index.html` (evita chiamate tipo `.../index.html/api/...` che causavano 404).
- Version bump: 0.1.221 -> 0.1.222.

## 2026-01-26 (proxy nav rewrite)
- Proxy: migliorata riscrittura navigazione (link `/security/...` ecc) con intercept click + patch `location.assign/replace` e supporto attributi non quotati (`href=/...`).
- Version bump: 0.1.222 -> 0.1.223.

## 2026-01-26 (proxy unknown routes fallback)
- Proxy: se è attivo un target (`buspro_px` cookie), route non-API tipo `/security/functions` vengono proxate invece di 404 (SPA fallback).
- Version bump: 0.1.223 -> 0.1.224.

## 2026-01-23 (buspro sniffer)
- Aggiunto Sniffer telegrammi BusPro (RX) con start/stop, filtri (operate_code/src/dst), e download.
- Salvataggio opzionale su `/share` in formato `jsonl` + download buffer se file non presente.
- Admin UI: pannello Sniffer con pulsanti Start/Stop/Scarica/Pulisci.
- Version bump: 0.1.169 -> 0.1.170.

## 2026-01-23 (sniffer live)
- Sniffer: endpoint `GET /api/sniffer/recent?limit=` per visualizzare gli ultimi telegrammi catturati.
- Admin UI: sezione Live (ultimi telegrammi) aggiornata automaticamente.
- Version bump: 0.1.170 -> 0.1.171.

## 2026-01-25 (umidità 12-in-1)
- Aggiunti sensori Umidità (tipo device `humidity`) con MQTT discovery + stati su topic `.../state/humidity/...`.
- Listener telegrammi 12-in-1: parsing umidità da `ReadSensorsInOneStatusResponse` (0x1605) con fallback raw opcode 0x1630.
- Admin UI: CRUD Umidità + realtime via WebSocket.
- Version bump: 0.1.175 -> 0.1.176.

## 2026-01-25 (luminosita 12-in-1)
- Aggiunti sensori Luminosita (tipo device `illuminance`) con MQTT discovery + stati su topic `.../state/illuminance/...`.
- Listener 12-in-1: parsing luminosita da `ReadSensorsInOneStatusResponse` (0x1605) con fallback raw opcode 0x1630.
- Admin UI: CRUD Luminosita + realtime via WebSocket.
- Version bump: 0.1.176 -> 0.1.177.

## 2026-01-25 (illuminance fix 0x1646)
- Fix: parsing luminosita anche da `ReadSensorStatusResponse` opcode raw 0x1646 (payload 16-bit) per evitare valore `?` in UI.
- Version bump: 0.1.177 -> 0.1.178.

## 2026-01-25 (illuminance fix 0x1605 alt format)
- Fix: alcuni 12-in-1 inviano la luminosita (lux) nel payload 0x1605 come 16-bit in `payload[2:4]` e lasciano `payload[5:8]` a `0xFFFFFF`; aggiunto fallback per evitare valore `?` in UI.
- Version bump: 0.1.178 -> 0.1.179.

## 2026-01-25 (cover no% clones + groups)
- MQTT discovery: aggiunte entita' cover clone "no%" (solo OPEN/CLOSE/STOP, senza posizione) per ogni cover e per ogni cover group; raggruppate sotto device `BusPro Cover no %`.
- Version bump: 0.1.179 -> 0.1.180.

## 2026-01-25 (cover no% assumed_state)
- MQTT discovery: per le entita' "no%" aggiunto `assumed_state: true` per avere sempre i comandi Up/Down/Stop disponibili anche se lo stato/posizione in HA e' desincronizzato.
- Version bump: 0.1.180 -> 0.1.181.

## 2026-01-25 (cover no% raw commands)
- MQTT discovery: le entita' "no%" ora pubblicano su topic raw (`cmd/cover_raw/...` e `cmd/cover_group_raw/...`) che usano `cover_open_raw/cover_close_raw` per bypassare la logica posizione/auto-stop e forzare UP/DOWN anche quando HA pensa che sia gia' chiusa/aperta.
- Version bump: 0.1.181 -> 0.1.182.

