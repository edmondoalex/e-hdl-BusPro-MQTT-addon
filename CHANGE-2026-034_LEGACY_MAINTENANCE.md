# e-Control Hub 0.1.566.4 — manutenzione legacy

La `0.1.566.4` separa correttamente i due punti di ingresso senza modificare
il runtime: Web UI usa la porta utente 8124; Home Assistant Ingress usa la
porta amministrativa 8125.

Le versioni `0.1.566.1`-`0.1.566.3` hanno introdotto l'indipendenza delle
pagine e la stabilizzazione responsive.

Questa release deriva esclusivamente dalla baseline pubblica `0.1.566` e rende
le pagine operative indipendenti dalla navigazione amministrativa.

- Nessuna migrazione privata.
- Nessuna modifica a configurazione, API, dispositivi o comandi.
- Nessun codice delle release private successive.
- Menu amministrativo invariato.

Riferimento coordinato: `CHANGE-2026-034`.
