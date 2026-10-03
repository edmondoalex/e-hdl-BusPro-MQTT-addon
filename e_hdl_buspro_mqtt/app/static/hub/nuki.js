(function () {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const url = path => new URL(path, window.location.href).toString();
  async function json(path, options = {}) {
    const response = await fetch(url(path), {cache: 'no-store', ...options});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }
  function stateText(device) {
    const value = device.state?.state || 'unknown';
    return ({locked:'Bloccata', unlocked:'Sbloccata', unlatched:'Porta aperta', unlatching:'Apertura in corso', locking:'Blocco in corso', unlocking:'Sblocco in corso', uncalibrated:'Non calibrata'})[String(value).toLowerCase()] || value;
  }
  function transport(device) {
    const attrs = device.state?.attributes || {};
    if (attrs.firmware) return 'MQTT locale';
    if (device.bridge_id !== undefined && device.bridge_id !== null) return 'Bridge locale';
    return device.web ? 'Web API' : 'Locale';
  }
  function yes(value) { return String(value ?? '').toLowerCase() === 'true'; }
  function batteryText(device) {
    const attrs = device.state?.attributes || {};
    const level = Number.parseInt(attrs.batteryChargeState, 10);
    const charging = yes(attrs.batteryCharging);
    if (Number.isFinite(level)) return `${level}%${charging ? ' · in carica' : ''}`;
    if (yes(attrs.batteryCritical)) return 'Critica';
    if (attrs.batteryCritical !== undefined) return `OK${charging ? ' · in carica' : ''}`;
    return 'Non disponibile';
  }
  function doorText(device) {
    const attrs = device.state?.attributes || {};
    const value = String(attrs.doorsensorState || attrs.doorState || '').toLowerCase();
    return ({0:'Non disponibile',1:'Chiusa',2:'Aperta',3:'Sconosciuta',4:'Calibrazione'})[value] || (value || 'Non disponibile');
  }
  function deviceCard(device) {
    const actions = [['unlock','Sblocca'],['lock','Blocca'],['unlatch','Apri porta'],['lockngo','Lock n Go']];
    return `<article class="adminFutureCard"><div class="flex"><div><b>${esc(device.name)}</b><div class="muted">ID ${esc(device.device_id)} · ${esc(transport(device))}</div></div><span class="spacer"></span><label><input type="checkbox" data-policy="eface" data-id="${esc(device.device_id)}" ${device.enabled?'checked':''}> e-Face</label><label><input type="checkbox" data-policy="commands" data-id="${esc(device.device_id)}" ${device.read_only?'':'checked'}> Comandi</label></div><div class="adminFutureGrid" style="margin-top:12px;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px"><div><span class="muted">Stato</span><br><b>${esc(stateText(device))}</b></div><div><span class="muted">Batteria</span><br><b>${esc(batteryText(device))}</b></div><div><span class="muted">Porta</span><br><b>${esc(doorText(device))}</b></div><div><span class="muted">Connessione</span><br><b>${device.available?'Online':'Non raggiungibile'}</b></div></div><div class="flex" style="margin-top:12px">${actions.map(([action,label])=>`<button class="btn secondary small" data-command="${action}" data-id="${esc(device.device_id)}" ${device.read_only||!device.available?'disabled':''}>${label}</button>`).join('')}</div></article>`;
  }
  function eventRow(event) {
    const stamp = event.timestamp ? new Date(typeof event.timestamp === 'number' ? event.timestamp * 1000 : event.timestamp).toLocaleString('it-IT') : '—';
    return `<tr><td>${esc(stamp)}</td><td>${esc(event.person || 'Origine non identificata')}</td><td>${esc(event.action_name || event.action)}</td><td>${esc(event.trigger_name || event.trigger || '—')}</td><td>${esc(event.auth_id || '—')}</td><td>${esc(event.code_id || '—')}</td></tr>`;
  }
  async function render() {
    const root = document.getElementById('nukiRoot');
    if (!root) return;
    try {
      const data = await json('api/integrations/nuki');
      const status = data.status || {}, config = data.config || {};
      root.innerHTML = `<div class="flex" style="align-items:center"><img src="static/hub/brands/nuki.svg" alt="Nuki" style="width:100px;height:63px;object-fit:contain"><div><b>Nuki Smart Access</b><div class="muted">Integrazione nativa e-Control · nessuna dipendenza da Home Assistant</div></div><span class="spacer"></span><span class="hub-badge">${status.bridge_token_configured?'BRIDGE LOCALE':'BRIDGE NON ASSOCIATO'}</span></div>
      <div class="notice" style="margin-top:14px"><b>Funzionamento locale:</b> Nuki Bridge o MQTT gestiscono stati e comandi anche senza Internet. La Web API è opzionale e serve per persone, autorizzazioni e storico accessi.</div>
      <form id="nukiConfig" class="adminFutureCard" style="margin-top:16px"><h3>Nuki Bridge locale</h3><div class="notice"><b>Associazione:</b> premi prima <b>Associa Bridge</b> e subito dopo premi il pulsante fisico del Bridge entro 30 secondi. Attendi la conferma senza cambiare pagina.</div><p class="muted">Rileva Bridge compila automaticamente indirizzo e porta. Il token resta protetto nel dispositivo e non viene mostrato.</p><div class="adminFutureGrid"><label><input type="checkbox" name="bridge_enabled" ${config.bridge_enabled?'checked':''}> Abilita Nuki Bridge locale</label><label>Indirizzo Bridge<input name="bridge_host" value="${esc(config.bridge_host || '')}" placeholder="es. 192.168.1.50"></label><label>Porta<input name="bridge_port" type="number" min="1" max="65535" value="${esc(config.bridge_port || 8080)}"></label></div><div class="flex"><button class="btn secondary" id="nukiDetectBridge" type="button">Rileva Bridge</button><button class="btn" id="nukiPairBridge" type="button">Associa Bridge</button><button class="btn secondary" id="nukiSyncBridge" type="button" ${status.bridge_token_configured?'':'disabled'}>Aggiorna dispositivi locali</button></div>
      <h3 style="margin-top:22px">MQTT locale e Web API opzionale</h3><div class="adminFutureGrid"><label><input type="checkbox" name="enabled" ${config.enabled?'checked':''}> Abilita integrazione MQTT locale</label><label>Prefisso MQTT<input name="mqtt_prefix" value="${esc(config.mqtt_prefix || 'nuki')}" required></label><label><input type="checkbox" name="cloud_enabled" ${config.cloud_enabled?'checked':''}> Abilita arricchimento Nuki Web API</label><label>Token Web API<input name="api_token" type="password" autocomplete="new-password" placeholder="${status.token_configured?'Configurato — lascia vuoto per mantenerlo':'Token opzionale'}"></label></div><div class="flex"><button class="btn" type="submit">Salva configurazione</button><button class="btn secondary" id="nukiSync" type="button" ${status.token_configured?'':'disabled'}>Sincronizza persone e accessi</button><button class="btn danger" id="nukiReset" type="button">Azzera configurazione Nuki</button><span class="muted" id="nukiMsg"></span></div></form>
      <h3>Dispositivi (${(data.devices||[]).length})</h3><p class="muted">e-Face decide la visibilità; Comandi autorizza il controllo diretto da questo pannello e da e-Face. Nomi, icone, categorie, piano e stanza si gestiscono in Dispositivi e presentazione.</p><div class="adminFutureGrid">${(data.devices||[]).map(deviceCard).join('') || '<div class="notice">Nessuna Nuki rilevata. Associa il Bridge locale oppure attiva MQTT nell’app Nuki.</div>'}</div>
      <h3>Registro accessi</h3><div style="overflow:auto"><table><thead><tr><th>Data</th><th>Persona</th><th>Azione</th><th>Origine</th><th>Auth ID</th><th>Code ID</th></tr></thead><tbody>${(data.events||[]).map(eventRow).join('') || '<tr><td colspan="6" class="muted">Nessun evento registrato</td></tr>'}</tbody></table></div>`;
      bind(root);
    } catch (error) { root.innerHTML = `<div class="notice">Errore Nuki: ${esc(error.message)}</div>`; }
  }
  function configPayload(form) {
    return {enabled:form.enabled.checked,mqtt_prefix:form.mqtt_prefix.value,cloud_enabled:form.cloud_enabled.checked,api_token:form.api_token.value,bridge_enabled:form.bridge_enabled.checked,bridge_host:form.bridge_host.value,bridge_port:Number(form.bridge_port.value || 8080)};
  }
  function bind(root) {
    const form = root.querySelector('#nukiConfig'), msg = root.querySelector('#nukiMsg');
    form?.addEventListener('submit', async event => { event.preventDefault(); try { await json('api/integrations/nuki/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(configPayload(form))}); await render(); } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiDetectBridge')?.addEventListener('click', async () => { try { msg.textContent='Ricerca Bridge...'; const result=await json('api/integrations/nuki/bridges'); const bridge=(result.items||[])[0]; if(!bridge) throw new Error('Nessun Nuki Bridge rilevato'); form.bridge_host.value=bridge.ip||bridge.host||''; form.bridge_port.value=bridge.port||8080; form.bridge_enabled.checked=true; msg.textContent=`Bridge rilevato: ${form.bridge_host.value}`; } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiPairBridge')?.addEventListener('click', async event => { const button=event.currentTarget; try { button.disabled=true; button.textContent='Premi ora il pulsante fisico'; msg.textContent='Finestra di associazione aperta: premi ora il pulsante fisico del Bridge entro 30 secondi...'; await new Promise(resolve=>setTimeout(resolve,100)); await json('api/integrations/nuki/bridge/pair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:form.bridge_host.value,port:Number(form.bridge_port.value||8080)})}); await render(); } catch(error) { button.disabled=false; button.textContent='Associa Bridge'; msg.textContent=error.message; } });
    root.querySelector('#nukiSyncBridge')?.addEventListener('click', async () => { try { msg.textContent='Aggiornamento Bridge...'; await json('api/integrations/nuki/bridge/sync',{method:'POST'}); await render(); } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiSync')?.addEventListener('click', async () => { try { msg.textContent='Sincronizzazione...'; await json('api/integrations/nuki/sync',{method:'POST'}); await render(); } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiReset')?.addEventListener('click', async () => { if (!confirm('Azzerare configurazione, catalogo ed eventi Nuki locali? Le serrature e il broker MQTT non verranno modificati.')) return; if (String(prompt('Scrivi AZZERA per confermare')||'').trim().toUpperCase()!=='AZZERA') return; try { await json('api/integrations/nuki/reset',{method:'POST'}); await render(); } catch(error) { alert(error.message); } });
    root.querySelectorAll('[data-policy]').forEach(input => input.addEventListener('change', async () => { const id=input.dataset.id, card=input.closest('article'), eface=card.querySelector('[data-policy="eface"]').checked, commands=card.querySelector('[data-policy="commands"]').checked; try { await json(`api/integrations/nuki/devices/${encodeURIComponent(id)}/policy`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({eface,commands})}); await render(); } catch(error) { alert(error.message); await render(); } }));
    root.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', async () => { if (!confirm(`${button.textContent} ${button.dataset.id}?`)) return; try { await json(`api/integrations/nuki/devices/${encodeURIComponent(button.dataset.id)}/command`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:button.dataset.command})}); await render(); } catch(error) { alert(error.message); } }));
  }
  const observer = new MutationObserver(() => { if (document.getElementById('nukiRoot') && !document.getElementById('nukiConfig')) render(); });
  observer.observe(document.documentElement,{childList:true,subtree:true});
  window.addEventListener('load',render);
  window.setInterval(() => {
    const root = document.getElementById('nukiRoot');
    if (!root || root.contains(document.activeElement)) return;
    render();
  }, 5000);
})();
