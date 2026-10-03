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
    return ({locked:'Bloccata', unlocked:'Sbloccata', unlatching:'Apertura in corso', locking:'Blocco in corso', unlocking:'Sblocco in corso'})[String(value).toLowerCase()] || value;
  }
  function deviceCard(device) {
    const actions = [['unlock','Sblocca'],['lock','Blocca'],['unlatch','Apri porta'],['lockngo','Lock n Go']];
    return `<article class="adminFutureCard"><div class="flex"><div><b>${esc(device.name)}</b><div class="muted">ID ${esc(device.device_id)} · ${esc(stateText(device))} · ${device.available?'online':'non raggiungibile'}</div></div><span class="spacer"></span><label><input type="checkbox" data-policy="eface" data-id="${esc(device.device_id)}" ${device.enabled?'checked':''}> e-Face</label><label><input type="checkbox" data-policy="commands" data-id="${esc(device.device_id)}" ${device.read_only?'':'checked'}> Comandi</label></div><div class="flex" style="margin-top:12px">${actions.map(([action,label])=>`<button class="btn secondary small" data-command="${action}" data-id="${esc(device.device_id)}" ${device.read_only||!device.available?'disabled':''}>${label}</button>`).join('')}</div></article>`;
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
      root.innerHTML = `<div class="flex" style="align-items:center"><img src="static/hub/brands/nuki.svg" alt="Nuki" style="width:100px;height:63px;object-fit:contain"><div><b>Nuki Smart Access</b><div class="muted">Integrazione nativa e-Control · nessuna dipendenza da Home Assistant</div></div><span class="spacer"></span><span class="hub-badge">${status.mqtt_connected?'MQTT CONNESSO':'MQTT NON CONNESSO'}</span></div>
      <div class="notice" style="margin-top:14px"><b>Funzionamento ibrido:</b> MQTT locale gestisce stati e comandi. La Web API opzionale completa persone, autorizzazioni e storico accessi.</div>
      <form id="nukiConfig" class="adminFutureCard" style="margin-top:16px"><h3>Connessione</h3><div class="adminFutureGrid"><label><input type="checkbox" name="enabled" ${config.enabled?'checked':''}> Abilita integrazione MQTT locale</label><label>Prefisso MQTT<input name="mqtt_prefix" value="${esc(config.mqtt_prefix || 'nuki')}" required></label><label><input type="checkbox" name="cloud_enabled" ${config.cloud_enabled?'checked':''}> Abilita arricchimento Nuki Web API</label><label>Token Web API<input name="api_token" type="password" autocomplete="new-password" placeholder="${status.token_configured?'Configurato — lascia vuoto per mantenerlo':'Token opzionale'}"></label></div><div class="flex"><button class="btn" type="submit">Salva configurazione</button><button class="btn secondary" id="nukiSync" type="button" ${status.token_configured?'':'disabled'}>Sincronizza persone e accessi</button><button class="btn danger" id="nukiReset" type="button">Azzera configurazione Nuki</button><span class="muted" id="nukiMsg"></span></div></form>
      <h3>Dispositivi (${(data.devices||[]).length})</h3><p class="muted">e-Face decide la visibilità; Comandi autorizza il controllo diretto da questo pannello e da e-Face. Nomi, icone, categorie, piano e stanza si gestiscono in Dispositivi e presentazione.</p><div class="adminFutureGrid">${(data.devices||[]).map(deviceCard).join('') || '<div class="notice">Nessuna Nuki rilevata. Attiva MQTT nell’app Nuki sul broker usato da e-Control.</div>'}</div>
      <h3>Registro accessi</h3><div style="overflow:auto"><table><thead><tr><th>Data</th><th>Persona</th><th>Azione</th><th>Origine</th><th>Auth ID</th><th>Code ID</th></tr></thead><tbody>${(data.events||[]).map(eventRow).join('') || '<tr><td colspan="6" class="muted">Nessun evento registrato</td></tr>'}</tbody></table></div>`;
      bind(root);
    } catch (error) { root.innerHTML = `<div class="notice">Errore Nuki: ${esc(error.message)}</div>`; }
  }
  function bind(root) {
    root.querySelector('#nukiConfig')?.addEventListener('submit', async event => {
      event.preventDefault(); const form = event.currentTarget, msg = root.querySelector('#nukiMsg');
      try { await json('api/integrations/nuki/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:form.enabled.checked,mqtt_prefix:form.mqtt_prefix.value,cloud_enabled:form.cloud_enabled.checked,api_token:form.api_token.value})}); msg.textContent='Configurazione salvata'; await render(); } catch(error) { msg.textContent=error.message; }
    });
    root.querySelector('#nukiSync')?.addEventListener('click', async () => { const msg=root.querySelector('#nukiMsg'); try { msg.textContent='Sincronizzazione...'; await json('api/integrations/nuki/sync',{method:'POST'}); await render(); } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiReset')?.addEventListener('click', async () => { if (!confirm('Azzerare configurazione, catalogo ed eventi Nuki locali? Le serrature e il broker MQTT non verranno modificati.')) return; if (String(prompt('Scrivi AZZERA per confermare')||'').trim().toUpperCase()!=='AZZERA') return; try { await json('api/integrations/nuki/reset',{method:'POST'}); await render(); } catch(error) { alert(error.message); } });
    root.querySelectorAll('[data-policy]').forEach(input => input.addEventListener('change', async () => { const id=input.dataset.id, card=input.closest('article'), eface=card.querySelector('[data-policy="eface"]').checked, commands=card.querySelector('[data-policy="commands"]').checked; try { await json(`api/integrations/nuki/devices/${encodeURIComponent(id)}/policy`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({eface,commands})}); await render(); } catch(error) { alert(error.message); await render(); } }));
    root.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', async () => { if (!confirm(`${button.textContent} ${button.dataset.id}?`)) return; try { await json(`api/integrations/nuki/devices/${encodeURIComponent(button.dataset.id)}/command`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:button.dataset.command})}); } catch(error) { alert(error.message); } }));
  }
  const observer = new MutationObserver(() => { if (document.getElementById('nukiRoot') && !document.getElementById('nukiConfig')) render(); });
  observer.observe(document.documentElement,{childList:true,subtree:true});
  window.addEventListener('load',render);
})();
