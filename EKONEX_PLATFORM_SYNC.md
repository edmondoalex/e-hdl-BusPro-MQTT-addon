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
- Stato: implementazione locale completata; non committata, non pubblicata e non rilasciata.
- Candidata locale aggiornata da `0.1.441` a `0.1.442`; non committata e non pubblicata.
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

- CHANGE: `CHANGE-2026-006`, Fase 1 in revisione.
- Esito coordinatore: implementazione locale approvata.
- Staging autorizzato esclusivamente per i 20 file già validati con `git add --dry-run`.
- Commit: da autorizzare.
- Candidata locale: versione `0.1.442` coerente in `config.json` e `app/main.py`; non pubblicata.
- Push: non autorizzato.
- Release: bloccata fino al completamento dei test reali.
- Risultato: branding e-Control Hub e distinzione della navigazione multi-bus completati localmente.
- Pagine globali: Home e Scenari.
- Dispositivo trasversale: Lock / serrature.
- Ramo driver HDL BusPro: Luci, Cover ed Extra.
- Runtime, discovery, API, configurazioni operative e persistenza: invariati.
- Asset: logo catalogo 250 × 250, icona 128 × 128, logo UI 192 × 192.
- Test: JSON, Python compile, HTML, titoli navigazione, coerenza versione, configurazione protetta, hash discovery, modifica isolata di `main.py` e diff check superati.
- Rischio residuo: installazione pulita, upgrade e ripristino backup devono essere provati su Home Assistant Supervisor di staging prima della release.
- Stato Git: incremento locale a `0.1.442` eseguito; nessun commit, push, installazione o release eseguiti.
- Distribuzione: il remoto espone soltanto `main`; il repository stabile è condiviso dagli impianti, con aggiornamenti automatici dichiarati disattivati.
- Backup/rollback: prima dell'installazione creare backup Home Assistant verificato; baseline Git `0.1.441` al commit `7a07cb4`; in caso di esito negativo ripristinare il backup e pubblicare, solo previa autorizzazione, un revert della candidata.
- Prossimo passo: verificare lo staging isolato autorizzato; attendere autorizzazioni ulteriori per commit, push e installazione. Nessun ramo canary remoto deve essere creato o pubblicato in questa fase.
