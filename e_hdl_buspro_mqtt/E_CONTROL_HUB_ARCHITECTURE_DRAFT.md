# e-Control Hub — Bozza architettura Fase 1

Stato: bozza locale non operativa per `CHANGE-2026-006`. Non è un contratto condiviso e non comporta spostamenti di codice o caricamento dinamico dei driver.

## Obiettivo

e-Control Hub è una piattaforma edge multi-bus Ekonex. HDL BusPro è il primo driver supportato, non il nome né il limite architetturale del prodotto.

```text
e-Control Hub
├── Core Hub
│   ├── configurazione e persistenza compatibili
│   ├── registro driver e capabilities
│   ├── routing normalizzato di comandi, stati ed eventi
│   ├── API, WebSocket, health e diagnostica
│   └── backup e ripristino
├── Driver bus
│   └── HDL BusPro (driver attivo)
│       ├── trasporto UDP
│       ├── pybuspro e telegrammi
│       ├── mapping dispositivi/canali
│       └── comandi, stati e diagnostica bus
└── Adattatori di esposizione
    ├── e-Control / e-Face
    ├── Home Assistant API
    └── MQTT e MQTT Discovery
```

## Core Hub

- gestisce ciclo di vita, configurazione, persistenza, health, diagnostica e backup;
- espone in futuro un modello normalizzato di dispositivi, comandi, stati, eventi e capabilities;
- registra concettualmente i driver senza dipendere dal nome di uno specifico protocollo;
- mantiene gli adattatori esterni separati dalla logica dei driver.

## Driver bus

- traduce il modello normalizzato nel protocollo fisico;
- dichiara capabilities, configurazione, diagnostica, requisiti hardware, dipendenze, licenza e compatibilità API;
- conserva gli identificativi tecnici necessari alla compatibilità del protocollo;
- non determina il branding commerciale del prodotto.

## Adattatore e-Control/e-Face

- presenta dispositivi e capabilities alla UI e agli altri componenti Ekonex;
- non implementa il protocollo bus;
- seleziona le funzioni disponibili in base alle capabilities dichiarate dal driver;
- preserva gli adattatori Home Assistant e MQTT esistenti durante la transizione.

## Navigazione multi-bus prevista

```text
e-Control Hub
├── Home                         globale, tutti i bus e sorgenti
├── Scenari                      globali e cross-bus
├── Dispositivi trasversali
│   └── Lock / serrature         e-Control, Home Assistant e altre integrazioni
└── Bus e integrazioni
    ├── HDL BusPro
    │   ├── Luci
    │   ├── Cover
    │   └── Extra
    ├── KNX                      pianificato
    ├── BTicino                  pianificato
    ├── Tuya                     pianificato
    ├── Modbus                   pianificato
    └── DALI                     pianificato
```

Una funzione è collocata in base alla proprietà dei dati e alla capacità di aggregazione. Le viste globali possono mostrare dispositivi gestiti dai singoli driver senza diventare dipendenti da uno specifico protocollo.

## Driver previsti

- HDL BusPro — attivo e implementato;
- KNX — futuro;
- BTicino — futuro;
- Tuya — futuro;
- Modbus — futuro;
- DALI — futuro;
- altri protocolli — estensione futura.

## Vincoli della Fase 1

- nessuno spostamento o refactoring del codice runtime;
- nessun loader dinamico;
- nessuna modifica a topic MQTT, API, entity ID, unique ID, configurazioni o dati persistenti;
- il registro statico è descrittivo e non viene consumato dal runtime;
- ogni attivazione futura del modello core/driver richiede una fase autorizzata e, se trasversale, una proposta CHANGE.

## Direzione successiva proposta

1. definire e approvare il contratto condiviso del driver e il modello normalizzato;
2. validare la compatibilità interna senza cambiare i contratti esterni;
3. estrarre HDL BusPro dietro l'interfaccia driver;
4. introdurre un driver manager e caricamento controllato;
5. integrare nuovi driver uno alla volta con test di conformità.
