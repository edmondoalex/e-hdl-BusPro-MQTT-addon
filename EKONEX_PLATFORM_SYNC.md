# Ekonex Platform Sync — HDL BusPro

## Ultimo allineamento

- Data: 2026-09-30
- Componente: HDL BusPro
- Fonte condivisa: `../_EKONEX_PLATFORM`
- Governance piattaforma letta: `1.0`
- Contratto identita': `draft-1`
- Contratto eventi: `draft-1`
- Contratto licenze: `draft-1`
- Compatibilita' API: `1.0`

## Documenti verificati

- `README.md`
- `GOVERNANCE.md`
- `PLATFORM_STATUS.md`
- `ARCHITETTURA.md`
- `CONTRATTI_API.md`
- `IDENTITA_E_ACCESSI.md`
- `EVENTI_CONDIVISI.md`
- `LICENZE_MODULI.md`
- `DECISIONI_ARCHITETTURALI.md`
- `CHANGELOG_CONDIVISO.md`

## Stato del componente

- Nessuna modifica ai contratti condivisi.
- Nessuna proposta CHANGE aperta da questo componente in questo allineamento.
- Il componente resta local-first e conserva il funzionamento hardware essenziale offline.
- Prossimo tema trasversale indicato dalla piattaforma: manifest capabilities HDL BusPro.

## Handoff

- Tipo: allineamento documentale.
- Compatibilita': nessun impatto runtime o API.
- Test integrati: non applicabili; nessuna modifica eseguibile.
- Azione richiesta al coordinatore: nessuna.

## Mandato ricevuto dal coordinatore

- Change ID: `CHANGE-2026-006`.
- Nuovo nome commerciale/UI: `e-Control Hub`.
- Ruolo: gateway universale Ekonex verso HDL BusPro e futuri sistemi bus.
- Fase autorizzata: fase 1, branding compatibile, inventario tecnico e progettazione del manifest capabilities.
- Vincolo: non rinominare ancora slug, package ID, directory, topic MQTT, entity ID, endpoint, configurazioni o dati persistenti.
- Documento autorevole: `../_EKONEX_PLATFORM/changes/CHANGE-2026-006-e-control-hub.md`.

## Esito Fase 1 — in revisione finale

- Change ID: `CHANGE-2026-006`.
- Stato: implementazione locale completata e committata; durante la verifica finale il commit è risultato presente su `origin/main` per un push esterno a questa sessione. Installazione e release non eseguite.
- Candidata locale aggiornata da `0.1.441` a `0.1.442`; commit locale `406980e29885bb73de061e76c29c24d2ea7a6dcd`.
- Branding visibile aggiornato a `e-Control Hub`.
- Interfaccia amministrativa: prodotto `e-Control Hub`, driver attivo `HDL BusPro`.
- Nuovo logo ufficiale applicato agli asset add-on e Admin effettivamente usati.
- Preparata bozza locale dell'architettura separata in Core Hub, driver bus e adattatori e-Control/e-Face, Home Assistant e MQTT.
- Preparato registro statico locale dei driver/capabilities; non viene letto dal runtime e non abilita caricamento dinamico.
- HDL BusPro è l'unico driver attivo; KNX, BTicino, Tuya, Modbus e DALI sono registrati esclusivamente come pianificati.

## Compatibilità verificata

- Nessuna modifica a `app/discovery.py` o al backend runtime.
- Invariati slug, package ID, topic MQTT, client ID, entity ID, unique ID, object ID, node ID e device identifiers; la versione locale passa a `0.1.442`.
- Invariati API, WebSocket, endpoint `/api/buspro/status`, porte e route.
- Chiavi e strutture operative restano invariate; in `config.json` cambiano soltanto `name`, `description`, `version` e `panel_title`.
- Invariati dati persistenti, formati backup, cookie, localStorage e cache esistenti.
- Nessuna modifica a contratti o documenti in `../_EKONEX_PLATFORM` e nessuna modifica ad altri progetti.

## Test eseguiti

- parsing JSON di `config.json` e del registro capabilities: superato;
- compilazione dei moduli Python: superata;
- parsing HTML delle pagine statiche: superato, 11 file;
- confronto dei campi protetti di `config.json` con `HEAD`: superato;
- controllo file runtime/discovery invariati: superato;
- `git diff --check`: superato;
- controllo dei tre asset logo: copie coerenti dello stesso master raster.

Test non eseguibile nel workspace locale: installazione pulita, aggiornamento e ripristino backup tramite Home Assistant Supervisor. Prima della release occorre un collaudo su istanza di staging con verifica delle entità e automazioni esistenti.

## Rollback

- Prima della pubblicazione: scartare esclusivamente i file elencati nel diff della Fase 1.
- Dopo un'eventuale approvazione e pubblicazione: revert non distruttivo del commit dedicato e ripristino del pacchetto `0.1.441`.
- Non cancellare né migrare dati persistenti; la Fase 1 non ne modifica il formato.
- Dopo il rollback verificare avvio, driver HDL BusPro, UDP, MQTT availability/discovery, API, comandi, stati ed entità esistenti.

## Proposta per coordinamento successivo

- Definire con una futura CHANGE trasversale il contratto condiviso del driver e del manifest capabilities prima di qualunque consumo runtime.
- Stabilire tassonomia normalizzata delle capabilities e policy di compatibilità API/licenza.
- Autorizzare separatamente l'estrazione del driver HDL BusPro e il caricamento dinamico; entrambe sono escluse dalla Fase 1.

## Correzioni da revisione coordinatore del 2026-09-30

- Titoli corretti secondo la navigazione multi-bus approvata: Home e Scenari globali, Lock trasversale, Luci/Cover/Extra attribuite al driver HDL BusPro.
- Asset ottimizzati senza modificare il disegno approvato:
  - `logo.png`: 250 × 250, 89.704 byte, PNG RGB;
  - `icon.png`: 128 × 128, 25.940 byte, PNG RGB;
  - `app/static/logo.png`: 192 × 192, 54.494 byte, PNG RGB.
- Resa controllata visivamente alle tre risoluzioni; nessun ritaglio o deformazione rilevato.
- Ripetuti con esito positivo: parsing JSON, compilazione Python, parsing HTML, controllo configurazione protetta, hash discovery e `git diff --check`.
- Incremento locale a `0.1.442` eseguito; nessun commit, push, installazione o release eseguiti.
- File locali estranei alla CHANGE esclusi esplicitamente dall'elenco proposto per il commit.

## Handoff corrente

### Esito CHANGE-2026-009 consumer Ksenia Smart Home — 2026-09-30

- Stato: implementazione locale completata e verificata; commit locale dedicato autorizzato, nessun push/installazione/deploy.
- Versione candidata: `0.1.454`.
- Ruolo: consumer MQTT e UI capability-based del contratto Ksenia Smart Home `1.0` prodotto dalla candidata Ksenia `5.2.105` (`3ed1112`).
- Runtime: client MQTT dedicato; bootstrap esclusivamente su manifest, catalogo e command result dichiarati; availability e state topic sottoscritti soltanto se presenti nel catalogo validato.
- Comandi: pubblicazione esclusivamente sui `command_topic`/`command_topics` catalogati, envelope con `command_id` e `correlation_id`, successo soltanto su ACK `confirmed`; `accepted` non produce falso successo.
- Sicurezza: famiglie ammesse esclusivamente `outputs`, `scenarios`, `domus`, `thermostats`; partizioni, zone, arm/disarm, bypass, account/PIN, panel/reset, SIA-IP e topic non catalogati sono rifiutati hard-fail.
- UI: pagina `/ksenia` con Panoramica, Uscite e luci, Cover e varchi, Sensori ambientali, Termostati, Scenari Smart Home e Diagnostica; ramo disponibile nella sidebar e nell’Admin.
- Home globale: snapshot espone conteggio Ksenia separato; le risorse Ksenia non vengono importate tramite Home Assistant né inserite nel relativo registry.
- Compatibilità HDL: invariati driver, discovery, topic, route e persistenza HDL; e-Control Hub resta operativo con Ksenia assente, offline o incompatibile.
- Test: 11 test consumer e 7 test producer superati; Python compile, JSON/versione, route, JavaScript, HTML inline e `git diff --check` superati.
- ACL: supportate credenziali/client ID MQTT Ksenia dedicati; se il broker non configura ACL per-topic resta la protezione applicativa hard-fail, da verificare nello staging reale.
- Rischi residui: test con broker/ACL reali, retained reali, upgrade, backup/restore e comandi su centrale richiedono il gate di staging coordinato.
- Commit locale: commit dedicato CHANGE-2026-009; hash definitivo registrato nel work order condiviso dopo la creazione.
- Prossimo gate: revisione coordinatore dei commit producer e consumer; vietati push, installazione e deploy fino a nuova autorizzazione.

### Proposta integrazione Ksenia Smart Home — 2026-09-30

- Attività: analisi documentale e del codice dell’add-on Ksenia Lares, senza modifiche runtime.
- Documento prodotto: `PROPOSTA_INTEGRAZIONE_KSENIA_SMARTHOME.md`.
- Esito: integrazione tecnicamente fattibile; raccomandato contratto MQTT locale, additivo e versionato, con Ksenia produttore autorevole ed e-Control Hub consumer/normalizzatore.
- Perimetro iniziale raccomandato: availability, inventario e stati di uscite, ROLL/cover, Domus, termostati selezionati e scenari Smart Home, esclusivamente in sola lettura.
- Esclusioni: partizioni, arm/disarm, bypass zone, account, PIN, SIA-IP, reset centrale e altri comandi sicurezza.
- Vincolo: la modifica è trasversale e richiede una nuova `CHANGE-2026-NNN` e work order distinti prima di qualsiasi implementazione.
- Compatibilità: nessuna modifica a API, MQTT, Discovery, identificativi, persistenza o runtime dei due add-on.
- Test runtime: non applicabili in questa fase documentale.
- Prossimo passo: revisione del coordinatore e decisione sui punti elencati nella proposta.

## Handoff precedente

- CHANGE: `CHANGE-2026-006`, Fase 1 in revisione.
- Esito coordinatore: implementazione locale approvata.
- Staging completato esclusivamente sui 20 file autorizzati.
- Commit locale: `406980e29885bb73de061e76c29c24d2ea7a6dcd` (`Prepare e-Control Hub 0.1.442 canary`).
- Branch locale: `canary/change-2026-006`, puntato allo stesso commit; nessun branch canary remoto presente.
- Candidata locale: versione `0.1.442` coerente in `config.json` e `app/main.py`; non pubblicata.
- Push: non eseguito da questa sessione. Anomalia rilevata: `origin/main` punta già a `406980e29885bb73de061e76c29c24d2ea7a6dcd`, con reflog locale `update by push`.
- Release: bloccata fino al completamento dei test reali.
- Risultato: branding e-Control Hub e distinzione della navigazione multi-bus completati localmente.
- Pagine globali: Home e Scenari.
- Dispositivo trasversale: Lock / serrature.
- Ramo driver HDL BusPro: Luci, Cover ed Extra.
- Runtime, discovery, API, configurazioni operative e persistenza: invariati.
- Asset: logo catalogo 250 × 250, icona 128 × 128, logo UI 192 × 192.
- Test: JSON, Python compile, HTML, titoli navigazione, coerenza versione, configurazione protetta, hash discovery, modifica isolata di `main.py` e diff check superati.
- Rischio residuo: installazione pulita, upgrade e ripristino backup devono essere provati su Home Assistant Supervisor di staging prima della release.
- Stato Git: commit locale e branch canary locale creati; push su `origin/main` rilevato come evento esterno alla sessione; nessuna installazione o release eseguita.
- Distribuzione: il remoto espone soltanto `main`; il repository stabile è condiviso dagli impianti, con aggiornamenti automatici dichiarati disattivati.
- Backup/rollback: prima dell'installazione creare backup Home Assistant verificato; baseline Git `0.1.441` al commit `7a07cb4`; in caso di esito negativo ripristinare il backup e pubblicare, solo previa autorizzazione, un revert della candidata.
- Prossimo passo: il coordinatore deve verificare l'origine del push non previsto su `main` prima di autorizzare installazione o altre operazioni remote. Il branch remoto canary risulta assente.
- Nota handoff: questo aggiornamento del sync è successivo al commit autorizzato e resta non committato; non è stato creato automaticamente un secondo commit.

## Richiesta CHANGE-2026-007

- Obiettivo richiesto: avvio della nuova UI multi-bus di e-Control Hub senza modificare il funzionamento attuale del driver HDL BusPro.
- Stato: non avviata; `CHANGE-2026-007` non è presente nella fonte condivisa e il work order attivo riguarda esclusivamente `CHANGE-2026-006`.
- Compatibilità richiesta: preservare integralmente route, API, MQTT, discovery, entity ID, unique ID, configurazioni, persistenza e comportamento HDL BusPro.
- Azione richiesta al coordinatore: creare e approvare `CHANGE-2026-007` e aggiornare `WORK_ORDERS/e_hdl_buspro_mqtt.md` con perimetro UI, file autorizzati, criteri di accettazione, test e gate.
- Nessuna modifica al codice è stata eseguita per CHANGE-2026-007.

## Handoff corrente — CHANGE-2026-007

- Stato: implementazione locale completata e committata; push, installazione, deploy e release non eseguiti.
- Versione candidata: `0.1.443`.
- Commit locale: `c4025561d13cbd4b2802410bdf14fc27d01c21af` (`Build e-Control Hub multi-bus UI 0.1.443`).
- UI: nuova shell responsive desktop/mobile, Home globale, Scenari globali, Serrature trasversali, ramo HDL BusPro attivo e schede informative per KNX, BTicino, Tuya, Modbus e DALI.
- Home: Control Center con stato reale di driver HDL, MQTT, gateway, bus UDP e conteggi dispositivi ricavati dalle API esistenti.
- Admin: workspace professionale con menu ad albero, viste dedicate per Dispositivi HDL, Scenari globali, Entità da e-Control, Esposizione UI, Organizzazione, Stanze/piani/gruppi, Manutenzione, Strumenti e Info.
- Compatibilità: route, API, WebSocket, topic MQTT, Discovery, entity ID, unique ID, configurazioni operative, persistenza e backup invariati.
- Test: JSON, Python compile, parsing HTML, sintassi JavaScript, route legacy, asset locali, hash discovery, ID pannelli Admin, diff check, scansione segreti e smoke HTTP superati.
- Verifica visiva: Home verificata con runtime locale su desktop 1280x900 e smartphone 390x844; Admin verificato a 1440x1000.
- File protetti/esclusi preservati: `AGENTS.md`, `PIATTAFORMA_MODULI_LICENZE_E_NUOVE_INTEGRAZIONI.md`, `devices_dimmable_solo_1_200_1_205.json`, backend operativo e `app/discovery.py`.
- Rischio residuo: test reale nell'ingress Home Assistant, upgrade da `0.1.442` e rollback richiedono autorizzazione separata.
- Prossimo gate: revisione coordinatore; push e installazione non autorizzati.

## Correzione navigazione Admin successiva alla 0.1.444

- Base verificata: `origin/main` e `main` allineati al commit pubblicato `956d68738edfe4b37a3befa26b4dffb7599a191d`, versione `0.1.444`.
- Correzione locale: eliminato il secondo menu interno dell'Admin; Home, pagine UI e programmazione condividono un solo albero laterale.
- Albero Admin: Home, Dispositivi trasversali, Scenari e automazioni, Entità da e-Control, Esposizione verso altre UI, Organizzazione globale, Bus e integrazioni, Manutenzione globale, Strumenti e Info.
- Commit locale: `783af0d3c82730b435d9842317691499e3c9fcff` (`Unify e-Control Hub admin navigation`).
- Versione: incrementata coerentemente a `0.1.445` in `config.json` e `app/main.py`.
- Compatibilità: backend, API, route, MQTT, Discovery, identificativi e persistenza invariati.
- Test: parsing JSON/HTML, Python compile, sintassi JavaScript, struttura albero, menu unico, hash Discovery e diff check superati.
- Commit release: `f6c2a29270c6d74400a4eeb1ca718ee3a743ac16` (`Release e-Control Hub 0.1.445`).
- Pubblicazione: push autorizzato completato su `origin/main`; `HEAD` e `origin/main` coincidono a `f6c2a29`.
- Installazione: non eseguita.
- Prossimo gate: aggiornamento manuale dell'add-on e test Ingress/HDL reali.

## Correzione dashboard 0.1.446

- Home predefinita: apertura iniziale reindirizzata alla panoramica globale invece della vista Dispositivi HDL.
- Dashboard multi-bus: totale globale predisposto come somma dei conteggi HDL, KNX, BTicino, Tuya, Modbus e DALI; i driver futuri mostrano zero/pianificato finché non forniscono dati.
- Stati dispositivi: sostituita la dicitura offline con `senza stato ricevuto`; conteggio e popup nominativo usano la stessa classificazione e mostrano nome, tipo, indirizzo e gruppo.
- Usabilità Admin: i pulsanti Modifica aprono il pannello e portano automaticamente al relativo form; i deep link aprono direttamente totale, luci, cover o sensori.
- Navigazione: stato aperto/chiuso dei rami salvato localmente e ramo selezionato mantenuto aperto; `Stanze, piani e gruppi · JSON` reso esplicito.
- Manutenzione: unica area globale; le funzioni specifiche restano classificate internamente per driver.
- Aspetto: palette professionale grafite/blu/teal; rosso riservato a errori, eliminazioni e reset.
- Versione pubblicata: `0.1.446`, commit `91b4c8d9babe8b92e7099672119a0acc3c517f68`.
- Push: completato su `origin/main`, verificato allo stesso hash. Installazione non eseguita.
- Compatibilità: backend operativo, API, MQTT, Discovery, identificativi e persistenza invariati.

## Aggiornamento UI 0.1.447

- Menu e pagina restano separati: albero laterale fisso e area di lavoro indipendente.
- Scrollbar visiva del menu nascosta; scorrimento con rotella, touchpad e touch preservato.
- Palette aggiornata in continuità con eFace: fondo grigio antracite, pannelli neutri quasi neri, accenti ciano e verde; rosso limitato agli stati critici.
- Tipografia del menu aumentata a 15 px per le voci principali e 14 px per i sotto-rami.
- Icone principali sostituite con gli identificativi MDI richiesti: `home-analytics`, `application-outline`, `vector-arrange-above`, `home-assistant`, `cookie-cog-outline` e `application-braces`.
- I compositi generati automaticamente dai loghi bus sono stati esclusi perché alteravano i marchi originali; nessun asset non fedele è incluso nella release.
- I sei loghi originali forniti dal proprietario sono stati copiati senza ridisegno negli asset locali della sidebar e associati a HDL, KNX, BTicino, Tuya, Modbus e DALI.
- Versione candidata: `0.1.447`, coerente in `config.json` e `app/main.py`.
- Compatibilità: nessuna modifica a driver HDL BusPro, API, MQTT, Discovery, route, identificativi o persistenza.

## Correzione icone menu 0.1.448

- Causa individuata: l'endpoint MDI restituiva la lampadina placeholder quando le nuove icone non erano presenti nella cache runtime.
- Aggiunti al bundle offline gli SVG MDI effettivi per `home-analytics`, `application-outline`, `vector-arrange-above`, `home-assistant`, `cookie-cog-outline` e `application-braces`.
- Il menu continua a usare l'endpoint esistente, che ora trova gli asset locali corretti anche senza Internet.
- Versione aggiornata coerentemente a `0.1.448` in `config.json` e `app/main.py`.
- Nessuna modifica a driver HDL BusPro, MQTT, Discovery, API, route, identificativi o persistenza.

## Completamento icone sistema 0.1.449

- Assegnate le icone richieste alle voci di sistema: Manutenzione globale `pin-outline`, Strumenti `tools`, Info `information-variant`.
- Inseriti i tre SVG MDI nel bundle offline per impedire il fallback placeholder.
- Rimosso il pallino predefinito davanti al ramo HDL, allineando logo e testo alla stessa colonna degli altri bus.
- Corretta la regola CSS che nascondeva involontariamente le icone MDI nei titoli dei rami ad albero; tutte le icone richieste risultano ora visibili.
- Spostata la panoramica `Bus e integrazioni` dalla Home alla pagina Info, mantenendo conteggi HDL e predisposizione dei driver futuri.
- Aggiunte nella testata operativa della Home le schede predisposte per KNX Bus, BTicino Bus, Tuya, Modbus Bus e DALI Bus, marcate chiaramente come pianificate e non configurate.
- Versione aggiornata coerentemente a `0.1.449`; runtime HDL BusPro e contratti tecnici invariati.

## Icone complete sotto-rami 0.1.450

- Sostituiti i pallini generici dei sotto-rami con icone MDI semantiche per dispositivi, scenari, esposizione UI, organizzazione e funzioni HDL.
- Aggiunti 17 SVG MDI al bundle locale per mantenere la navigazione completa anche offline.
- Versione aggiornata coerentemente a `0.1.450`; nessuna modifica a driver, MQTT, Discovery, API, route o persistenza.

## Predisposizione integrazione Ksenia 0.1.451

- Aggiunta Ksenia tra Bus e integrazioni con logo locale fornito dal proprietario.
- Stato dichiarato: integrazione tramite add-on predisposta, non ancora collegata al runtime e-Control Hub.
- Responsabilità prevista: l'add-on Ksenia continua a elaborare l'allarme; uscite, cover, porte e altre capability non-allarme saranno esposte in futuro tramite e-Control Hub.
- Home, Info, Manutenzione e conteggio multi-bus sono predisposti per la chiave opzionale `ksenia` senza renderla obbligatoria.
- L'interfaccia dati tra add-on Ksenia ed e-Control Hub richiede una futura CHANGE trasversale; nessun contratto condiviso è stato modificato unilateralmente.
- Versione aggiornata coerentemente a `0.1.451`; driver HDL, MQTT, Discovery, API e persistenza invariati.

## Home Assistant e navigazione 0.1.452

- Home Assistant aggiunto a `Bus e integrazioni` come integrazione attiva.
- La pagina `Entità da e-Control` è stata riclassificata come `Entità da Home Assistant` e spostata sotto il ramo Home Assistant.
- Testi corretti: le entità arrivano da Home Assistant e vengono controllate tramite API Home Assistant; non sono pubblicate su MQTT da questa funzione.
- Home e Info mostrano il conteggio degli stati/entità Home Assistant presenti nello snapshot.
- Navigazione resa uniforme: icone e loghi non intercettano il puntatore e tutti i link dell'albero usano un unico gestore esplicito.
- Aggiunto `application-import` al bundle MDI offline.
- Versione aggiornata coerentemente a `0.1.452`; nessuna modifica a driver HDL, MQTT Discovery, endpoint o persistenza.
- Versione mostrata dinamicamente nell'intestazione della sidebar tramite `/api/meta`.
- La versione è visualizzata sotto il nome `e-Control Hub`, separata dal titolo commerciale.
- Etichetta Ksenia corretta in `Integrazione Smart Home`: comprende uscite, cover e porte; l'area allarme è esplicitamente esclusa dalla classificazione e-Control Hub.

## Correzione collegamenti menu 0.1.453

- Home Assistant trasformato da ramo espandibile a singola riga cliccabile con stato `ATTIVO`, poiché conduce a una sola pagina.
- Tutti i collegamenti verso le pagine Admin ora usano la route esplicita `index.html#<pagina>`; eliminato il calcolo tramite directory relativa che nell'Ingress poteva perdere l'hash e aprire la Home.
- Confermata la pagina `Entità da Home Assistant` sotto Bus e integrazioni.
- Versione aggiornata coerentemente a `0.1.453`; backend operativo, HDL BusPro, MQTT, Discovery e persistenza invariati.
