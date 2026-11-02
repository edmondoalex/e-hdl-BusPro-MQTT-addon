# e-Control Hub — Manifest capabilities (bozza)

Stato: bozza locale di Fase 1. Non è un contratto centrale, non è letta dal runtime e non autorizza il caricamento dinamico dei driver.

## Campi richiesti per ogni driver

| Campo | Significato |
|---|---|
| `driver_id` | Identificativo tecnico stabile del driver |
| `version` | Versione del driver |
| `status` | Stato dichiarato: attivo, futuro, sperimentale o disabilitato |
| `capabilities` | Funzioni e classi dispositivo supportate |
| `configuration` | Schema/configurazione necessaria al driver |
| `diagnostics` | Health check, metriche e strumenti diagnostici disponibili |
| `hardware_requirements` | Gateway, interfacce o bus fisici richiesti |
| `dependencies` | Librerie e servizi necessari |
| `license` | Licenza e vincoli di distribuzione/uso |
| `api_compatibility` | Versione del contratto Core Hub richiesta/supportata |

## Regole di compatibilità

- `driver_id` non sostituisce slug, package ID o identificativi legacy dell'add-on.
- Il manifest non modifica topic MQTT, endpoint, entity ID, unique ID o dati persistenti.
- Le capabilities descrivono ciò che il driver offre; gli adattatori decidono come esporlo.
- Un driver futuro non può essere dichiarato attivo prima dell'implementazione e dei test.
- Modifiche al contratto condiviso richiedono approvazione tramite governance Ekonex Platform.

## Registro statico allegato

Il file `driver_capabilities.registry.json` prepara il registro richiesto dalla Fase 1:

- HDL BusPro è l'unico driver `active`;
- KNX, BTicino, Tuya, Modbus e DALI sono indicati esclusivamente come `planned`;
- nessun codice carica o interpreta il file in questa fase.
