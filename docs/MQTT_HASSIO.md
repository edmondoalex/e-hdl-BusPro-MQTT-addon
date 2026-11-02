# Client MQTT di Home Assistant in e-Control

Aprire **MQTT → Rete, configurazione e strumenti**. È il client MQTT di HASSIO, non un broker. La gestione di Mosquitto è esclusa; il trasporto MQTT interno di e-Control resta separato.

## Rete e presentazione

Il catalogo include tutte le entità del registro MQTT, anche quelle disabilitate in HA, contrassegnate esplicitamente. Ricerca per nome/entity ID/dispositivo/produttore/modello, filtri e pagine da 50 righe. I doppioni con altri bus sono soltanto avvisi: nessuna esclusione automatica.

Le nuove entità hanno **eFace disattivato** e **Comandi disattivati**. Attivare eFace per le sole entità desiderate; abilitare separatamente i comandi. Senza capacità operative o con eFace disattivato i comandi restano spenti. Configura permette nome, icona, piano, stanza, categorie e visibilità, come negli altri bus. I permessi sono presenti anche in Dispositivi e presentazione.

Gli ID persistenti derivano dal registro HA, non dal nome visualizzato. Una rinomina conserva le assegnazioni; un'entità rimossa viene segnalata come orfana senza cancellare le scelte.

## Configurazione applicata in HASSIO

Connessione, Opzioni MQTT e + Dispositivo HASSIO utilizzano i moduli e la validazione della versione HA installata, incluse le sezioni avanzate e i certificati TLS. Il riepilogo viene riletto dopo l'applicazione. Le password già salvate non vengono inviate al browser: campo vuoto le conserva. I parametri JSON sono un'alternativa avanzata ai campi dello stesso passo.

I dispositivi creati con subentry HA possono essere modificati riaprendo Configurazione MQTT in HASSIO. Le entità discovery del produttore mostrano topic e diagnostica: per modificarne la discovery si usa una pubblicazione esplicita, non una riscrittura automatica del dispositivo.

Una modifica alla connessione può interrompere temporaneamente i dispositivi MQTT di Home Assistant. Nessuna configurazione viene applicata all'apertura della pagina.

## Pubblicazione e ascolto

Publish supporta testo/JSON, template HA, QoS 0/1/2 e retain. Ogni pubblicazione richiede conferma; payload vuoto con retain richiede una seconda conferma perché rimuove il messaggio conservato. L'accettazione del servizio HA non prova l'esecuzione di un dispositivo.

Ascolto supporta `#` e `+`, JSON, pausa della visualizzazione, copia, pulizia e stop. Massimo quattro sessioni, 200 messaggi per sessione in RAM, payload visualizzati fino a 4096 caratteri. Le sessioni inattive scadono; uscire dalla pagina interrompe l'ascolto. Nessun archivio generalizzato dei topic o scrittura dei payload nel registro globale.

## Aggiornamenti e persistenza

Il client MQTT è parte di Home Assistant: non ha un aggiornamento indipendente. La pagina mostra la versione HA e le entità MQTT `update` effettivamente esposte dai dispositivi. L'installazione firmware richiede conferma e usa il backup soltanto se il dispositivo lo supporta. Non vengono installati o aggiornati broker/add-on da questa pagina.

Catalogo e permessi sono in `/data/mqtt_manager.json`, scritti solo quando cambiano, inclusi nel backup Hub insieme all'organizzazione. Stati correnti e ascolti restano in RAM. Connessione, credenziali e subentry richiedono il backup Home Assistant; non sono duplicati nel backup e-Control.

API amministrative: `/api/integrations/mqtt`, `/sync`, `/client-status`, `/flow`, `/updates`, `/devices/{id}/debug`, `/publish`, `/listen`. Presentazione e permessi usano le API multi-bus esistenti. La porta utente non espone le API amministrative MQTT.

## Verifiche

Suite `python -m pytest -q`; UI/live `node tests/test_mqtt_browser.cjs http://HOST:8125/`. Quest'ultimo apre e annulla i moduli HA e pubblica un solo messaggio diagnostico non retained su un topic univoco, senza comandare dispositivi, cambiare il broker o attivare esposizioni. La verifica iniziale presuppone zero entità MQTT esposte.
