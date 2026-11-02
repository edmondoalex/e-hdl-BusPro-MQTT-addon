# Ekonex Platform Sync — HDL BusPro

## Handoff corrente - rimozione etichetta 0.1.566 / CHANGE-2026-017

- INSTALLATO: commit `828f06c` pubblicato, 0.1.566 started/nessun update; backup preventivo 0.1.565 `02c92ce1`. 218 test Python e parsing JavaScript superati. Live: 22 importazioni ritirate da bus/organizzazione/snapshot, 48 manuali identiche per hash, presentazione e policy MQTT del gruppo identiche; quattro membri nello snapshot. Browser desktop/mobile PASS in sola lettura (mqtt-composer-live-ttYKWJ), nessun comando o etichetta HA modificata. Bootstrap diretto eFace protetto da login: verifica della rimozione attestata sul catalogo Hub consegnato al consumer, non su sessione eFace autenticata. Nessun cambiamento eFace richiesto.

- 2026-10-06, autorizzazione diretta proprietario: togliere l'etichetta deve ritirare l'importazione da e-Control/eFace. Implementata sincronizzazione valida ogni circa 30 secondi anche a pagina chiusa; errore/registri malformati conservano il catalogo. Voci manuali mai acquisite dalla sincronizzazione; catalogo MQTT indipendente.
- Preferenze archiviate in ui.ha_label_archive e organizzazione su disco, escluse da catalogo attivo, organizzazione UI e snapshot; ripristino stessa identita e permessi rimettendo etichetta. Nessuna cancellazione in HA o deduplicazione tra bus. API/contratto consumer invariati, nessuna modifica eFace necessaria.
- Test store/API coprono rimozione, riavvio, ripristino, nome/icona/permessi, etichetta ereditata dal dispositivo, manuali, MQTT parallelo, backup ed errori. Baseline live acquisita senza modificare etichette o comandi. Residui preesistenti non tracciati preservati; nessun gate operativo residuo.

## Storico - composizione sequenziale 0.1.565 / CHANGE-2026-017

- Diagnosi successiva 2026-10-06, nessuna mutazione runtime: la rimozione di un'etichetta HA imposta solo label_present=false nel catalogo persistente (store.sync_ha_labeled_devices), senza disabilitare/eliminare la voce. La UI mostra quindi Etichetta rimossa; una voce del campione resta visibile anche nello snapshot eFace. Il pulsante Elimina rimuove esclusivamente il record locale ha_devices, non l'entita HA ne il catalogo MQTT. Nessuna cancellazione eseguita; eventuale sincronizzazione automatica in rimozione richiede scelta del proprietario.

- INSTALLATO: runtime `02b5ced` pubblicato e Hub 0.1.565 started/nessun aggiornamento, backup 0.1.564 `4e748ec0`. Browser live con autorizzazione esplicita: compositore aperto dalla riga esistente, quattro selezioni salvate e rilette, principale preservato, pulsante visibile desktop/mobile. Hash globale policy identico al baseline; nessuna rimozione di altre sorgenti. Screenshot locali mqtt-composer-live-DTzFsY. Test live ripetibile in tests/test_card_composer_live.cjs (sola lettura senza --save-existing).

- 2026-10-06: rifacimento autorizzato dal proprietario. MQTT solo entita/tecnica/icona e nome; compositore modale in Dispositivi e presentazione accanto a Comandi. Selezione, anteprima, Salva sempre visibile; principale automatico, modifica facoltativa. Errori nello stesso pannello e rilettura server/snapshot prima di dichiarare successo.
- Ordine persistente member_order, metadata additivo member_ids; eFace 2.21.325 visualizza l'ordine senza modificare catalogo/routine/ID. Nessuna deduplicazione automatica, comandi preservati.
- 208 test Hub, 480 eFace, 14 assert JS e percorso browser isolato desktop/mobile superati: quattro valori realmente visibili in eFace dopo rilettura disco, riapertura, errore simulato e retry, espansione a sette entita e routine indipendenti. Screenshot temporanei mqtt-composite-browser-Q7Wdcs. Nessun comando hardware.
- Il proprietario ha nel frattempo salvato le quattro entita desiderate: confermate live con principale valido, quattro presentazioni uguali e visibilita true. Conservarle nell'aggiornamento. Baseline permessi acquisita; installazione con backup in corso nell'autorizzazione esistente. Guida aggiornata, file estranei preservati.

## Storico - verifica configurazione multi-entita 2026-10-06

- Diagnosi richiesta dal proprietario, esclusivamente GET su API installate: dispositivo segnalato con 10 entita MQTT, sola occupazione abilitata e presentation vuota. Snapshot privo di presentation_group; non e quindi una scheda composta effettivamente configurata.
- La seconda scheda omonima con stato off proviene dall'entita update del catalogo generico, non da un secondo sensore di presenza. Batteria e illuminamento sono anch'essi esposti separatamente dal catalogo generico. Nessuna deduplicazione o selezione modificata.
- I test precedenti dimostravano il raggruppamento con fixture; non attestavano la composizione salvata del dispositivo reale, rimasto senza esposizioni al rilascio. Prossimo passo: composizione esplicita delle entita scelte e collaudo della configurazione reale, senza rimuovere automaticamente le voci di altre sorgenti.
- Nessuna modifica runtime, deploy, comando o migrazione. CHANGE-2026-017 e compatibilita invariate; solo questo handoff e work order aggiornati. Rischio residuo: la selezione individuale nell'organizzazione non equivale al salvataggio della composizione fisica.

## Storico - rifinitura MQTT 0.1.564 / CHANGE-2026-017

- 2026-10-05, richiesta diretta proprietario: eliminare diciture HASSIO non necessarie, logo MQTT originale orizzontale, distinguere configurazione bus da composizione scheda eFace. Commit runtime `4305ac6` pubblicato; installazione autorizzata nella continuazione del lavoro di rilascio, in verifica.
- Logo locale originale mqtt.org, titolo senza frase introduttiva, Aggiorna MQTT, Disabilitate, filtri/riepiloghi MQTT senza suffisso. Catalogo generico denominato Integrazioni esterne in menu, Info e organizzazione. Valore reale dell'etichetta d'importazione HASSIO preservato, come topic/ID/payload tecnici.
- Dispositivo MQTT apre Configurazione dispositivo senza campi di presentazione. Sezione Scheda eFace separata: selezione entità, principale solo tra selezionate, gruppo unico o separato e anteprima della composizione. Piano/stanza/pagine restano editor standard di presentazione, non parametri bus. Link diretto dalla singola riga dell'organizzazione al dispositivo fisico, senza deduzioni da nome.
- Filtro verificato: soltanto platform=mqtt, anche se altre piattaforme condividono il medesimo device_id. 207 test Python superati; browser isolato desktop/mobile, logo, sezioni, anteprima, link diretto e raggruppamento eFace superati. Nessuna nuova API o migrazione, eFace 2.21.324 resta invariato.
- Baseline pre-update: 92 dispositivi/1991 entità/zero esposte; hash delle policy `3A36B97F03698F698C510AD86AE92B31F7AEEB47F85CDE0A356CA5753D5A0079`. Broker invariato; nessuna prova su attuatori.
- Guida aggiornata: docs/MQTT_DISPOSITIVI_COMPOSTI.md. I testi tecnici/raw conservano il nome della dipendenza reale quando necessario; Aggiorna MQTT sincronizza e non aggiorna il Core.
- ESITO INSTALLAZIONE: 0.1.564 avviata, corrente/ultima coincidenti, update false; API meta conferma. Backup precedente 0.1.563 `3723fb89`. Dopo aggiornamento 92 dispositivi/1991 entità/zero esportate e hash policy identico al baseline. Nessun comando MQTT pubblicato nel collaudo live.

## Storico - MQTT multi-entità 0.1.563 / CHANGE-2026-017

- 2026-10-05: pubblicato e installato `4372af4`, Supervisor started, corrente/ultima 0.1.563, update false, `/api/meta` confermato. Backup precedente 0.1.562 `c51ca914`. Autorizzazione esplicita del proprietario: «Sì, pubblica e aggiorna entrambi».
- Dispositivo fisico con sensori/configurazione/diagnostica, controlli admin tramite HA indipendenti dall'esposizione, editor standard bus. Presentazioni e selezioni persistenti in mqtt_manager.json/backup; chiavi canoniche immutate. Metadata additivo `presentation_group`, consumer eFace 2.21.324 `4db36ef` installato con backup `ab18a198`.
- Stato MQTT dedicato inoltrato sul WebSocket con ID canonico per UI e routine. Comandi validati su capability, disponibilità, opzioni e limiti freschi; audit delle azioni admin. Numero/opzioni restano valori nativi, non percentuali luminose.
- Test: 205 Hub e 480 eFace superati; 11 assert raggruppamento, 23 controlli browser isolato desktop/mobile; smoke MQTT installato e 18 regressioni Info/Registro/menu senza eccezioni. Il test loghi attende il completamento del caricamento immagini, non solo quello dei dati Info.
- Probe live: 92 dispositivi, 1991 entità, ZERO esportate prima/dopo; realtime true. Aqara Motion Cantina ha 10 entità corrette (2 sensori/comandi, 4 configurazione incluso update, 4 diagnostiche). Nessun comando hardware, firmware, configurazione broker o esposizione automatica eseguito. Prove di comando complete con HA simulato; prova fisica lasciata al proprietario.
- Guida: `docs/MQTT_DISPOSITIVI_COMPOSTI.md`. Evidenze `%TEMP%/mqtt-composite-browser-HsweTm` e `%TEMP%/econtrol-register-browser-MN0Ogi`. Nessun archivio topic aggiunto: buffer RAM esistente, polling scoped al dispositivo aperto. File estranei non toccati.
- Prossimo passo: e-Control > MQTT > Dispositivi > Apri, scegliere entità, principale/presentazione e salvare. Nessun gate di pubblicazione residuo per questa CHANGE.

## Storico - client MQTT HASSIO 0.1.562

- 2026-10-05, CHANGE-2026-016 approvata: implementazione amministrazione CLIENT MQTT attraverso HASSIO. Il broker e il trasporto interno Hub restano invariati; nessuna gestione Mosquitto.
- Pagina MQTT nativa: rete, ricerca e paginazione, connessione/opzioni/subentry tramite flow HA reali, TLS upload scoped, diagnostica, publish/template/QoS/retain, ascolto limitato a 200 messaggi in RAM, aggiornamenti solo delle entità update MQTT realmente presenti.
- Catalogo persistente con identità HA stabili; eFace e comandi spenti per default. Presentazione, icone, piani/stanze e policy standard bus; backup Hub include policy/catalogo. Configurazione connessione e credenziali restano in HA. Doppioni SOLO avvisi, nessun blocco o esclusione automatica: questa istruzione sostituisce la precedente proposta di deduplicazione.
- Test: 191 superati, incluso catalogo da 2000 entità e invalidazione cache su modifica; Python/JavaScript e diff-check validi. Probe live HA 2026.9.3: 1 integrazione, 92 dispositivi, 1991 entità di registro incluse le disabilitate; moduli connessione/opzioni/dispositivo aperti e annullati senza applicare modifiche.
- Iterazioni 0.1.560/561 installate con backup. Il collaudo ha evidenziato rivalidazione ripetuta dell'organizzazione e rendering di migliaia di schede nascoste: cache invalidata da metadati/revisione file, catalogo metadata-only e UI lazy/paginata da 50 righe risolvono lo scaling. Lettura organizzazione misurata a 0,75 s; nessun aumento dello storico topic.
- ESITO FINALE: release 0.1.562 (`57e3590`) pubblicata e installata, Supervisor started, versione corrente/ultima coincidenti, nessun aggiornamento pendente; `/api/meta` conferma 0.1.562. Backup precedente 0.1.561 `64474674`; baseline 0.1.559 `e093ff04`, intermedio 0.1.560 `96187ef3`.
- Browser installato desktop/mobile: MQTT completo superato, inclusi moduli HA, password non restituite, filtri, paginazione, aggiornamenti, loopback su topic diagnostico univoco NON retained, pausa/clear/stop e organizzazione paginata. Zero eccezioni. Regressione Info/Registro/menu: 18 controlli superati. Porta utente MQTT admin HTTP 404. Catalogo effettivo: 92 dispositivi, 1991 entità, ZERO esportate; 23 corrispondenze con altri bus segnalate senza blocchi.
- Evidenze browser: `%TEMP%/econtrol-mqtt-browser-EnV0Xr`, `%TEMP%/econtrol-register-browser-UCRdWt`. Catalogo persistente 1.213.610 byte; organizzazione globale 1.568.490 byte. Campione finale processo: 107,1 MiB RAM, 31,75% di un core (non metrica dell'intero host). Payload ascolto non archiviati.
- Il test attende il batching subscription HA: l'ACK WebSocket registra il callback, non è un SUBACK del broker. Nessun firmware installato o attuatore fisico comandato nei test. Connessione/opzioni reali aperte e annullate; applicazione flow coperta dai test automatici. eFace usa il contratto Smart Home 1.0 invariato; nessun runtime eManager modificato. Prossimo passo utente: scegliere le entità da esporre; broker deliberatamente rimandato.

## Storico - proposta MQTT tramite Home Assistant (sola analisi)

- 2026-10-05: il proprietario chiede come esporre in e-Control l'integrazione MQTT di Home Assistant sul modello ESPHome. Ispezionati catalogo ESPHome, accesso Builder/Supervisor e catalogo HASSIO; verificate documentazione ufficiale MQTT e WebSocket HA. Proposta: HA autorevole per integrazione/discovery, UI amministrativa nativa Hub per dispositivi/configurazione/diagnostica, eventi realtime e comandi tramite HA, mantenendo il trasporto e-Control esistente distinto.
- Nessuna implementazione, installazione o modifica configurazione eseguita in questa richiesta. Da verificare API/versioni e matrice funzioni prima di promettere copertura totale. Requisiti proposti: ID/organizzazione preservati, esclusione doppioni dei driver nativi e MQTT Discovery esportato dallo stesso Hub, percorso locale Nuki invariato, nessun recorder indiscriminato topic, permessi/credenziali server-side. Evoluzione trasversale routine richiede CHANGE approvata. Runtime resta 0.1.559.

## Handoff corrente - menu integrazioni e disponibilità 0.1.558

- ESITO FINALE: 0.1.559 (`c7c9dcf`) pubblicata e installata, started, health ok, nessun aggiornamento pendente. Backup precedente 0.1.558 `1a0db97b`, backup 0.1.557 `2a4ea405`. Rifinitura finale: badge MQTT riletto ogni 10 s con pagina visibile, evitando stato fermo dopo la riconnessione. Suite 168 superata; 18 controlli Edge live desktop/mobile, loghi caricati, UI corretta, Ksenia online e dettaglio HASSIO corrispondente all'API, zero eccezioni. Nessun comando fisico. Le righe sotto descrivono la preparazione 0.1.558; nessun gate pendente.

- 2026-10-05, richiesta proprietario: aggiunte 13 voci MQTT, Zigbee, Z-Wave, Shelly, Aqara, LoRa, Yale, Tado, Sensibo, Somfy, Ecowitt, Nice, FAAC con loghi locali e provenienza in `static/hub/brands/SOURCES.md`. MQTT mostra il collegamento esistente; le altre 12 sono esplicitamente PREVISTE, nessun driver fittizio o configurazione/comando introdotto. Tuya/DALI restano previste.
- Titolo UI sopra Anteprima interfacce utente. Nome Home + Control esplicitato BTicino / Legrand · Netatmo in Info e nel gruppo bus. Pulizie Info della 0.1.557 conservate.
- Diagnosi reale sola lettura: Ksenia dichiara online, MQTT connesso, 9 disponibili ma stati stale dopo 120 s; il riepilogo li contava erroneamente offline. Ora disponibilità dichiarata e anzianità dello stato sono separate. HASSIO dichiara 63/65 disponibili: elenco nomi non disponibili consultabile nella scheda. Nessuna modifica ai comandi, allo stale consumer, ai contratti Smart Home o alla sicurezza.
- Suite 168 test superati, sintassi JS e diff-check; pubblicazione/installazione richiesta nel flusso corrente in corso. Nessun comando fisico. File estranei preservati.
- Documento del proprietario archiviato senza modifiche e con hash verificato in `../_EKONEX_PLATFORM/references/integrations/`; indice con tag per 22 ambiti, riferimento candidato e non autorizzazione implicita a implementare.
- CHANGE-2026-015: affinamento diagnostica/UI amministrativa senza modifica contratto condiviso. Prossimo passo: verifica installazione e browser.

## Handoff corrente - Registro in Sistema e Info globale mini PC

- ESITO DEFINITIVO: Hub 0.1.557 `bc32416` installato, started e nessun update pendente; backup precedente 0.1.556 `79c3fd34`. Ultima rifinitura richiesta: rimossi spiegazioni CPU/RAM/disco, swap e scheda registro da Info; Registro resta Sistema. Badge/bordi disponibilità verde online, giallo parziale, rosso indisponibili, neutro nessun esportato. Nome CPU Intel N95 verificato; risorse host reali. Undici controlli browser finali senza eccezioni, suite 164 superata. Le note intermedie sotto documentano la sequenza della stessa sessione.

- Richieste successive proprietario, CHANGE-2026-015: destinazione corretta e-Control, non eManager; Registro globale sotto Sistema; Info con risorse dell'intero mini PC e archivio; dettagli API collassati; elenco integrazioni automatico.
- Runtime pubblicati: `9a5603e` 0.1.554, `364f134` 0.1.555, affinamento `b5c288b` 0.1.556. La 0.1.555 installata con backup `a6d9892a` della 0.1.553; aggiornamento finale 0.1.556 in verifica. eFace 2.21.323 installato prima, backup `821ea8a4`.
- Proxy ristretto al registro eFace locale 8130 e login: sessione reale/ruoli eFace conservati, nessun inoltro autorità Hub/Ingress, comandi esclusi, cookie dedicato scoped. ACL API storage eFace invariata admin-only. Nessuna copia DB, nessun PIN/evento grezzo nelle metriche.
- Info: CPU globale /proc/stat, RAM host totale e disponibile, swap, filesystem /data condiviso, uptime host; processo Hub distinto in secondo piano. In VM dati della VM Home Assistant. Nessuno storico risorse salvato; poll ogni 10 secondi solo in Info visibile. Limiti archivio 30 giorni/250 MB/100.000 righe invariati, buffer Hub 24 ore/10.000.
- Integrazioni: schede da provider registrati/catalogo, include Nuki/ESPHome e sorgenti future senza modifica UI. Conteggi rilevati/esportati/visibili/disponibili; nessuna connessione dedotta. Pianificate distinte. Endpoint risorse e panoramica amministrativi.
- Test finali 164 Hub, 463 eFace, 5 label, 7 browser eFace; nove verifiche browser live Hub sulla 0.1.555, zero eccezioni e nessun overflow mobile. Live: nove sorgenti, API protetta, risorse globali disponibili (4 core, circa 15,4 GiB RAM, filesystem dati circa 219 GiB). Nessun comando fisico; file estranei preservati.
- Guida e limiti: `../e-Face X4/docs/REGISTRO_GLOBALE_EVENTI.md`. Ritirato soltanto il collegamento locale eManager mai distribuito. Nessuna migrazione dati.

## Handoff corrente - buffer Registro globale 0.1.553 installato

- Pubblicazione/installazione autorizzata dal proprietario il 2026-10-05 ed eseguita: commit `8d663ef` su origin/main, aggiornamento Supervisor con backup automatico `da99ab7d` della 0.1.552. Versione corrente/ultima 0.1.553, stato started. Feed live schema 1.0, quattro eventi osservati alla prima verifica, gap false ed errori 0; nessun traceback/errore SQLite rilevato nei log iniziali. eFace 2.21.322 installato successivamente, importazione verificata nel suo SQLite (63 accessi, 7 variazioni digitali, zero ID duplicati). Nessun comando fisico di test.

- 2026-10-05, CHANGE-2026-015: nuovo `activity_feed.py`, buffer SQLite durevole 24 ore/10.000 eventi, endpoint user read-only `/api/user/activity-feed` schema 1.0, cursor/epoch e rilevazione gap. Nessun topic/ID MQTT o configurazione modificati.
- Hook comandi Smart Home generici e bus admin: `audit_id` restituito per collegamento esatto al registro eFace 2.21.322. Nessun attore dichiarato da payload, nessun valore/PIN copiato. Cambi digitali del catalogo rilevati ogni secondo, baseline persistente senza eventi ripetuti. Supportati anche stati nativi HDL `STA` e envelope `value`; campioni analogici esclusi. Non è un packet recorder e non attribuisce la causa delle variazioni osservate.
- Suite finale `145 passed`; test su ID risposta/feed, restart, scope catalogo, formati stato e pruning; compile/diff-check OK. Nessun comando fisico. Limiti e prova in `../e-Face X4/docs/REGISTRO_GLOBALE_EVENTI.md`.
- Release pubblicata e installata con backup; file estranei/non tracciati preservati, DB separato reversibile tramite rollback add-on. Prossimo passo: collaudo manuale scelto dal proprietario. Distribuzione VPS eManager esclusa.

## Handoff precedente - directory Nuki 0.1.552 installata

- Verifica sola lettura 2026-10-05 14:49: pagina installata `index.html#nuki`, browser Edge desktop 1440x1000. `Connessioni e configurazione` esiste dopo l'intera directory, immediatamente prima di `Dispositivi (4)` (circa y=1855 prima dello scroll). Click sul summary apre correttamente Bridge locale e MQTT/Web API. Nessun errore JavaScript osservato; nessuna configurazione salvata o release eseguita. La posizione molto in basso e' poco evidente; nessuna modifica UI autorizzata in questa verifica.
- Richiesta proprietario completata il 2026-10-05: commit runtime `fd4bb95` pubblicato e installato con backup Supervisor; versione corrente/ultima `0.1.552`, stato `started`, health OK. Prima installata anche la precedente MQTT-first `0.1.551` come richiesto.
- Bus > Nuki contiene schede serratura con utenti/app, codici keypad e accessori dichiarati da Nuki, ricerca e filtri, validita e stato autorizzazione. Associazioni persistenti nel NukiStore; filtri e sezioni persistenti nel browser. Configurazione e comandi esistenti conservati.
- Autorizzazioni indicizzate per coppia serratura/ID: nessuna attribuzione da nomi o da ID locali coincidenti su serrature diverse. Record legacy senza associazione esplicita separati e conservati; PIN esclusi dalla risposta API e dalle nuove sincronizzazioni.
- Verifiche: suite Hub `141 passed`; sintassi JS, compile Python e diff-check OK. Anteprima Edge desktop/mobile: nessun errore JS, ricerca/filtri/persistenza verificati. API admin live `8125` HTTP 200 con nuova directory (4 serrature, 10 autorizzazioni utente/app, 4 codici, 2 accessori; 26 record legacy non assegnati), nessun PIN esposto. La porta utente `8124` blocca correttamente l'API amministrativa.
- CHANGE-2026-014 invariata nel contratto routine; nuova directory solo amministrativa additiva. Nessun comando fisico inviato. Co-installato e-Face `2.21.321` con Commuta nelle routine. File non tracciati preesistenti preservati; nessuna pulizia distruttiva.

## Handoff corrente - Nuki MQTT-first 0.1.551 (locale)

- Installazione autorizzata ed eseguita il 2026-10-05: commit `8e31a9c` pubblicato, aggiornamento Supervisor con backup completato, Hub `0.1.551` avviato e senza aggiornamenti pendenti; health OK. Accesso operativo gia' configurato: SSH NUC con chiave locale `%TEMP%/eface_c4_debug_20260914`, senza nuove credenziali.
- Eventi `lockActionEvent` MQTT non retained: ID UUID salvato atomicamente con l'evento; ritrasmissioni identiche ravvicinate e DUP con stesso packet ID scartati. I Nuki con evento MQTT osservato usano solo il percorso locale per le routine; la copia Web non le rilancia. Per vecchi Bridge resta il refresh Web mirato su cambio stato.
- Endpoint additivo `GET /api/user/routine-access-events` per controllo leggero e-Face. Nessun PIN, identificativo dispositivo, topic o comando modificato. La Web API resta necessaria per l'identificazione dei codici Bridge; MQTT non offre garanzia assoluta contro due pubblicazioni autonome identiche.
- Suite Hub `138 passed`, compile e diff-check superati. Nessuna misura di latenza live, nessun comando serratura, nessun push/installazione. Installato ancora `0.1.549`; candidata precedente `0.1.550` non pubblicata. Prossimo gate: revisione e autorizzazione esplicita per pubblicare/installare insieme a e-Face `2.21.320`.

## Handoff corrente - correzione Nuki 0.1.550 (locale)

- Corretto l'ID MQTT numerico di otto caratteri: resta un ID esadecimale, evitando duplicati del medesimo log Nuki Web. Il registro deduplica anche i dati storici in lettura.
- Collegato l'ID Web dell'autorizzazione al codice esistente senza dedurre persone o esporre PIN; il pulsante fisico ha un evento separato. I trigger routine restano basati su ID log Web stabili.
- Un evento MQTT Nuki non retained o un cambio di stato del Bridge mette in coda una lettura Web mirata dopo 2 secondi e un solo nuovo tentativo dopo 35 secondi; segnali ravvicinati sono accorpati per serratura. Il controllo completo ogni 60 secondi resta attivo.
- Offline: i cambi di stato locali continuano; gli eventi MQTT osservati su alcuni Nuki contengono anche ID codice, ma non entrano ancora nel feed routine per assenza di ID evento stabile. Il Bridge vecchio non fornisce l'identità del codice.
- Test: suite Hub `133 passed`, sintassi e diff-check superati. Nessun push, installazione o comando reale; versione installata sul NUC ancora `0.1.549`. Prossimo gate: revisione integrata e autorizzazione esplicita per pubblicazione/installazione.

## Handoff corrente - CHANGE-2026-014, eventi accesso routine 0.1.549

- Producer Smart Home 1.0 additivo: ogni driver puo' dichiarare `routine_events`; il feed `routine_event_log` accetta soltanto eventi stabili e selettori dichiarati. HDL, Ksenia e bus futuri non espongono eventi accesso finche' i rispettivi driver non li forniscono realmente.
- Nuki pubblica ID di autorizzazione/codice esatti e nomi come etichette, senza PIN. Per le routine usa soltanto log Web API con ID evento stabile; gli eventi MQTT sintetici e le azioni non classificate non sono convertiti in sblocchi per deduzione. Le autorizzazioni rimosse dalla lista Web API completa vengono tolte dal catalogo alla sincronizzazione riuscita.
- Compatibilita': API Smart Home 1.0 e dati legacy invariati; nessun topic MQTT, Discovery, comando o permesso cambiato.
- Test: suite completa `128 passed`; schema JSON, compilazione Python e diff-check superati. Commit `8884c1e` pubblicato su `origin/main`.
- Add-on `0.1.549` aggiornato sul NUC con backup automatico; Supervisor riporta `started`, versione corrente/ultima `0.1.549` e nessun aggiornamento pendente. `/health` risponde `ok`.
- Nessun comando serratura o prova fisica della routine eseguito. Prossimo passo: prova controllata dall'utente con un codice reale e verifica del registro routine.

## Handoff corrente - correzione registro persone e sorgenti Nuki 0.1.548

- Risoluzione persona: codice keypad nominativo (tipo 13), poi nome specifico dell'evento, poi nome autorizzazione; etichette generiche non sono più scambiate per persone.
- Origine tecnica `MQTT`, `Nuki Bridge` e `Nuki Web` ora appare nel campo origine e non nel campo persona. Le azioni fisiche senza Auth ID/Code ID restano onestamente non attribuite.
- Verifica dati NUC: l'evento `easas keypad (Keypad)` è il nome personalizzato del codice keypad, non un'identità personale. Non deve essere associato automaticamente a `EA SAS`; eventi da pulsante e codici condivisi non identificano necessariamente chi li ha usati.
- Test suite completa: 125 superati nella candidata locale; compile e diff-check superati. Release `0.1.548` pubblicata e installata; il registro colloca sorgenti MQTT/Bridge in `origine` e mantiene il nome personalizzato del codice senza inventare una persona.
- Limite residuo: per registrare la persona occorre un'autorizzazione individuale nominativa associata all'evento/codice. Oggi il contratto espone il testo evento nel campo `person`; separare in UI il nome del codice dall'identità personale richiede un aggiornamento coordinato producer/consumer e-Face.

## Handoff corrente - editor icone Nuki 0.1.546

- La pagina bus Nuki espone per ogni serratura il campo `Icona MDI`, l'anteprima e il salvataggio persistente nello stesso archivio organizzazione usato dagli altri bus.
- Il backend usa l'endpoint multi-bus gia' validato; piano, stanza, categorie e policy restano centralizzati in `Dispositivi e presentazione`.
- Verifiche: suite completa `121 passed`, sintassi JavaScript, compilazione Python e diff check superati.

## Handoff corrente - anteprima icone catalogo multi-bus 0.1.545

- Corretta l'anteprima in `Dispositivi e presentazione`: ora applica la priorita' standard `icon_override`, `icon_auto`, icona compatibile legacy e infine `mdi:devices`.
- La correzione e' unica e vale per tutti i bus e integrazioni; le icone HASSIO gia' acquisite, come `mdi:gate`, non vengono piu' sostituite visivamente dall'icona generica.
- Aggiornato il cache-buster di `organization.js` per rendere effettiva la correzione dopo l'upgrade senza pulizia manuale della cache.
- Verifiche: suite completa `120 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati.

## Handoff corrente - policy universale e-Face e Comandi 0.1.538

- `Dispositivi e presentazione` mostra sempre i flag `e-Face` e `Comandi` per ogni dispositivo di ogni bus o integrazione, inclusi HDL, Ksenia e driver futuri.
- Le due policy sono indipendenti: disattivare la pubblicazione e-Face non modifica automaticamente il permesso Comandi.
- L'organizzazione centrale persiste entrambe le policy con default compatibili (`true`) per i record esistenti; i driver che possiedono una policy nativa continuano a riceverla e la copia centrale viene mantenuta allineata.
- Il catalogo Smart Home applica la policy a HDL, Ksenia e sorgenti aggiuntive: `e-Face=false` esclude il dispositivo, `Comandi=false` lo espone in sola lettura senza inventare capability.
- Audit eseguito su tutte le sorgenti attuali e sul fallback per bus futuri. Test e-Control `114 passed`; contratto e-Face multi-bus `33 passed`; compilazione Python, sintassi JavaScript e diff check superati.
- Il cache-buster di `organization.js` è stato riallineato alla release per forzare il caricamento della UI corretta senza pulizia manuale della cache.
- Release `0.1.538` pubblicata e installata sul NUC; Supervisor riporta versione corrente/ultima `0.1.538`, stato `started` e nessun aggiornamento pendente.

## Handoff corrente - serrature Nuki complete per e-Face 0.1.531

- Le Nuki sono pubblicate a e-Face come dispositivi `lock`, con stato, disponibilita, percentuale batteria e azioni consentite dai permessi `Comandi`.
- Il registro accessi condiviso espone serratura, persona/autorizzazione, azione, origine, Auth ID, Code ID e data; gli ID cloud decimali vengono ricondotti all'identita locale della serratura.
- La sincronizzazione autorizzazioni usa l'Auth ID Nuki numerico, permettendo di risolvere i nomi reali al posto di etichette generiche; l'origine 172 e riconosciuta come MQTT.
- Il catalogo organizzazione elimina gli alias cloud duplicati, conserva assegnazioni e personalizzazioni sul record canonico e non pubblica i vecchi dispositivi Bridge indisponibili e disabilitati.
- Aggiunta la categoria `Serrature` nella pagina Dispositivi e presentazione; i lock nuovi la ricevono automaticamente.
- Consumer e-Face aggiornato separatamente per visualizzare serrature, batteria e gli ultimi eventi di accesso nella pagina Sicurezza/Serrature.
- Verifiche: suite e-Control `106 passed`, sintassi JavaScript superata; suite e-Face `421 passed`.
- Compatibilita: HDL invariato; nessuna dipendenza da Home Assistant introdotta.

## Handoff corrente - stati e batteria Nuki 0.1.530

- Ogni scheda Nuki mostra in modo esplicito stato serratura, livello/stato batteria, stato porta, connessione e trasporto locale.
- La percentuale batteria viene mostrata quando fornita da MQTT o Bridge; sui modelli senza percentuale vengono mostrati `OK`, `Critica` o `Non disponibile`.
- Corretto il falso `online` dei dispositivi Bridge senza `lastKnownState`: ora risultano non raggiungibili e i comandi restano disabilitati.
- Verifica sui dati reali: Portoncino Scala 41%, Porta Sala 80%, Porta Ufficio 28%; vecchio Portoncino privo di telemetria marcato non raggiungibile.
- Test: `104 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati. HDL invariato; nessun comando serratura inviato.
- Pubblicata e installata `0.1.530`; runtime verificato con batterie 41%, 80% e 28%, UI aggiornata e vecchio Portoncino correttamente non raggiungibile dopo sync Bridge.

## Handoff corrente - correzione pairing Nuki Bridge 0.1.529

- Corretta la sequenza guidata: `Associa Bridge` apre la finestra Nuki e indica di premere subito dopo il pulsante fisico entro 30 secondi.
- Timeout `/auth` portato a 35 secondi; gli errori Bridge 403, 404 e 503 ora producono istruzioni specifiche invece di `Not Found`.
- Test: `104 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati. Nessun comando serratura inviato.
- Pubblicata e installata `0.1.529`; runtime HTTP verificato, cache UI corretta e discovery reale confermata su `192.168.3.22:8080`.

## Handoff corrente - Nuki Bridge locale 0.1.528

- La pagina Nuki configura autonomamente anche installazioni nuove: rilevamento Bridge, host/porta manuali, pairing tramite pulsante fisico, token locale protetto e importazione serrature.
- Stati e comandi del Bridge funzionano in LAN senza Web API e senza configurazioni Home Assistant; MQTT locale resta disponibile in parallelo per le serrature compatibili e la Web API rimane opzionale per metadati e registro accessi.
- Il Bridge viene interrogato periodicamente e la pagina Nuki si aggiorna ogni 5 secondi senza refresh manuale, sospendendo il ridisegno mentre l'utente compila un campo.
- Compatibilita': pannello e identificativi HDL invariati; ID Nuki normalizzati e policy e-Face/Comandi persistenti conservate.
- Verifiche locali: `104 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati; discovery reale ha rilevato il Bridge `192.168.3.22:8080`.
- Pubblicazione e installazione completate: commit `28607b6` su `origin/main`; runtime/Supervisor `0.1.528`, stato `started`, nessun aggiornamento pendente, route Nuki e discovery Bridge HTTP 200, log di avvio regolari.
- Prossimo passo utente: dalla pagina Nuki premere il pulsante fisico del Bridge, quindi `Rileva Bridge` e `Associa Bridge`; il collaudo non ha inviato comandi alle serrature.

## Handoff corrente - nomi visibili nei pannelli bus 0.1.517

- Nei pannelli di tutti i bus il nome personalizzato e' ora visibile anche a sezione `Modifica` chiusa; quando differente, sotto compare `Nome originale: ...`.
- Tendine Categoria multi-bus e doppio nome in `Dispositivi e presentazione` restano inclusi.
- Test: `96 passed`, sintassi JavaScript e `git diff --check` superati. Commit `ebb0886` pubblicato; sorgente `0.1.517` copiata e verificata sul NUC.

---

## Handoff corrente - categorie guidate e doppio nome 0.1.516

- `Categoria` e' ora una tendina in tutti i pannelli bus e integrazioni, inclusi i form tecnici HDL gia' esistenti; `Automatica` conserva la classificazione rilevata e gli eventuali valori storici restano selezionabili.
- In `Dispositivi e presentazione` il nome personalizzato e' mostrato come titolo e, quando differente, il nome originale compare subito sotto. Il filtro ricerca trova entrambi e anche l'ID tecnico.
- Compatibilita': HDL non modificato; identificativi e valori persistiti invariati.
- Test: `96 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati.
- Release `0.1.516`, commit runtime `bdecb32` e completamento multi-bus `4eb46c7` pubblicati su `origin/main`. Sorgente add-on sul NUC sincronizzata e verificata byte per byte; ricostruzione runtime ancora da eseguire tramite canale amministrativo autenticato.

---

## Handoff corrente - nome personalizzato ESPHome 0.1.515

- Il nome impostato con `Modifica` nel pannello ESPHome e' ora il nome principale anche in `Dispositivi e presentazione`, nell'ordinamento e nel filtro di ricerca.
- La ricerca conserva anche nome originale e ID tecnico, quindi un dispositivo resta rintracciabile dopo la rinomina.
- Dopo `Salva modifica` la vista organizzazione viene ricaricata nello stesso processo UI senza refresh manuale.
- Compatibilita': identificativi tecnici e HDL invariati; cambia soltanto la presentazione degli override gia' persistiti.
- Test: `95 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati.
- Release `0.1.515`, commit runtime `93506fe` pubblicato su `origin/main`. Installazione NUC pendente per indisponibilita' del canale amministrativo autenticato nella sessione corrente.

---

## Handoff corrente - ESPHome Device Builder 0.1.514

- Integrato `ESPHome Device Builder` in e-Control con logo originale, pagina dedicata e badge menu per aggiornamenti del Builder e dei dispositivi.
- e-Control usa direttamente l'archivio autorevole `/config/esphome`: elenco nodi, editor YAML con controllo concorrenza, validazione, compilazione, installazione OTA, log e coda lavori non creano copie divergenti.
- L'aggiornamento del Builder installato e' gestibile dalla stessa pagina; nelle superfici visibili non compaiono i nomi della piattaforma o del supervisore sottostante.
- Le entita' ESPHome sono sincronizzate nel catalogo multi-bus con `source=esphome`, stato, capability, comandi, organizzazione, policy indipendenti e-Face/Comandi e backup/ripristino persistente.
- Collaudo reale NUC: release `0.1.514` avviata, Builder `2026.9.1` attivo, 2 nodi online, 34 entita' organizzabili, 2 aggiornamenti dispositivo rilevati; lettura YAML e coda lavori verificate senza modificare configurazioni ne' inviare OTA/comandi.
- Test locali: `94 passed`; compilazione Python, sintassi JavaScript inline/esterna e `git diff --check` superati. Commit runtime `d93f069` pubblicato su `origin/main`.
- Backup preventivo completo `89eb93f2`. Compatibilita': HDL BusPro non modificato; cataloghi, identificativi e dati esistenti conservati.

---

## Handoff corrente — configuratore Ferroli 0.1.513

- La pagina parte da una sola pompa e offre `Aggiungi pompa`; ogni unità successiva può usare lo stesso gateway principale oppure un gateway Waveshare differente.
- Sullo stesso gateway gli Slave ID devono essere distinti; su gateway differenti possono coincidere. Il backend supporta fino a 16 unità e raggruppa le connessioni per IP/porta.
- Configurazione autorevole persistita in `/data/modbus_manager.json`: nomi, Slave ID, gateway, IP, porte e abilitazione comandi vengono ricaricati nella UI dopo refresh, riavvio e aggiornamento e sono inclusi nell'export/import backup generale.
- Una nuova preparazione sostituisce atomicamente il set Ferroli gestito: pompe e gateway rimossi non restano appesi. HDL e gli altri driver non sono stati modificati.
- Profilo prudenziale invariato: vengono create automaticamente soltanto le tre funzioni verificate Zona 1, Zona 2 e ACS; l'estensione richiede la mappa registri ufficiale completa.
- Versione `0.1.513`; suite `92 passed`, compilazione Python, sintassi JavaScript inline/esterna e `git diff --check` superati.
- Pubblicazione e installazione completate: commit `53c1618` su `origin/main`; backup Supervisor `2ecfaca3`; NUC aggiornato, add-on `started`, versione runtime/Supervisor `0.1.513`, nessun aggiornamento pendente e nessun errore di avvio.
- Nessuna configurazione Ferroli fittizia applicata. Prossimo passo: estendere il profilo dalla mappa ufficiale integrale e collaudare letture prima di abilitare le scritture sul gateway fisico.

---

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

### Salvataggio immediato e stato Comfort Netatmo - 2026-10-03

- Release `0.1.508` pubblicata, installata e avviata sul NUC; commit `4772286` pubblicato su `origin/main`.
- Piano, stanza, pagine e visibilita' vengono ora applicati automaticamente a ogni modifica; il pulsante Salva resta disponibile come conferma manuale.
- Normalizzato lo stato climate Netatmo diretto: temperatura misurata e setpoint sono esposti con chiavi stabili; un dispositivo raggiungibile senza misura mostra `online` invece di `unknown`.
- Sincronizzazione live riuscita: 21 dispositivi rilevati; Veranda espone 20,2 °C, setpoint 8 °C, raggiungibile e organizzazione Comfort persistente.
- Test: `83 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati; log runtime regolari, BusPro/MQTT/WebSocket operativi.
- Nessun comando o setpoint e' stato inviato durante il collaudo.

### Policy e-Face e Comandi centralizzate - 2026-10-03

- Release `0.1.507` pubblicata, installata e avviata sul NUC; commit `3b5d70c` e `53e0b3b` pubblicati su `origin/main`.
- `Dispositivi e presentazione` gestisce ora nello stesso riquadro dispositivo piano, stanza, pagine, visibilita', pubblicazione `e-Face` e autorizzazione `Comandi`.
- I pannelli dei singoli bus non duplicano piu' le due policy: mantengono stato, controlli di collaudo e configurazione tecnica `Modifica`, secondo il modello HDL senza modificare il pannello HDL.
- Le policy sono lette e salvate nei cataloghi nativi KNX, MyHOME SCS, Home + Control/Netatmo e Modbus; `Comandi` resta indipendente dalla pubblicazione e-Face.
- Collaudo live: versione `0.1.507`, cache-buster UI corretto, 21 policy Netatmo caricate, API meta/organizzazione/policy/snapshot/Home + Control tutte HTTP 200; log di avvio regolari e BusPro/MQTT/WebSocket operativi.
- Test locali: `82 passed`; `git diff --check` superato. Nessun comando reale o setpoint Netatmo inviato durante questa verifica.
- Compatibilita': HDL, identificativi, MQTT, Discovery, persistenza e contratti Smart Home esistenti invariati.

### Pannelli bus allineati al modello HDL - 2026-10-03

- Release `0.1.505` pubblicata, installata e avviata; HDL usato esclusivamente come riferimento e non modificato.
- Gli altri bus adottano una tabella comune Nome, identificativo utile/ambiente, Stato e Controlli, con comando immediato e Modifica; Home + Control non espone MAC/ID tecnici ma Ambiente e modello.
- `e-Face` controlla esclusivamente la pubblicazione nelle pagine utente; `Comandi` abilita il test diretto dal pannello bus anche con e-Face disattivato.
- Gli stati non mostrano piu' JSON grezzo ma sintesi operative (online, temperatura/setpoint quando disponibili, riscaldamento, batteria, moduli, posizione).
- Aggiunto endpoint admin bus indipendente dal catalogo e-Face e compatibilita' automatica con record Netatmo storici che conservavano `room_id` negli attributi di stato.
- Test: `82 passed`, compilazione Python, parsing JavaScript e diff check superati. Collaudo live sicuro su termostato non esposto a e-Face: comando diretto raggiunge il validatore Netatmo e rifiuta correttamente 42 °C senza modificare l'impianto; versione live `0.1.505`, stato started, nessun errore runtime.

### Pannelli operativi multi-bus e separazione presentazione - 2026-10-03

- Release installata e collaudata: e-Control Hub `0.1.502`; commit pubblicati `1187028`, `f4ad0c8`, `3910cde`.
- `Dispositivi e presentazione` gestisce esclusivamente piano, stanza, pagine e visibilita'; nome, icona, categoria e opzioni tecniche sono stati spostati nei pannelli delle singole integrazioni.
- Pannello operativo comune applicato a Ksenia, KNX, MyHOME SCS, Home + Control/Netatmo, Modbus e Integrazioni esterne: stato, comandi capability-based, rinomina, icona, categoria e, quando compatibili, dimmer e gruppo/canale RGB.
- Home + Control usa ora il comando diretto Netatmo per il setpoint stanza; il catalogo conserva `home_id` e `room_id` e fonde temperatura/setpoint live della stanza con il modulo fisico.
- I comandi non sono mostrati finche' il dispositivo non e' abilitato e controllabile; il backend continua a rifiutare dispositivi assenti, read-only, non disponibili o capability non dichiarate.
- Compatibilita': HDL, identificativi, MQTT, Discovery, route e persistenza preesistenti conservati; e-Face continua a consumare lo stesso contratto Smart Home v1 arricchito dagli override operativi.
- Test locali: `81 passed`; compilazione Python, parsing JavaScript, JSON e `git diff --check` superati.
- Collaudo impianto reale: `0.1.502` started, nessun update pendente e nessun errore runtime; Admin, e-Face, Luci, Extra, snapshot, organizzazione, KNX, Modbus e Home + Control rispondono; catalogo operativo 180 dispositivi (`hdl=130`, `ksenia=9`, `ha=41`) e 21 dispositivi Netatmo rilevati.
- Limiti hardware: KNX e Modbus non hanno hardware di campo disponibile; i relativi flussi sono verificati con test e smoke API ma i comandi fisici richiederanno il futuro collaudo sugli impianti reali. Nessun setpoint Netatmo reale e' stato alterato durante il collaudo.

### Credenziali applicative Netatmo in e-Control - 2026-10-02

- Release `0.1.488` installata e avviata; commit `af1bdce` pubblicato.
- La pagina Home + Control accetta Client ID e Client Secret con campo password e li registra tramite `application_credentials/create` ufficiale Home Assistant.
- Il Secret non viene restituito dalla API di stato né scritto nei log; la UI espone soltanto presenza, conteggio e nome credenziale.
- Link Netatmo Developer, documentazione e istruzioni sicurezza inclusi nella stessa pagina.
- Verifica live: versione `0.1.488`, form presente, endpoint credenziali HTTP 200 e stato iniziale non configurato coerente.
- Test: `73 passed`, compilazione Python e diff check superati.

### Ripristino provisioning Home + Control / Netatmo - 2026-10-02

- Release installata: e-Control Hub `0.1.486`; commit pubblicati `4671156`, `2cb37b0`, `87b56b4`, `7e25eef`.
- Causa verificata: Home Assistant manteneva un lock OAuth Netatmo fantasma e restituiva `already_in_progress`, pur senza un config-flow Netatmo nell'elenco attivo; il `flow_id` dell'abort era già invalido.
- e-Control tenta ora il recupero autonomo dei flow attivi, supportando handler semplici e composti, senza indirizzare l'installatore alla UI Home Assistant.
- Per il lock fantasma già presente sull'impianto è stato riavviato esclusivamente Home Assistant Core; add-on e bus locali sono rimasti attivi.
- Collaudo live conclusivo: `POST /api/integrations/bticino/home_plus_control/provision/start` restituisce HTTP 200, `type=external`, `step_id=auth` e URL OAuth ufficiale Netatmo.
- Test locali: `73 passed`, compilazione Python e `git diff --check` superati.
- Prossimo passo utente: completare il login Netatmo dalla pagina e-Control, quindi sincronizzare e abilitare selettivamente i dispositivi per e-Face.

### Conteggi Info separati per integrazione - 2026-10-02

- Candidata locale: `0.1.479`; nessun push o aggiornamento impianto eseguito.
- Corretto `devices_by_bus.hdl_buspro`: prima contava l'intero ramo legacy, includendo 46 entita' Home Assistant; ora usa esclusivamente il catalogo HDL.
- Aggiunta `integration_metrics` additiva con rilevati/configurati, esportati Smart Home, visibili, sicurezza legacy ed esclusi per HDL, Ksenia, Home Assistant e KNX.
- La pagina Info espone tutti i conteggi e lo stato reale e-KNX Manager; il totale globale include Home Assistant come sorgente distinta.
- Verifica sull'impianto corrente atteso: HDL `130`, Ksenia `9`, Home Assistant `47 = 40 Smart Home + 7 Sicurezza legacy`, esclusi HA `0`.
- Test: `62 passed`; compile Python, JSON config e `git diff --check` superati.

### Ripristino entita' Home Assistant in e-Face - 2026-10-02

- Causa: dopo l'adozione del catalogo Smart Home v1, le entita' HA configurate restavano soltanto nel ramo legacy `devices`; e-Face privilegia correttamente `smart_home`, quindi luci ed extra HA non erano piu' visibili.
- Correzione installata: e-Control Hub `0.1.478`, commit `4ccee0d`.
- Aggiunto adapter `source=ha` che conserva entity ID, nome, destinazione, gruppo, icona, stato e capability; i comandi passano dall'endpoint Smart Home validato.
- Le entita' della pagina serrature restano sul percorso sicurezza legacy e-Face gia' protetto, evitando duplicati e regressioni di autorizzazione.
- Collaudo live: 47 configurazioni HA persistenti; 40 entita' non-sicurezza pubblicate nel nuovo catalogo (`lights:3`, `extra:37`), tutte 40 disponibili; le 7 serrature restano nel percorso legacy.
- Catalogo live totale: `hdl:130`, `ksenia:9`, `ha:40`. Comando non catalogato respinto HTTP 400.
- Test: `61 passed`, compilazione Python e `git diff --check` superati.

### e-KNX Manager con Home Assistant nascosto - 2026-10-02

- Architettura approvata dal proprietario: e-Control e' configuratore, catalogo e policy engine; Home Assistant KNX/XKNX resta il motore di campo nascosto e aggiornabile; e-Face consuma Smart Home v1 `source=knx`.
- Release installata e collaudata: `0.1.477`; commit pubblicati `fe5a424`, `0114b25`, `1f865ed`, `a75fc1d`, `ba94faf`.
- Aggiunto `e-KNX Manager` con pagine Panoramica, Progetto ETS, Dispositivi e Diagnostica/monitor BUS.
- Provisioning KNX eseguito da e-Control tramite config-flow ufficiale HA; nessun intervento nella UI Home Assistant richiesto.
- Import `.knxproj` tramite API file-upload ufficiale HA, lettura progetto e monitor telegrammi tramite WebSocket KNX ufficiale; nessun accesso a `.storage`, database o YAML interni.
- Catalogo persistente opt-in, ID stabili, dispositivi read-only per default, adapter Smart Home v1 e backup/restore e-Control completati.
- Verifica live: API Supervisor REST/WebSocket accessibili; KNX non configurato rilevato come `setup_required`; config-flow reale avviato al passo `connection_type`; upload invalido respinto 400; monitor non configurato fallisce isolato senza degradare HDL/Ksenia.
- Test: `58 passed`, Python compile e `git diff --check` superati.
- Limite di collaudo: sull'impianto non e' presente/configurato un gateway KNX/IP; tunnel, import reale ETS, telegrammi e comandi fisici richiedono i dati e l'hardware di campo. Nessun indirizzo e' stato inventato e nessuna configurazione fittizia e' stata salvata.
- Compatibilita': API Smart Home v1 additiva; identificativi, driver HDL/Ksenia, MQTT e Discovery invariati.

### Gerarchia completa delle pagine Admin - 2026-10-02

- Release installata: `0.1.471`; commit `4c613f7` pubblicato su `origin/main`.
- Applicata all'intera area interessata la regola concordata: una funzione con una sola pagina resta un collegamento diretto; una funzione con piu' pagine diventa un ramo e mostra sottopagine distinte.
- `Azioni Home` resta diretta e apre immediatamente il proprio contenuto.
- `Esposizione interfacce` ora espone cinque sottopagine autonome: collegamenti Home, ordine Home2, WebApp Home2, proxy/collegamenti esterni e telecamere e-Guard.
- `HDL BusPro` contiene il ramo `Dispositivi HDL`, articolato in nove pagine funzionali: luci e dimmer, cover, gruppi cover, temperatura, umidita', luminosita', qualita' aria, presenza e contatti; `Diagnostica HDL` resta diretta.
- `Manutenzione` resta diretta e apre subito gli strumenti MQTT. Conservati i deep link legacy `#scenarios`, `#devices/<sezione>` e `#exposure` tramite instradamento compatibile.
- Corretto il collegamento del marchio Hub verso `Stato e informazioni`, evitando il vecchio hash generico dei dispositivi.
- Collaudo visivo live completato su Azioni Home, Esposizione interfacce, Dispositivi HDL e Manutenzione; rami, sottopagine, stato attivo e pannelli aperti verificati.
- Test finali: `53 passed`; controlli JavaScript, compilazione Python e `git diff --check` superati.

### Gerarchia pagine e apertura diretta - 2026-10-02

- Release installata: `0.1.470`; commit `36b545b` pubblicato su `origin/main`.
- `Scenari e automazioni` è ora un ramo con due sottopagine reali: `Scenari multi-bus` e `Trigger Home Assistant`.
- Il ramo selezionato si apre automaticamente e ciascuna pagina mostra subito il relativo contenuto aperto.
- `Home Assistant`, avendo una sola pagina, resta una voce diretta; `Entità da Home Assistant` viene aperta immediatamente senza accordion chiuso.
- Conservata la compatibilità del precedente deep link `#scenarios`, indirizzato alla gestione scenari multi-bus.
- Collaudo visivo live completato sulle tre destinazioni; menu, stato attivo e contenuti verificati.
- Test: `53 passed`; JavaScript, Python compile e diff check superati.

### Audit globale dashboard e collaudo live - 2026-10-01

- Release installata: `0.1.469`; commit e `origin/main` allineati a `76f1e87`.
- Verificate tutte le route utente (`home`, `home2`, `e-face`, luci, cover, extra, scenari, serrature e Ksenia), le API snapshot/Ksenia e tutte le destinazioni Admin della nuova sidebar: risposta HTTP `200`.
- Ripristinato l'accesso diretto a pagina, catalogo e comandi Ksenia sulla porta utente; le autorizzazioni operative restano validate server-side.
- Sidebar resa univoca: HDL, Ksenia e Home Assistant attivi; KNX, BTicino, Tuya, Modbus e DALI pianificati; nessun duplicato Home Assistant o Info.
- Separata Diagnostica HDL dagli strumenti globali; backup e ripristino hanno una destinazione dedicata.
- Ksenia verificata live online, compatibile, MQTT connessa e con 9 risorse; dashboard Ksenia ripulita dal JSON grezzo con stati e comandi leggibili e ambienti visibili.
- Panoramica globale corretta: Ksenia non appare più `Non collegato`, mostra 9 dispositivi e partecipa al totale globale di 185 dispositivi.
- Verifica visiva desktop eseguita pagina per pagina sull'installazione reale; organizzazione, ambienti, scenari, info, diagnostica, manutenzione, strumenti e anteprime risultano caricate e coerenti.
- Test finali: `53 passed`; JavaScript, Python compile, HTML, `git diff --check`, route runtime e log di avvio superati. Restano soltanto warning FastAPI di deprecazione, non errori runtime.

### Correzione post-collaudo cache/menu - 2026-10-01

- Versione candidata: `0.1.466`.
- Risolta la causa della pagina vuota e del vecchio pannello ancora visibile: aggiunto cache-buster agli asset shell/organizzazione in Admin e pagine utente.
- Menu `Bus e integrazioni` piatto e completo: HDL, Ksenia, Home Assistant, KNX, BTicino, Tuya, Modbus, DALI; rimosso il contenitore `Altre integrazioni`.
- Home Assistant eliminato dalla Programmazione e mantenuto una sola volta come integrazione attiva.
- Badge attivo ripristinato su HDL e Ksenia; panoramica riordinata con Ksenia subito dopo HDL.
- Verifica Ksenia live: detected/compatible/MQTT online, 9 dispositivi, nessun errore.
- Test: `50 passed`, JavaScript e diff check superati.

### Revisione navigazione e palette Hub - 2026-10-01

- Versione candidata: `0.1.465`.
- Sidebar ricostruita per attivita' installatore: programmazione globale, driver, anteprime utente separate e sistema.
- `Scenari e automazioni` apre l'editor Admin con configurazione e trigger; la UI esecutiva e' confinata alle anteprime.
- Editor scenari reso installatore-first: controlli visuali in primo piano e JSON confinato in `Strumenti avanzati`.
- Palette unica grafite/ciano applicata alla shell e alle superfici comuni Admin/User; colori semantici conservati per stato, successo e pericolo.
- Colori base Admin allineati anche prima del caricamento della shell, eliminando il fallback grigio.
- Driver futuri raccolti nel ramo compatto `Altre integrazioni`.
- Compatibilita': nessuna modifica a driver, API, route, persistenza, MQTT, Discovery o identificativi.
- Test: suite Hub completa `50 passed`, sintassi JavaScript, compilazione Python e diff check superati.
- Push: `origin/main` allineato a `db7c2a3`.
- Backup Supervisor pre-update: `14930047` (`Pre e-Control Hub 0.1.465`).
- Installazione: aggiornamento da `0.1.462` a `0.1.465` completato; add-on `started`, nessun update pendente.
- Smoke test: porte 8124/8125 e route health/meta/home/Admin scenari rispondono `200`; gateway HDL avviato, nessun errore di startup rilevato.
- Verifica visiva live desktop superata su Admin Scenari e nuova sidebar.

### Correzione collaudo organizzazione Hub - 2026-10-01

- Versione candidata: `0.1.464`.
- Separata la pagina `Dispositivi e presentazione` da `Piani, stanze e gruppi` e da `Azioni Home`.
- Rimossi dai filtri dispositivi `Sicurezza` e `Scenari`: la sicurezza Ksenia resta esclusa dal contratto Smart Home e gli scenari usano le aree dedicate.
- Eventuali categorie legacy non vengono cancellate durante il salvataggio.
- Rimossa la dicitura errata `JSON`; il riquadro storico e' ora `Ordine ambienti legacy` e spiega il formato testuale HDL.
- Archivio autorevole invariato: `/data/organization.json`, persistente e incluso nel backup.
- Test: `49 passed`; sintassi JavaScript, compilazione Python e diff check superati.
- Gate: nessun push, installazione o deploy eseguito.

### Esito CHANGE-2026-013 - 2026-10-01

- Versione candidata: `0.1.463`.
- Commit locale: `1bf7aaf` (`Clarify Hub organization ownership 0.1.463`).
- UI organizzazione: rimossi numero posizione, Preferito e Scorciatoia; ordine delegato al drag e-Face; gruppi spiegati come insiemi logici facoltativi.
- Compatibilita': campi persistenti legacy conservati; nessuna modifica a MQTT, Discovery, identificativi o comandi bus.
- Test: `49 passed`, JavaScript valido, Python compile e diff check superati.
- Gate: nessun push, installazione o deploy eseguito.

### Esito producer CHANGE-2026-011 Smart Home per e-Face — 2026-10-01

- Stato: producer driver-neutral completato, verificato e committato localmente; hash definitivo registrato nel work order condiviso; nessun push/installazione/deploy/release.
- Versione candidata: `0.1.459`.
- Autorità: `/data/organization.json` conserva per `source:device_id` piano, stanza, gruppi multipli, categorie/pagine multiple, ordine per categoria, visibilità, preferiti, scorciatoie e icone; dati inclusi nel backup/restore esistente.
- Contratto: `/api/user/snapshot` mantiene invariato `devices` e pubblica `smart_home` schema `1.0` con organizzazione/presentazione, capability, descrittori comando e metadati per realtime, scenari e routine.
- Parità: HDL, Ksenia e source futura simulata attraversano lo stesso modello; provider catalogo e handler comando si registrano per source senza modificare la route centrale.
- Comandi: `POST /api/user/smart-home/{source}/{device_id}/command` risolve catalogo e handler esclusivamente server-side; categorie visuali e metadati client non autorizzano operazioni.
- Sicurezza: Ksenia resta limitata alle famiglie Smart Home whitelist; partizioni, zone, arm/disarm, bypass, panel, PIN, SIA e dettagli di trasporto restano esclusi.
- UI: Organizzazione globale consente gruppi e categorie multiple, ordine, visibilità, preferiti, scorciatoie e override icona anche per Ksenia e driver futuri.
- Compatibilità: endpoint/payload legacy, MQTT, Discovery, entity ID, unique ID e device identifier invariati.
- Artefatti: schema JSON e fixture v1 aggiornati; suite Hub 45/45 e producer Ksenia 14/14 superate, oltre a compile Python, JavaScript, route/versione, JSON, Discovery invariata e diff check.
- Prossimo gate: revisione coordinatore del commit locale; push/installazione/deploy vietati.

### Esito CHANGE-2026-010 organizzazione globale multi-bus — 2026-10-01

- Stato: implementazione locale completata, verificata e committata localmente; hash definitivo registrato nel work order condiviso; nessun push/installazione/deploy.
- Versione candidata: `0.1.457`.
- Persistenza: nuovo archivio separato e versionato `/data/organization.json`, scrittura atomica, backup `.bak`, recupero controllato dei file corrotti e inclusione nel backup/ripristino generale.
- Identità: chiavi canoniche `hdl:<subnet.device.channel>` e `ksenia:<device_id>`; collisioni fra bus impossibili e nessun topic o ID ricostruito per Ksenia.
- Migrazione: importazione HDL una tantum e idempotente da intestazioni piano, gruppi e dispositivi esistenti; collisioni segnalate senza sovrascrittura.
- Ciclo vita: dispositivi assenti conservati come orfani e riattivati mantenendo associazioni dopo rename, refresh, restart e offline/online.
- Icone: default MDI centralizzati per classe/tipo e override manuale rigorosamente validato.
- UI/API: pagina globale responsive per piani, stanze, gruppi e dispositivi HDL/Ksenia; API dedicate senza metodi MQTT generici.
- Compatibilità: `app/discovery.py`, MQTT, payload, entity ID, unique ID e device identifier invariati; producer Ksenia non modificato.
- Test: 25 test e-Control Hub e 14 test producer Ksenia superati; Python compile, route/versione, JavaScript, responsive statico, Discovery invariata e diff check superati.
- Rischi residui: migrazione, backup/restore e resa Ingress desktop/mobile devono essere collaudati su staging reale prima della pubblicazione.
- Prossimo gate: revisione coordinatore del commit locale; push, installazione, deploy e release vietati.

### Esito CHANGE-2026-009 consumer Ksenia Smart Home — aggiornato 2026-10-01

- Stato: riallineamento locale al producer approvato completato e verificato; commit correttivo locale autorizzato, nessun push/installazione/deploy.
- Versione candidata: `0.1.455`.
- Ruolo: consumer MQTT e UI capability-based del contratto Ksenia Smart Home `1.0` prodotto da Ksenia `5.2.106` (`3ed1112` + `67135e1`).
- Runtime: client MQTT dedicato; bootstrap esclusivamente su manifest, catalogo e command result dichiarati; availability e state topic sottoscritti soltanto se presenti nel catalogo validato.
- Comandi: pubblicazione esclusivamente sui `command_topic`/`command_topics` catalogati, envelope con `command_id` e `correlation_id`; ACK validato per schema, topic, correlazione, timestamp e `confirmation_source`; `accepted` non produce falso successo e il primo esito terminale resta immutabile.
- Sicurezza: famiglie ammesse esclusivamente `outputs`, `scenarios`, `domus`, `thermostats`; partizioni, zone, arm/disarm, bypass, account/PIN, panel/reset, SIA-IP e topic non catalogati sono rifiutati hard-fail.
- UI: pagina `/ksenia` con Panoramica, Uscite e luci, Cover e varchi, Sensori ambientali, Termostati, Scenari Smart Home e Diagnostica; ramo disponibile nella sidebar e nell’Admin.
- Home globale: snapshot espone conteggio Ksenia separato; le risorse Ksenia non vengono importate tramite Home Assistant né inserite nel relativo registry.
- Compatibilità HDL: invariati driver, discovery, topic, route e persistenza HDL; e-Control Hub resta operativo con Ksenia assente, offline o incompatibile.
- Test di riallineamento: 13 test consumer e 14 test producer `5.2.106` superati; Python compile, JSON/versione, JavaScript e `git diff --check` superati.
- ACL: supportate credenziali/client ID MQTT Ksenia dedicati; se il broker non configura ACL per-topic resta la protezione applicativa hard-fail, da verificare nello staging reale.
- Rischi residui: test con broker/ACL reali, retained reali, upgrade, backup/restore e comandi su centrale richiedono il gate di staging coordinato.
- Commit base locale: `7fe671f`; commit correttivo locale dedicato `0.1.455`, con hash definitivo registrato nel work order condiviso.
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

## Handoff corrente — BTicino 0.1.481

- Risultato: implementate e mantenute separate le integrazioni `myhome_scs` (BTicino MyHOME SCS/OpenWebNet locale) e `home_plus_control` (BTicino/Legrand Home + Control tramite Netatmo cloud).
- Architettura: e-Control gestisce configurazione, catalogazione, diagnostica, opt-in e organizzazione; Home Assistant fornisce i motori aggiornati; e-Face riceve esclusivamente i dispositivi abilitati nel catalogo Smart Home normalizzato.
- UI: ciascuna integrazione dispone di pagine singole Panoramica, Dispositivi e Diagnostica sotto il ramo BTicino e Legrand; stati uniformati ad ATTIVO/INATTIVO.
- MyHOME: installatore del componente OpenWebNet-HA/MyHOME 0.9.4 con URL e SHA-256 bloccati, limite dimensione, validazione percorsi/manifest e backup della versione precedente. Installazione e riavvio non eseguiti sull'impianto perché non è disponibile un gateway MyHOME per il collaudo.
- Home + Control: configurazione guidata tramite il config flow ufficiale Home Assistant Netatmo; nessun account collegato durante il collaudo.
- Backup: incluso lo stato persistente dei due cataloghi nel backup/ripristino e-Control.
- Compatibilità: HDL, Ksenia, catalogo Home Assistant legacy, KNX, MQTT, Discovery e identificativi esistenti conservati.
- Test: `67 passed`; Python compile, JavaScript syntax, JSON parsing e diff check superati.
- Pubblicazione: commit `487fa19`, push su `origin/main`, add-on aggiornato e avviato alla versione `0.1.481`.
- Verifica runtime: endpoint Admin MyHOME e Home + Control rispondono; entrambi risultano correttamente INATTIVI/non configurati con zero dispositivi. Conteggi snapshot separati e aggregato BTicino coerenti a zero.
- Rischio residuo: collaudo fisico e comandi reali richiedono rispettivamente gateway SCS/OpenWebNet o account Home + Control/Netatmo.
- Prossimo passo: quando sarà disponibile l'impianto, eseguire configurazione guidata, sincronizzazione, abilitazione selettiva dispositivi e prova completa e-Face/comandi.

## Handoff corrente — e-Modbus Manager 0.1.482

- Risultato: implementato e pubblicato e-Modbus Manager con configuratore e-Control per TCP, seriale RTU/RS-485, RTU-over-TCP e UDP.
- Modello: connessioni, profili versionati, registri validati, dispositivi/slave, catalogo Home Assistant e opt-in e-Face persistenti in `/data/modbus_manager.json`.
- Home Assistant nascosto: e-Control genera `/config/modbus_econtrol.yaml`, inserisce una sola volta l'include nel file principale, crea backup preventivo, rifiuta sezioni Modbus già gestite esternamente e richiama la validazione Supervisor prima del riavvio esplicito.
- UI: pagine Panoramica, Connessioni, Profili e registri, Dispositivi e Diagnostica; tutorial contestuale breve per ogni trasporto con cablaggio, parametri e dati da reperire nel manuale.
- Sicurezza: entità non esposte automaticamente; sola lettura predefinita; scritture abilitate esplicitamente; limiti, indirizzi, tipi dato, scala, offset, swap e framing validati.
- Prima capability produttiva: sensori, sensori binari e switch, sufficienti per telemetria, stati, consensi e allarmi PDC. Le entità HVAC composte richiedono i manuali reali dei costruttori per modellare setpoint, modalità e conferme correttamente.
- Backup: archivio Modbus incluso nell'export/import generale e-Control.
- Test: 73 test superati; compilazione Python, sintassi JavaScript esterna e inline, JSON e diff check superati.
- Pubblicazione: commit `8523561`, push su `origin/main`, add-on aggiornato e avviato alla versione `0.1.482`.
- Smoke test reale: API e-Modbus Manager disponibile, UI contiene tutorial RS-485/TCP, stato iniziale coerente (zero connessioni/profili/dispositivi), log senza errori.
- Non eseguito: nessuna configurazione fittizia applicata e nessun riavvio Home Assistant, per non alterare l'impianto senza una pompa di calore/gateway reale.
- Prossimo passo: acquisire marca, modello e manuale registri della prima PDC; creare il profilo ufficiale e svolgere collaudo lettura prima di abilitare comandi.

## Handoff corrente — interfaccia e-Control e reset Netatmo 0.1.490

- Regola UI applicata globalmente: il motore sottostante non viene nominato nelle schermate installatore o utente; le diciture sono state sostituite con termini e-Control, integrazioni esterne e servizi di sistema.
- Home + Control: eliminata dalla UX la scelta del motore OAuth; e-Control seleziona automaticamente le credenziali applicative `e-Control Hub`.
- Documentazione: rimossi collegamenti e riquadri esterni non necessari; mantenuta una guida Netatmo breve direttamente nell'integrazione.
- Recupero: aggiunto il comando `Azzera tentativo`, che conserva le credenziali Netatmo, elimina i flussi recuperabili e riavvia il servizio d'integrazione per liberare anche i flussi OAuth non enumerabili.
- Navigazione: la voce del catalogo generico è ora `Integrazioni esterne`, con icona neutra e senza marchi del motore sottostante.
- Test: build e-Face completata, compilazione Python superata, `73 passed`; controllo testuale delle superfici UI senza occorrenze vietate.
- Correzione 0.1.491: il reset usa il canale di controllo interno con avvio differito, evitando il `403 Forbidden` del Supervisor; la sincronizzazione mantiene un esito persistente con il conteggio rilevato.
- Correzione 0.1.494: catalogo, capability e comandi HDL usano ora un unico classificatore condiviso, eliminando la divergenza che causava HTTP 400 sui dispositivi privi del campo tecnico `type`; allineate anche versione del pacchetto e versione runtime. Resta eliminato il riavvio automatico dal reset Netatmo. Le 0.1.492/0.1.493 intermedie sono state superate prima della verifica funzionale.
- Netatmo 0.1.495: rimosso il relay OAuth con marchio esterno; introdotto collegamento diretto Netatmo→e-Control con callback locale, archivio credenziali/token protetto, stato OAuth monouso e procedura UI verticale. Suite: 76 test superati. Il catalogo e i comandi diretti restano il passo successivo dopo il collaudo OAuth reale dell'account.

## Handoff corrente — organizzazione multi-bus e Netatmo 0.1.498

- Corretto il filtro Bus in `Dispositivi e presentazione`: mostra sempre HDL BusPro, Ksenia Smart Home, e-KNX Manager, BTicino MyHOME SCS, BTicino Home + Control / Netatmo, e-Modbus Manager e HA.
- La voce HA resta esplicita perché identifica realmente il catalogo proveniente dall'integrazione Hassio; le altre UX continuano a non esporre il motore interno.
- KNX, MyHOME SCS, Home + Control/Netatmo e Modbus alimentano l'organizzazione anche con dispositivi rilevati ma non ancora abilitati in e-Face, eliminando il blocco circolare configurazione/abilitazione.
- Collaudo impianto: runtime e pacchetto installato `0.1.498`, servizio avviato, 199 dispositivi organizzabili; 21 Home + Control/Netatmo e 41 HA.
- Test: `76 passed`, diff check superato; commit `c3cdc92` pubblicato su `origin/main` e add-on aggiornato sul NUC.
- Compatibilità: nessuna modifica a identificativi, comandi, MQTT, Discovery o dati di presentazione esistenti.

## Correzione catalogo Netatmo 0.1.499

- Unita la topologia Netatmo allo stato live: nomi di modulo, stanze e casa sostituiscono i MAC grezzi nell'interfaccia.
- Classificazione corretta per tipo nativo: `NATherm1` e `NRV` climate, `NAMain`/`NAModule1` sensori, `NAPlug` gateway tecnico in sola lettura.
- Risincronizzazione reale completata: 21 dispositivi aggiornati, zero orfani; nomi e stanze Netatmo verificati via API sul NUC.
- Runtime installato e avviato in versione `0.1.499`; suite `78 passed`; commit `2d8de2f` pubblicato.

## Nome visualizzato dispositivi 0.1.500

- Aggiunto alla configurazione globale il campo persistente `Nome visualizzato`, separato dal nome originale del catalogo e dall'identificativo tecnico.
- Un valore personalizzato viene pubblicato a e-Face e sopravvive a riavvii e risincronizzazioni; lasciandolo vuoto si continua a seguire il nome originale.
- Installazione reale verificata in versione `0.1.500`; campo servito nella UI e catalogo Netatmo aggiornato; suite `79 passed`; commit `c3eb664`.

## Handoff corrente — comando Netatmo 0.1.509

- Risolto alla radice l'HTTP 400 dei comandi clima: l'organizzazione sovrascriveva il `room_id` nativo Netatmo con l'identificativo della stanza di presentazione.
- Il catalogo conserva ora separatamente `command_home_id` e `command_room_id`; piano e stanza scelti dall'utente restano esclusivamente dati di presentazione.
- Suite completa: `84 passed`; compilazione Python e `git diff --check` superati.
- Commit `7b78509` pubblicato e add-on `0.1.509` installato sul NUC.
- Collaudo reale: comando `temperature` sulla Veranda da 8,0 a 8,5 °C accettato e confermato da Netatmo (`status: ok`); lo stato di ritorno espone 22,5 °C misurati e setpoint 8,5 °C.
- Compatibilità: nessuna modifica a HDL, identificativi pubblici, assegnazioni di piano/stanza o permessi e-Face.

### Aggiornamento esterno Netatmo 0.1.510

- Aggiunto aggiornamento automatico ogni 30 secondi dello stato Netatmo diretto, seguito da sincronizzazione organizzazione e pubblicazione WebSocket verso e-Face.
- Collaudo reale: un setpoint modificato esternamente è passato in e-Control/e-Face da 8,5 a 10 °C senza usare `Rileva e sincronizza`.
- Release `0.1.510` installata e avviata; `84 passed`; commit `3cc6b5f` pubblicato. HDL non modificato.

### Integrazione dedicata Ferroli OMNIA 0.1.511

- Aggiunta in e-Control la pagina `Ferroli OMNIA` con logo, configurazione guidata del gateway Waveshare e supporto a una o due OMNIA M 3.2 con Slave ID distinti.
- Profilo iniziale prudenziale: registri PLC 40015/40016/40017 convertiti negli offset 14/15/16 e pubblicati in sola lettura; la scrittura richiede una scelta esplicita dopo il collaudo.
- Corretto il generatore Modbus comune: sezioni valide `switches` e raggruppamento unico di più dispositivi sullo stesso gateway.
- Release `0.1.511`, commit `8cf2ef0`, `87 passed`; installazione NUC avviata e verificata. Pagina e logo HTTP 200, endpoint admin presente e validazione input attiva.
- Nessuna configurazione fittizia salvata sull'impianto: IP e Slave ID saranno inseriti quando il gateway sarà installato. HDL invariato.
- Correzione visibilità `0.1.512`: la voce Ferroli era stata inserita nel menu amministrativo legacy nascosto dal layout corrente. È ora presente nella navigazione laterale effettiva con logo e cache-buster dedicato; collaudo live conferma versione 0.1.512, link servito e asset aggiornato. Suite: `87 passed`; commit `c70291c`.

## Handoff corrente — Nuki Smart Access 0.1.520

- Integrazione Nuki nativa e-Control, indipendente da Home Assistant: MQTT locale per rilevamento, stato e comandi; Web API opzionale per nomi, autorizzazioni e registro accessi.
- Smart Lock/Opener con `unlock`, `lock`, `unlatch` e Lock n Go; e-Face e Comandi sono permessi separati e partono disabilitati/in sola lettura.
- Gli eventi conservano azione, origine, Auth-ID, Code-ID e persona risolta. Configurazione, catalogo, eventi e autorizzazioni sono persistenti e inclusi nel backup; il token cloud è separato e non esportato.
- Aggiunta pagina Nuki, registro accessi, comandi di collaudo, logo e presenza in Dispositivi e presentazione; le serrature confluiscono in Sicurezza/Serrature di e-Face.
- HDL invariato; compatibilità degli identificativi esistenti conservata.
- Test locali: compilazione Python, sintassi JavaScript, diff check e suite completa `99 passed`.
- Pubblicazione: commit `c51dfae` su `origin/main`; add-on aggiornato e avviato sul NUC in versione `0.1.520`.
- Smoke test reale: API e asset HTTP 200, runtime `0.1.520`, tre dispositivi Nuki rilevati direttamente via MQTT (`3D7F376C`, `4D054BEF`, `4CA6FAF4`), tutti inizialmente non esposti e in sola lettura; log senza errori/traceback.
- Rischio residuo: prova meccanica e identificazione reale utenti/codici richiedono una Nuki fisica configurata sul broker e, per l'arricchimento, un token Web API.

## Handoff corrente — catalogo accessi HA 0.1.533

- Data: 2026-10-04.
- Le entità della vecchia pagina `locks` sono ora importate nel catalogo Smart Home multi-bus mantenendo il tipo nativo: lock, switch e cover.
- Verificati dal runtime installato quattro lock, un comando cancello switch e due portoni cover nella categoria `security`, con capability native di lettura e scrittura.
- Suite completa: `108 passed`; commit `339b85f` pubblicato; add-on `0.1.533` installato e avviato sul NUC.
- Compatibilità: nessuna deduplicazione per nome; gli ID canonici restano `ha:<entity_id>` e i duplicati intenzionali tra Nuki e HA restano distinti.

### Standardizzazione permessi integrazioni 0.1.535

- Anche `Integrazioni esterne` espone ora i flag persistenti `e-Face` e `Comandi` in Dispositivi e presentazione.
- Regola uniforme per tutti i cataloghi opt-in: disabilitare `e-Face` forza `Comandi` spento e non selezionabile; dispositivi senza capability operative mostrano `Comandi` disattivato.
- Verificati KNX, MyHOME SCS, Home + Control, Modbus, ESPHome, Nuki e HA esterno. HDL e Ksenia restano cataloghi nativi sempre pubblicati.
- Suite completa `111 passed`; commit `33e9d21`, `9a30abd`, release `a0166be`; versione `0.1.535` installata e verificata live.

### Eliminazione override categorie HA legacy 0.1.536

- Rimossa l'autorità di presentazione della vecchia `page` HA: categorie, piano e stanza dell'organizzazione multi-bus sono ora definitive.
- Verifica live: `Sensore Allagamento Loc. Caldaia` pubblicato come `sensors`, piano `GARAGE / MAGAZZINO`, stanza `LOCALE CALDAIA`, senza ricadere in `Extra`.
- Suite `111 passed`; commit `22f01ee`; versione `0.1.536` installata.

## Handoff corrente — HASSIO, importazione per etichetta e anteprima icone 0.1.539

- La precedente voce `Integrazioni esterne` è stata uniformata come `HASSIO`, con logo Home Assistant nella navigazione, nel filtro bus e nella pagina dedicata.
- e-Control Hub importa automaticamente le entità con etichetta Home Assistant configurabile; il valore predefinito è `HASSIO`. Sono supportate etichette applicate direttamente alle entità o ereditate dal dispositivo.
- L'importazione è persistente e deduplicata per `entity_id`; la rimozione successiva dell'etichetta non cancella configurazioni e assegnazioni, ma mostra `Etichetta rimossa`.
- Le entità importate usano lo stesso modello delle altre HASSIO: modifica tecnica, organizzazione, pagine, e-Face e Comandi. La modifica non altera più involontariamente i permessi persistenti.
- La pagina si sincronizza automaticamente ogni 15 secondi e offre configurazione dell'etichetta e pulsante `Sincronizza ora`; le scritture persistenti avvengono solo in presenza di cambiamenti.
- Aggiunta anteprima MDI globale accanto a tutti i campi icona dei pannelli bus, compresi quelli generati dinamicamente; `Dispositivi e presentazione` mostra l'icona effettiva per ogni dispositivo di tutti i bus.
- Verifica locale: suite completa `118 passed`, compilazione Python, sintassi JavaScript e `git diff --check` superati.
- Pubblicazione e collaudo: commit funzionale `e8bb279` su `origin/main`; add-on `0.1.539` installato e avviato sul NUC, nessun aggiornamento pendente. API admin HASSIO operativa con configurazione persistente `enabled=true`, etichetta `HASSIO`; al collaudo non erano ancora presenti entità etichettate (`found=0`). Asset logo e anteprima icone HTTP 200; log di avvio senza errori applicativi.
- Correzione 0.1.540: il selettore DOM dell'anteprima puntava al contenitore grafico e ne eliminava l'immagine inserendo il testo. Separati correttamente riquadro e didascalia; aggiunto cache-buster dedicato.
- Correzione 0.1.541: rimossa la seconda lista HASSIO duplicata; stato, comandi, configurazione e anteprima icona sono riuniti nella lista principale. Le icone native dei cataloghi vengono ora propagate come `icon_auto` nell'organizzazione, lasciando priorità agli override manuali. L'anteprima intercetta anche i valori assegnati programmaticamente agli editor.
- Correzione 0.1.542: gli editor vengono aperti direttamente sotto il dispositivo selezionato su tutti i bus. HASSIO sposta sotto la riga il proprio editor e sospende il ridisegno automatico durante la modifica; HDL applica lo stesso comportamento a luci, cover, temperatura, umidità, luminosità, aria, presenza e contatti. Salva/Annulla ripristinano sempre correttamente il modulo.
- Correzione 0.1.543: `/api/eface/snapshot` include il catalogo Smart Home standardizzato, come `/api/user/snapshot`. Le entità HASSIO abilitate per e-Face (compresi i sensori batteria) arrivano così a e-Face con stanza, categorie, icona e stato configurati in Dispositivi e presentazione; il catalogo legacy rimane temporaneamente additivo per compatibilità.
- Correzione 0.1.544: il cloud Nuki sincronizza automaticamente autorizzazioni e registro ogni 60 secondi. Negli eventi keypad il `codeId` risolve il nome del singolo codice (es. Claudia) con priorità sull'autorizzazione generica “Nuki Keypad”; anche i log cloud conservano ora `codeId`, tipo e codice autorizzazione.
