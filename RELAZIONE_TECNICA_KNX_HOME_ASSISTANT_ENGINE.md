# Relazione tecnica — KNX in e-Control Hub con motore Home Assistant/XKNX

Data: 2026-10-02  
Stato: architettura approvata dal proprietario; implementazione da eseguire per fasi controllate  
Componenti: e-Control Hub, e-Face, Home Assistant KNX/XKNX, e-Manager

## 1. Decisione

KNX deve rispettare lo stesso criterio gia' adottato per HDL BusPro e Ksenia:

- e-Control Hub e' il configuratore e il catalogo autorevole Ekonex;
- e-Face consuma il contratto driver-neutral Smart Home e non conosce il trasporto KNX;
- Home Assistant KNX/XKNX e' il motore di campo che gestisce tunnel/routing, DPT, Secure, reconnect e telegrammi;
- ETS resta l'autorita' della programmazione fisica KNX;
- e-Manager coordinera' in futuro installazione, compatibilita', aggiornamenti e backup dei componenti Ekonex.

```text
ETS / KNX Panel Home Assistant
             |
             v
Home Assistant KNX / XKNX ---- KNX/IP ---- Bus KNX
             ^
             | API e WebSocket autenticati
             v
e-Control Hub — source=knx
  | catalogo, capability, organizzazione, policy e audit
  | piani, stanze, gruppi, categorie, icone, visibilita'
  v
Smart Home API v1
  v
e-Face / scenari / e-Voice
```

## 2. Principio comune a tutti i bus

Ogni driver deve produrre lo stesso oggetto logico:

- `source` e `device_id` stabile;
- nome e classe dispositivo;
- capability consentite;
- stato, disponibilita', qualita' e timestamp;
- organizzazione autorevole e-Control;
- descrittori di comando validati server-side;
- nessun indirizzo fisico o credenziale necessario al client utente.

Per KNX la sorgente e' `knx`. L'`entity_id` Home Assistant e i riferimenti KNX sono mapping nativi conservati nel record del driver, non l'identita' mostrata a e-Face. Rinominare un'entita' o modificare un group address non deve cancellare piano, stanza, categorie, icona o scenari Ekonex.

## 3. Ruoli e responsabilita'

### e-Control Hub

- rileva lo stato dell'integrazione KNX Home Assistant;
- acquisisce progetto, entita' e configurazioni tramite API WebSocket KNX supportate;
- crea e conserva il catalogo `source=knx`;
- propone classificazione capability-based e consente correzione installatore;
- conserva piani, stanze, gruppi, categorie, ordine, icone e visibilita';
- inoltra soltanto comandi consentiti alle API servizi Home Assistant;
- verifica lo stato conseguente e distingue `confirmed`, `estimated`, `timeout` e `unavailable`;
- espone diagnostica senza chiavi, password o payload sensibili;
- include mapping e organizzazione nel backup locale e-Control.

### Home Assistant KNX/XKNX

- connessione KNX/IP automatica, tunnelling UDP/TCP/Secure o routing;
- KNX IP Secure e Data Secure tramite keyring;
- codifica e decodifica DPT;
- state updater, letture iniziali, telegrammi live e reconnect;
- entity store KNX e servizi di comando;
- gestione del progetto ETS attraverso le API del pannello KNX.

### e-Face

- riceve KNX tramite il contratto Smart Home v1 esistente;
- visualizza luci, switch, cover, clima, sensori e scene come HDL/Ksenia;
- non usa direttamente API Home Assistant e non conosce group address o DPT;
- invia i comandi a e-Control con `source=knx` e ID Ekonex.

## 4. Interfacce Home Assistant utilizzate

### REST stabile

- `GET /api/states` per stato e attributi;
- `POST /api/services/<domain>/<service>` per comandi tipizzati;
- nessun `knx.send` arbitrario accessibile a e-Face o utente.

### WebSocket amministrativa KNX

Il componente ufficiale registra comandi dedicati, fra cui:

- `knx/get_base_data` per connessione, versione XKNX, progetto e DPT;
- `knx/get_knx_project` per struttura progetto disponibile;
- `knx/get_entity_config` e `knx/get_entities_by_group` per mapping;
- `knx/get_schema` e `knx/validate_entity` per configurazione guidata;
- `knx/create_entity`, `knx/update_entity`, `knx/delete_entity` per amministrazione futura;
- API monitor telegrammi per la diagnostica installatore.

La prima release usa lettura e catalogazione. Le operazioni di modifica KNX saranno abilitate solo dopo test di compatibilita' con la versione Home Assistant installata.

### Divieti

- nessuna lettura o scrittura diretta di `.storage`;
- nessuna modifica automatica del YAML;
- nessun accesso diretto al keyring;
- nessun raw send dal browser;
- nessuna deduplicazione per nome, stanza o icona;
- nessuna cancellazione del catalogo se HA o KNX sono offline.

## 5. Identita' e persistenza

Record minimo persistente:

```json
{
  "source": "knx",
  "device_id": "knx:01HV...",
  "native": {
    "entity_id": "light.cucina",
    "config_entry_id": "...",
    "platform": "light",
    "project_fingerprint": "sha256:..."
  },
  "name": "Luce cucina",
  "device_class": "light",
  "capabilities": ["turn_on", "turn_off", "set_brightness"],
  "mapping_summary": {
    "command": "1/1/10",
    "state": "1/2/10",
    "dpt": ["1.001", "5.001"]
  },
  "enabled": false,
  "read_only": true
}
```

L'identita' Ekonex viene assegnata alla prima importazione e poi mantenuta mediante mapping esplicito. I dati specifici KNX servono alla diagnostica installatore ma non vengono pubblicati nel payload utente.

## 6. Flusso configuratore e-Control

Il ramo `Bus e integrazioni > KNX` conterra':

1. **Panoramica** — stato HA, integrazione KNX, XKNX, connessione e progetto;
2. **Importa e sincronizza** — confronto fra catalogo HA KNX e catalogo e-Control;
3. **Dispositivi KNX** — ricerca, classificazione, capability, abilitazione e organizzazione;
4. **Diagnostica** — mapping, DPT, disponibilita', ultimo stato e problemi;
5. **Monitor telegrammi** — fase successiva, riservata all'installatore.

La sincronizzazione produce un diff: nuovi, modificati, mancanti, ambigui. Nessun nuovo dispositivo diventa comandabile senza conferma dell'installatore. Un dispositivo non piu' presente diventa `orphaned`, non viene cancellato.

## 7. Comandi e sicurezza

- e-Face chiama esclusivamente `/api/user/smart-home/knx/<device_id>/command`;
- e-Control risolve internamente l'`entity_id` consentito;
- dominio, azione e valore sono validati contro le capability catalogate;
- e-Control invoca soltanto servizi tipizzati HA (`light.turn_on`, `cover.open_cover`, ecc.);
- successo HTTP significa comando accettato, non confermato;
- la conferma deriva dal successivo stato HA coerente;
- timeout, indisponibilita' e stato stimato sono espliciti;
- lock, accessi, allarme e funzioni critiche restano esclusi dalla prima fase.

## 8. Deduplicazione

KNX resta visibile in Home Assistant perche' HA e' il motore, ma e-Control non deve reimportarlo anche come generica sorgente `ha`.

Regole:

- le entita' riconosciute come KNX sono assegnate soltanto a `source=knx`;
- il mapping usa registry/config entry, mai il nome;
- e-Control non ripubblica a HA le stesse entita' KNX tramite MQTT Discovery;
- entita' ambigue restano escluse finche' l'installatore non le associa;
- e-Face riceve una sola rappresentazione del dispositivo.

## 9. Compatibilita' e versionamento

Il connettore mantiene una matrice delle versioni Home Assistant/KNX API verificate. All'avvio esegue capability detection:

- API disponibili e compatibili: catalogazione attiva;
- API KNX cambiate: diagnostica `incompatibile`, catalogo conservato e comandi disabilitati;
- Home Assistant offline: ultimo catalogo conservato, dispositivi `unavailable`;
- KNX offline ma HA online: diagnostica specifica, nessuna cancellazione.

Gli aggiornamenti non vengono assunti compatibili automaticamente. e-Manager potra' in futuro coordinare aggiornamento, test e rollback.

## 10. Fasi di implementazione

### Fase A — connettore e observer

- client WebSocket autenticato verso Home Assistant;
- health e capability detection KNX;
- import read-only del progetto e delle entita';
- catalogo persistente `source=knx`;
- adapter Smart Home v1 con `read_only=true`;
- UI professionale e-Control per diff e classificazione.

### Fase B — pilot comandi

- luci, dimmer, switch e cover non critiche;
- allowlist server-side;
- conferma tramite stato e timeout;
- audit e diagnostica;
- collaudo e-Face senza modifiche specifiche KNX.

### Fase C — parita' funzionale

- sensori, clima e scene non di sicurezza;
- scenari cross-bus;
- backup/restore e report compatibilita';
- gestione guidata delle entita' KNX tramite API supportate.

### Fase D — strumenti avanzati

- monitor telegrammi, analisi DPT e latenza;
- import/diff ETS assistito;
- fleet management e backup coordinato e-Manager.

## 11. Test obbligatori

- HA con KNX assente, offline, incompatibile e funzionante;
- tunnel KNX perso e ripristinato senza perdita catalogo;
- catalogo con luci, dimmer, cover, sensori, clima e scene;
- mapping persistente dopo rename entity e aggiornamento progetto;
- nessun duplicato fra sorgenti `ha` e `knx`;
- comandi non catalogati e raw send sempre respinti;
- conferma, timeout, stale e unavailable;
- e-Face con dispositivi HDL, Ksenia e KNX contemporaneamente;
- restart, aggiornamento, backup e restore;
- nessuna credenziale, keyring o payload sensibile in API e log;
- compatibilita' con almeno due release Home Assistant supportate.

## 12. Criteri di accettazione

- KNX appare come bus attivo con conteggi e diagnostica propri;
- e-Control configura e organizza KNX con lo stesso modello degli altri bus;
- e-Face non contiene codice specifico Home Assistant KNX;
- dispositivi KNX arrivano tramite Smart Home v1 con `source=knx`;
- nessun doppione in e-Face o Home Assistant;
- assenza o guasto KNX non degrada HDL e Ksenia;
- nessuna dipendenza da file interni Home Assistant;
- rollback disabilita il connettore conservando catalogo e organizzazione.

## 13. Fonti tecniche

- Home Assistant KNX: https://www.home-assistant.io/integrations/knx/
- Home Assistant KNX WebSocket API implementation: https://github.com/home-assistant/core/blob/dev/homeassistant/components/knx/websocket.py
- XKNX: https://github.com/XKNX/xknx
- KNX frontend: https://github.com/XKNX/knx-frontend

