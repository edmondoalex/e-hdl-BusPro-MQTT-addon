# CHANGE-2026-006 — e-Control Hub — Piano Fase 1

## Stato e perimetro

- Documento preparatorio per la revisione del coordinatore.
- Riferimento approvato: `../_EKONEX_PLATFORM/changes/CHANGE-2026-006-e-control-hub.md`.
- Prodotto commerciale futuro: **e-Control Hub**.
- Ruolo architetturale: **Ekonex Edge Bus Gateway**.
- Primo driver supportato: **HDL BusPro**.
- Questa fase comprende esclusivamente branding visibile, documentazione e bozze architetturali locali.
- Nessuna modifica applicativa, di configurazione o documentale ulteriore deve iniziare prima dell'approvazione di questo piano.
- La compatibilità con installazioni, automazioni e backup esistenti è un requisito vincolante.

## 1. Stringhe esclusivamente commerciali e visibili

Le seguenti stringhe possono essere rinominate in **e-Control Hub**, purché non siano usate come identificativi o valori persistenti:

- nome commerciale dell'add-on mostrato nel catalogo Home Assistant;
- titolo del pannello Ingress;
- titolo e intestazione dell'interfaccia amministrativa;
- titoli HTML delle pagine utente;
- testo alternativo del logo;
- intestazioni, introduzioni e descrizioni commerciali della guida amministrativa;
- titolo e presentazione commerciale del README;
- titolo e presentazione commerciale del playbook di build;
- descrizione commerciale dell'add-on;
- logo e icona visibili, usando il nuovo logo ufficiale fornito.

Esempi attuali da riclassificare come branding visibile:

- `e-hdl BusPro MQTT`;
- `e-hdl BusPro MQTT Add-on`;
- `e-Control` quando identifica il prodotto/pannello;
- `BusPro - Home`, `BusPro - Luci`, `BusPro - Cover`, `BusPro - Lock`, `BusPro - EXTRA` e `BusPro - Scenari` quando sono esclusivamente titoli pagina.

Il termine `HDL BusPro` deve restare vicino alle funzioni del driver, per evitare di presentare il supporto attuale come universale quando in questa fase il solo driver operativo è HDL BusPro.

## 2. Riferimenti tecnici reali al protocollo HDL BusPro da mantenere

Non devono essere rinominati i riferimenti che descrivono realmente protocollo, trasporto, driver o implementazione:

- `HDL BusPro` e `BusPro` quando indicano il protocollo o il driver;
- BusPro UDP e la porta UDP `6000`;
- indirizzamento BusPro tramite subnet, device e channel;
- telegrammi BusPro, sniffer, scansione e diagnostica del bus;
- libreria e simboli `pybuspro`;
- modulo `buspro_gateway.py` e relativi nomi di classi, funzioni, variabili e logger;
- opzioni `BUSPRO_OPTIONS` e `BUSPRO_LOCAL_IP`;
- tipi scenario `buspro_light` e `buspro_cover`;
- testi tecnici nelle guide che spiegano dispositivi, comandi, stati o vincoli BusPro;
- identificatori MQTT e di discovery che contengono `buspro`;
- nomi legacy necessari a importazione, ripristino e compatibilità.

## 3. Slug e package ID

Devono rimanere invariati:

- slug add-on: `e_hdl_buspro_mqtt`;
- identificativi di repository o package già pubblicati;
- package frontend: `buspro-eface`;
- qualunque package ID presente nei manifest, nelle build o nei lockfile;
- URL del repository e riferimenti di installazione esistenti.

Il campo commerciale `name` non deve essere confuso con lo slug o con un package ID.

## 4. Nomi directory e file

Non devono essere rinominati:

- directory principale dell'add-on `e_hdl_buspro_mqtt/`;
- directory `app/`, `app/static/`, `app/static/user/` e `app/eface_frontend/`;
- file tecnici esistenti, inclusi `buspro_gateway.py`, `discovery.py` e gli altri moduli Python;
- file, directory e nomi legacy referenziati da build, runtime, backup o documentazione operativa;
- nomi di file contenenti `buspro` quando costituiscono un riferimento tecnico o un percorso stabile.

È consentita soltanto la creazione dei nuovi documenti di bozza previsti dalla fase 1, senza rinominare risorse esistenti.

## 5. Topic MQTT

Tutti i topic MQTT devono rimanere byte-per-byte invariati. In particolare:

- base topic predefinito: `buspro`;
- availability topic: `<base_topic>/availability`;
- topic di stato sotto `<base_topic>/state/...`;
- topic di comando sotto `<base_topic>/cmd/...`;
- topic Home Assistant MQTT Discovery esistenti;
- componenti dei topic relativi a luci, switch, RGB, cover, gruppi, scenari e sensori;
- client ID predefinito esistente, incluso `buspro-addon`;
- node ID e object ID usati nella discovery.

Il file `e_hdl_buspro_mqtt/app/discovery.py` non deve essere modificato nella fase 1, neppure per cambiare nomi descrittivi. Questa precauzione evita ricreazioni, duplicazioni o perdita di associazioni delle entità Home Assistant.

## 6. Entity ID e unique ID

Devono rimanere invariati:

- tutti gli `entity_id` Home Assistant configurati o generati;
- tutti i `unique_id` pubblicati tramite MQTT Discovery;
- object ID, node ID e device identifiers della discovery;
- identificatori basati su subnet, device e channel;
- identificatori di gruppi RGB, cover, scenari, trigger e sensori;
- associazioni tra entità, automazioni, dashboard e registri Home Assistant.

Non sono previste migrazioni del registro entità nella fase 1.

## 7. Chiavi di configurazione

Devono rimanere invariati nomi, struttura, tipo e semantica di tutte le chiavi di configurazione, incluse:

- `gateway_port`;
- `base_topic`;
- credenziali e parametri MQTT;
- opzioni del gateway e del driver BusPro;
- `BUSPRO_OPTIONS` e `BUSPRO_LOCAL_IP`;
- impostazioni Ingress, rete, discovery, polling, interfaccia e dispositivi;
- chiavi dei file JSON e delle strutture caricate dal runtime;
- valori predefiniti che hanno effetto su connessioni, automazioni o dati persistenti.

Sono modificabili soltanto campi manifest puramente espositivi, come nome, descrizione e titolo pannello, dopo approvazione del piano.

## 8. Endpoint e porte

Devono rimanere invariati:

- endpoint `/api/buspro/status`;
- tutti gli endpoint API e WebSocket esistenti;
- percorsi relativi usati da Ingress e frontend;
- porta BusPro UDP `6000/udp`, valore predefinito `6000`;
- porte HTTP/Ingress e mapping di rete esistenti;
- route, nomi di route e parametri richiesti dai client.

Non è prevista alcuna nuova API o modifica di contratto nella fase 1.

## 9. Dati persistenti e percorsi backup

Devono rimanere invariati:

- formato e posizione dei dati persistenti dell'add-on;
- chiavi persistenti, incluse le famiglie `light:`, `cover:` e `rgb:`;
- strutture e nomi dei dati relativi a dispositivi, gruppi, scenari, sensori e UI;
- cookie, chiavi `localStorage` e nomi cache/service worker esistenti;
- nomi e percorsi legacy di backup, esportazione, importazione e sniffer;
- formato dei backup e modalità di ripristino;
- compatibilità in lettura e scrittura con dati prodotti dalla versione `0.1.441` e precedenti.

La fase 1 non introduce migrazioni dati. Il nuovo branding non deve essere scritto dentro identificatori persistenti già esistenti.

## 10. Documenti da aggiornare dopo l'approvazione

- `e_hdl_buspro_mqtt/README.md`: nome e descrizione commerciale, mantenendo le istruzioni tecniche HDL BusPro.
- `e_hdl_buspro_mqtt/ADDON_BUILD_PLAYBOOK.md`: intestazione e contesto commerciale, preservando slug, percorsi e riferimenti operativi.
- `e_hdl_buspro_mqtt/app/static/admin_guide.html`: intestazioni e presentazione del prodotto, mantenendo protocollo, esempi e procedure BusPro.
- nuovo documento locale di bozza dell'architettura **core + driver**.
- nuovo documento locale di bozza del **manifest capabilities**.
- `EKONEX_PLATFORM_SYNC.md`: solo al termine dell'implementazione, con esito, compatibilità, test, rollback e handoff; nessuna modifica ai contratti centrali.

Non sarà riscritta la documentazione storica quando il nome precedente serve a descrivere versioni, percorsi o decisioni passate.

## 11. File che si intende modificare dopo l'approvazione

Elenco previsto e limitativo, da confermare contro il diff prima del commit:

- `e_hdl_buspro_mqtt/config.json`, esclusivamente campi commerciali visibili e versione;
- `e_hdl_buspro_mqtt/app/main.py`, esclusivamente costante di versione;
- `e_hdl_buspro_mqtt/app/static/index.html`, esclusivamente branding visibile, intestazioni e testo alternativo;
- pagine in `e_hdl_buspro_mqtt/app/static/user/` che contengono titoli commerciali visibili;
- `e_hdl_buspro_mqtt/app/static/admin_guide.html`, esclusivamente branding e descrizioni commerciali;
- `e_hdl_buspro_mqtt/README.md`;
- `e_hdl_buspro_mqtt/ADDON_BUILD_PLAYBOOK.md`;
- asset logo effettivamente usati: `e_hdl_buspro_mqtt/logo.png`, `e_hdl_buspro_mqtt/icon.png` e `e_hdl_buspro_mqtt/app/static/logo.png`;
- eventuali copie pubbliche del logo solo se una verifica dimostra che sono effettivamente usate dall'interfaccia;
- due nuovi documenti locali: bozza architettura core + driver e bozza manifest capabilities;
- `EKONEX_PLATFORM_SYNC.md`, soltanto a fine lavoro;
- questo documento, solo se il coordinatore richiede correzioni al piano.

Versione prevista dopo l'approvazione: `0.1.442` a partire da `0.1.441`.

## 12. File che non devono essere modificati

- `e_hdl_buspro_mqtt/app/discovery.py`;
- `e_hdl_buspro_mqtt/app/buspro_gateway.py`;
- moduli runtime che implementano protocollo, comandi, stato, persistenza, backup, API o WebSocket, salvo nuova autorizzazione esplicita;
- manifest/package frontend e lockfile quando contengono package ID tecnici;
- directory e file della piattaforma condivisa in `../_EKONEX_PLATFORM/`;
- contratti centrali e documenti di altri componenti;
- file utente già presenti e non pertinenti, inclusi `PIATTAFORMA_MODULI_LICENZE_E_NUOVE_INTEGRAZIONI.md` e `devices_dimmable_solo_1_200_1_205.json`;
- file di dati, backup o configurazione generati da installazioni reali;
- documentazione storica non elencata nella sezione precedente;
- asset grafici non effettivamente utilizzati, fino a verifica e approvazione del loro impiego.

## 13. Piano esatto di esecuzione dopo l'approvazione

1. Acquisire un inventario/checksum pre-modifica degli identificativi protetti.
2. Applicare il nuovo logo esclusivamente agli asset visibili confermati.
3. Sostituire il branding commerciale con **e-Control Hub** nei soli campi e testi autorizzati.
4. Conservare `HDL BusPro` in ogni riferimento reale al driver o al protocollo.
5. Aggiornare la documentazione prevista senza cambiare esempi e identificativi operativi.
6. Creare la bozza locale non operativa dell'architettura core + driver HDL BusPro.
7. Creare la bozza locale non operativa del manifest capabilities, chiarendo che non è un contratto attivo.
8. Portare la versione da `0.1.441` a `0.1.442` nei soli punti previsti.
9. Eseguire i test indicati nella sezione successiva.
10. Controllare il diff per escludere rinominazioni tecniche o file estranei.
11. Aggiornare soltanto il file locale `EKONEX_PLATFORM_SYNC.md` per il coordinamento finale.
12. Preparare commit e push del solo componente, se tutti i controlli risultano positivi.
13. Restituire il blocco `HANDOFF DA INVIARE AL COORDINATORE` con esito, limiti e proposte per le fasi successive.

## 14. Test di installazione, aggiornamento e compatibilità

### Installazione pulita

- validazione sintattica di `config.json` e degli altri manifest interessati;
- verifica che slug, package ID, porte e opzioni predefinite siano invariati;
- compilazione/import dei moduli Python interessati;
- avvio locale o smoke test equivalente, quando disponibile nell'ambiente;
- verifica che pannello, pagine desktop/mobile e asset del nuovo branding siano caricabili;
- verifica che il driver si presenti correttamente come HDL BusPro.

### Aggiornamento da installazione esistente

- confronto automatico pre/post degli identificativi protetti;
- aggiornamento sintetico da configurazione compatibile con `0.1.441`;
- caricamento di dati legacy sintetici senza migrazione o perdita;
- verifica che opzioni, route, endpoint e porte rimangano compatibili;
- verifica che non vengano create nuove entità a causa del cambio commerciale;
- ove l'ambiente non consenta un aggiornamento reale tramite Supervisor, dichiarazione esplicita del limite e richiesta di collaudo su istanza di staging.

### Ripristino backup

- creazione di un dataset sintetico privo di dati cliente;
- test di caricamento/round-trip dei formati persistenti e di backup esistenti;
- verifica che nomi dei file, percorsi e chiavi legacy siano ancora riconosciuti;
- ove non sia disponibile Home Assistant Supervisor, test statico/sintetico locale e collaudo finale richiesto su staging.

### Compatibilità Home Assistant e MQTT

- conferma che `app/discovery.py` sia identico prima e dopo la modifica;
- snapshot o checksum di topic, `entity_id`, `unique_id`, object ID, node ID e device identifiers;
- verifica invariata dei topic di comando, stato e availability;
- verifica che automazioni e dashboard continuino a riferirsi agli stessi identificativi;
- controllo delle entità luci, switch, RGB master/canali, cover, scenari e sensori;
- smoke test degli endpoint, incluso `/api/buspro/status`;
- controllo che non siano cambiate le strutture JSON operative.

### Controlli finali

- ricerca completa dei nomi precedenti e classificazione di ogni occorrenza residua come tecnica, storica o da correggere;
- `git diff --check`;
- validazione JSON;
- compilazione Python;
- verifica responsive essenziale delle schermate interessate;
- verifica che non siano stati modificati file esclusi dal piano;
- verifica che i file non tracciati dell'utente siano rimasti intatti;
- revisione del diff prima di commit e push.

## 15. Procedura di rollback

1. Identificare il commit unico della fase 1 e la precedente versione stabile `0.1.441`.
2. Fermare la distribuzione della `0.1.442` se uno dei controlli di compatibilità fallisce.
3. Eseguire un revert non distruttivo del commit della fase 1; non usare reset distruttivi e non cancellare dati persistenti.
4. Ricostruire e ripubblicare gli asset e i manifest della versione precedente.
5. Ripristinare il pacchetto `0.1.441` tramite i normali strumenti Home Assistant/Supervisor.
6. Non migrare né riscrivere configurazioni o backup, perché la fase 1 non deve modificarne il formato.
7. Verificare dopo il rollback: avvio add-on, BusPro UDP, stato gateway, API, MQTT availability, discovery, comandi, stati ed entità esistenti.
8. Se il problema è limitato al branding, mantenere i dati persistenti e ripristinare soltanto file statici, manifest visibile e documentazione.
9. Registrare causa, commit, controlli eseguiti ed eventuale proposta CHANGE, senza includere segreti o dati cliente.

## 16. Criteri di approvazione del coordinatore

L'implementazione può iniziare soltanto dopo conferma che:

- la distinzione tra branding commerciale e riferimenti tecnici è corretta;
- la discovery MQTT resta completamente esclusa dalle modifiche;
- l'elenco dei file modificabili è accettato;
- le bozze architetturali locali non assumono valore di contratto condiviso;
- test e rollback sono adeguati;
- non è richiesta alcuna modifica trasversale o ai contratti centrali nella fase 1.
