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

## Scenari da Admin

Nella pagina Admin, sezione `Scenari: configurazione JSON`, puoi creare un nuovo scenario o modificare uno scenario esistente senza passare dalla UI utente.

- `Nuovo scenario` apre una configurazione vuota.
- `Duplica scenario` copia lo scenario selezionato e lo prepara come nuovo scenario senza ID.
- La ricerca filtra per nome, gruppo, indirizzo BusPro o `entity_id`.
- `Aggiungi visibili` inserisce nello scenario tutti i dispositivi compatibili attualmente filtrati.
- Sono supportati luci BusPro, cover BusPro, gruppi cover, luci/switch Home Assistant e cover Home Assistant.
- Sensori e lock non vengono mostrati perche' il motore scenari non li esegue.

## Smart link Home2

In Admin, sezione `Home (hub) links`, puoi abilitare gli Smart link locale/remoto per i link manuali di Home2.

- Funzione spenta: ogni link usa il campo `URL` normale, come prima.
- Funzione accesa: se Home2 e' aperta da `Host locale`, usa `URL locale`; se e' aperta da `Host remoto`, usa `URL remoto`.
- Debug acceso: ogni click su un link smart scrive nei log la decisione presa.
- Se `URL locale` o `URL remoto` sono vuoti, il link torna al campo `URL` normale.

## Redirect pagine locale/remoto

Nella stessa sezione Admin puoi abilitare `Redirect pagine` per le pagine utente (`/home`, `/home2`, `/home_plus`, `/e-face`, `/lights`, `/covers`, `/scenarios`, `/extra`, `/locks`, `/e-guard`) e per le pagine proxate `/ext/<nome>/`.

- `Base URL locale`: ad esempio `http://192.168.3.24:8124`.
- `Base URL remoto`: ad esempio `http://manager.ekonex.it:20052`.
- All'apertura da remoto, la pagina prova `Base URL locale + /health` con timeout breve.
- Se il browser blocca il `fetch()` verso IP privato, viene provato anche un fallback tramite immagine statica locale.
- Se il locale risponde, resta sulla stessa pagina ma passa al base locale, ad esempio `/lights` -> `http://192.168.3.24:8124/lights`.
- Per le pagine proxate mantiene anche il prefisso `/ext/<nome>/`, ad esempio `/ext/termostati/` -> `http://192.168.3.24:8124/ext/termostati/`.
- Se il locale non risponde, resta sull'URL remoto.
- Se passi da dati mobili a Wi-Fi con la pagina gia' aperta, il controllo viene ripetuto su focus/visibilita'/online e con retry leggero.
- `noredirect=1` disattiva il redirect per una singola apertura, utile per test.
- Con `Debug` acceso vengono loggati esito, host corrente, target scelto e motivo.

## Control4 WebViewer su iPhone

Quando le pagine dell'add-on vengono aperte dentro Control4 WebViewer su iPhone, la WebView iOS puo' chiudere in modo anomalo il WebSocket (`code=1006`). Il sintomo tipico e' una pagina che ogni tanto resta in caricamento o non aggiorna piu' gli stati, anche se il server risponde correttamente.

Per le pagine native BusPro e' disponibile la modalita' polling HTTP:

- non apre il WebSocket `/ws`;
- aggiorna gli stati con richieste HTTP periodiche;
- mantiene la stessa interfaccia e gli stessi comandi;
- e' consigliata solo per i link usati dentro Control4 WebViewer/iPhone.

### Link consigliati per Control4

Imposta nel driver/WebViewer Control4 questi URL, sostituendo `IP_HOME_ASSISTANT` con l'indirizzo corretto:

```text
http://IP_HOME_ASSISTANT:8124/lights?poll=1
http://IP_HOME_ASSISTANT:8124/covers?poll=1
http://IP_HOME_ASSISTANT:8124/scenarios?poll=1
http://IP_HOME_ASSISTANT:8124/extra?poll=1
http://IP_HOME_ASSISTANT:8124/locks?poll=1
```

Per aprire direttamente l'editor scenari dentro la pagina Luci:

```text
http://IP_HOME_ASSISTANT:8124/lights?sc=1&poll=1
```

Per browser normali, app Home Assistant o uso desktop puoi continuare a usare i link senza `poll=1`, cosi' resta attivo il realtime via WebSocket.

### Tutorial rapido

1. Aggiorna l'add-on alla versione `0.1.386` o successiva.
2. Riavvia l'add-on.
3. Verifica la versione:

```bash
curl -s http://127.0.0.1:8124/api/meta | grep version
```

4. Nel progetto Control4, sostituisci i link delle pagine native BusPro con quelli che includono `?poll=1`.
5. Su iPhone chiudi completamente l'app Control4 e riaprila.
6. Apri le pagine dal WebViewer e verifica che gli stati si aggiornino. Con `poll=1` l'aggiornamento puo' richiedere qualche secondo.

### Pagine proxate di altri add-on

I link verso altri add-on proxati, ad esempio:

```text
http://IP_HOME_ASSISTANT:8124/ext/core/security
```

non possono essere convertiti automaticamente in polling, perche' il JavaScript appartiene all'altro add-on. Per queste pagine l'add-on aggiunge diagnostica: se la WebView Control4/iPhone rompe WebSocket o EventSource, nei log compariranno eventi come:

```text
ext_proxy bootstrap_debug ... "kind": "ws_error"
ext_proxy bootstrap_debug ... "kind": "ws_close"
ext_proxy bootstrap_debug ... "kind": "es_error"
```

### Diagnostica log

Per filtrare gli eventi utili:

```bash
ha apps logs a59e0dbb_e_hdl_buspro_mqtt -n 3000 | grep -Ei "ui_log|bootstrap_debug|iPhone|ws_error|ws_close|es_error|fetch_error|js_error|js_rejection"
```

Se una pagina nativa BusPro con `poll=1` funziona, nei log vedrai:

```text
ui_log page=lights phase=poll_mode detail=enabled
```

Se invece vedi `ws_close code=1006`, significa che quella pagina sta ancora usando WebSocket: controlla che nel link Control4 sia presente `poll=1`.

### Note
- Robustezza MQTT: in caso di restart/disconnect del broker, l’add-on si riconnette e ripristina automaticamente le subscribe ai topic comandi.
