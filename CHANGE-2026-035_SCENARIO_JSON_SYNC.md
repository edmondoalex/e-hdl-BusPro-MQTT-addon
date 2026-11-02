# CHANGE-2026-035 — Sincronizzazione editor JSON scenari

## 0.1.566.7

L'editor JSON degli scenari aggiorna ora la bozza visuale non appena il testo
contiene un oggetto JSON valido. La validazione e il salvataggio applicano la
stessa bozza sincronizzata, evitando che una successiva interazione grafica
ripristini i vecchi valori `ON` dopo avere incollato o modificato `OFF`.

Per le luci in stato `OFF`, `brightness` viene normalizzato a `null`, in modo
coerente con il salvataggio backend. Nessuna route, porta, integrazione o
logica di comando dei dispositivi è stata modificata.
