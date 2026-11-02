# Dispositivi MQTT multi-entità

Release e-Control 0.1.565 + eFace 2.21.325, CHANGE-2026-017.

## Configurazione

In e-Control aprire MQTT, Dispositivi, Apri sul dispositivo fisico. La sezione **Configurazione dispositivo** contiene sensori/comandi, configurazione e diagnostica secondo le categorie del registro Home Assistant. Non mostra i campi piano/stanza/pagine. I parametri scrivibili si applicano tramite HA anche se il dispositivo non è esposto in eFace. Gli aggiornamenti firmware mantengono una conferma separata.

In MQTT restano entità associate, stati, configurazione tecnica e scelta di icona/nome. Piano, stanza, pagine, esposizione e composizione non sono più in questa pagina.

Da **Dispositivi e presentazione**, premere **Componi scheda multipla** accanto a Comandi. Nel pannello selezionare almeno due entità, controllare l'anteprima e premere **Salva scheda multipla**, sempre visibile nel fondo fisso. Non si cambia pagina. Il nome è già compilato e il principale è automatico; la scelta manuale è solo nelle opzioni facoltative. Le frecce cambiano l'ordine dei valori. Nome, selezione, principale e ordine sono riletti dal server dopo il salvataggio; anche il catalogo destinato a eFace viene verificato. Errori mostrati accanto al pulsante, senza perdere le spunte.

Piano, stanza, pagine e permessi restano nella pagina Dispositivi e presentazione; la scheda segue l'organizzazione dell'entità principale. Le altre entità di un dispositivo non diventano pubbliche senza selezione esplicita. I comandi esistenti sono preservati, non abilitati dal compositore. Le voci degli altri bus non sono eliminate. Il filtro MQTT mostra soltanto la piattaforma MQTT; Integrazioni esterne resta un catalogo separato.

Il logo orizzontale originale proviene da [mqtt.org](https://mqtt.org/assets/img/mqtt-logo-transp.svg) ed è servito localmente. Le diciture HASSIO sono state rimosse dai testi MQTT, menu e riepiloghi. Restano invariati i dati tecnici reali: etichetta d'importazione eventualmente chiamata HASSIO, topic discovery, ID e payload diagnostici. Cambiarli automaticamente interromperebbe associazioni esistenti. La dipendenza tecnica dall'integrazione Home Assistant non viene rimossa: il client non ha un aggiornamento autonomo; «Aggiorna MQTT» sincronizza il catalogo, non aggiorna Core né il broker.

eFace mostra una scheda con i valori selezionati, ad esempio occupazione, illuminamento, batteria e temperatura. Il catalogo delle routine resta composto da entità distinte: ognuna ha trigger e condizioni propri; solo quelle scrivibili hanno azioni. Number conserva unità/limiti/passo reali, select propone le opzioni reali. I confronti numerici non accettano stati sconosciuti. I trigger di soglia scattano all'ingresso nella condizione, non a ogni aggiornamento che resta oltre soglia.

## Persistenza e compatibilità

Da Hub 0.1.566, rimuovere l'etichetta d'importazione HA ritira la corrispondente voce generica da e-Control ed eFace (controllo circa ogni 30 secondi o «Sincronizza ora»). Le entita originali HA, le voci manuali e le esposizioni MQTT separate restano intatte. Se l'etichetta e ancora sul dispositivo padre, l'importazione resta valida. Errori di connessione o registri malformati non rimuovono voci. Nome e impostazioni restano nel backup di configurazione e vengono recuperati rimettendo l'etichetta, senza registrare uno storico degli stati.

Associazioni solo dal device registry HA, mai dedotte dal nome. ID delle entità invariati; `presentation_group` è metadata additivo Smart Home 1.0, non un nuovo destinatario di comandi. Se il principale scompare, il gruppo conserva il proprio ID e mostra i membri rimasti senza reindirizzare comandi. Catalogo/presentazioni sono in mqtt_manager.json, inclusi nel backup Hub. Connessione e credenziali restano in HA. Doppioni soltanto segnalati. Broker invariato.

Il campo opzionale `presentation_group.member_ids` comunica l'ordine dei valori. Le configurazioni precedenti senza ordine restano valide. Il salvataggio fallisce senza scrivere se le entità del registro sono cambiate o l'ordine contiene membri estranei/duplicati.

Diagnosi del 06/10/2026: l'anteprima del vecchio editor mostrava anche una selezione non salvabile perché mancava il principale; l'errore di salvataggio era lontano, nel riepilogo superiore MQTT. Non era una prova di composizione persistita. Il nuovo percorso elimina il passaggio obbligatorio e verifica la rilettura. Il proprietario ha poi salvato correttamente le quattro entità nel vecchio editor: configurazione riletta live e da preservare nell'aggiornamento.

L'ascolto topic resta limitato in RAM. Non viene creato un secondo archivio di messaggi; il polling della scheda legge soltanto il dispositivo aperto. Gli eventi delle entità MQTT esposte arrivano al consumer sul WebSocket Hub con chiave canonica.

## Verifica ripetibile senza impianto

- Hub: `python -m pytest -q` dalla radice.
- eFace: `python -m pytest -q tests` dalla cartella e_face_x4; `node tests/test_device_groups.cjs`.
- UI isolata: `python scripts/preview_mqtt_composite.py`, quindi `node tests/test_mqtt_composite_browser.cjs`. Solo dati sintetici, storage temporaneo e porte localhost; nessun comando hardware.
- Prova fisica finale: selezionare volontariamente un dispositivo, salvare, provocare un evento e verificare il valore e la routine scelta. Non viene eseguita automaticamente durante l'installazione.
