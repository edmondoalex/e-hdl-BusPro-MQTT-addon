# Ekonex Platform Sync — HDL BusPro

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
