(function () {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const url = path => new URL(path, window.location.href).toString();
  const style = document.createElement('link');
  style.rel = 'stylesheet'; style.href = url('static/hub/nuki.css?v=0.1.552'); document.head.appendChild(style);
  const viewKey = 'econtrol.nuki.directory.v1';
  let view = {query:'', filter:'all', closed:[], expanded:[]};
  try { Object.assign(view, JSON.parse(localStorage.getItem(viewKey) || '{}')); } catch (_) {}
  if (!['all','users','codes','accessories','other'].includes(view.filter)) view.filter = 'all';
  if (!Array.isArray(view.closed)) view.closed = [];
  if (!Array.isArray(view.expanded)) view.expanded = [];
  function saveView() { try { localStorage.setItem(viewKey, JSON.stringify(view)); } catch (_) {} }
  const groups = [['users','Utenti e app','user'],['codes','Codici keypad','key'],['accessories','Accessori','keypad'],['other','Altre autorizzazioni','link']];
  function glyph(name) {
    const paths = {
      lock:'<rect x="5" y="10" width="14" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
      user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
      key:'<circle cx="8" cy="8" r="5"/><path d="m11.5 11.5 9 9m-5-5 3-3m0 6 3-3"/>',
      keypad:'<rect x="5" y="2" width="14" height="20" rx="3"/><path d="M9 6h6m-6 4h.01M15 10h.01M9 14h.01M15 14h.01M9 18h.01M15 18h.01"/>',
      link:'<path d="m10 13 4-4m-6 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 2 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
      search:'<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',
      refresh:'<path d="M20 7v5h-5M4 17v-5h5M5 7a8 8 0 0 1 13-2l2 3M4 16l2 3a8 8 0 0 0 13-2"/>',
      chevron:'<path d="m9 5 7 7-7 7"/>',
    };
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.link}</svg>`;
  }
  function dateText(value) {
    if (!value) return '';
    const date = new Date(typeof value === 'number' ? value * 1000 : value);
    return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('it-IT', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
  }
  function authRow(entry, scope) {
    const fold = `${scope}:${entry.web_id || entry.auth_id || ''}`;
    const expired = entry.allowed_until && new Date(entry.allowed_until).getTime() < Date.now();
    const future = entry.allowed_from && new Date(entry.allowed_from).getTime() > Date.now();
    const badge = entry.enabled === false ? 'Disabilitata' : expired ? 'Scaduta' : future ? 'Programmata' : 'Abilitata';
    const quiet = entry.enabled === false || expired;
    const symbol = groups.find(([key])=>key===entry.group)?.[2] || 'link';
    const details = [['ID autorizzazione',entry.auth_id],['Valida dal',dateText(entry.allowed_from)],['Valida fino al',dateText(entry.allowed_until)],['Accesso remoto',entry.remote_allowed === true ? 'Consentito' : entry.remote_allowed === false ? 'Non consentito' : '']].filter(([,value])=>value);
    return `<details class="nuki-auth ${quiet?'is-disabled':''}" data-nuki-expand="${esc(fold)}" ${view.expanded.includes(fold)?'open':''}><summary><span class="nuki-avatar is-${esc(entry.group)}">${glyph(symbol)}</span><span class="nuki-auth-name"><strong>${esc(entry.name)}</strong><small>${esc(entry.type_label)}</small></span><span class="nuki-auth-status ${quiet?'is-muted':future?'is-pending':''}">${badge}</span><span class="nuki-chevron">${glyph('chevron')}</span></summary><dl class="nuki-auth-meta">${details.map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('') || '<div><dt>Dettagli</dt><dd>Non forniti da Nuki</dd></div>'}</dl></details>`;
  }
  function directoryCards(data, organization) {
    const directory = data.access_directory || {locks:[],unassigned:[]};
    const query = String(view.query || '').trim().toLocaleLowerCase('it');
    const matches = entry => `${entry.name} ${entry.type_label} ${entry.auth_id || ''}`.toLocaleLowerCase('it').includes(query);
    const cards = directory.locks.map(lock => {
      const org = (organization.devices || {})[`nuki:${lock.device_id}`] || {};
      const lockMatch = `${lock.name} ${org.room_name || ''}`.toLocaleLowerCase('it').includes(query);
      const entries = lock.entries.filter(entry => (view.filter === 'all' || view.filter === entry.group) && (lockMatch || matches(entry)));
      if (!entries.length && (query || view.filter !== 'all')) return '';
      const state = lock.state?.state;
      const label = state === 'locked' ? 'Bloccata' : state === 'unlocked' ? 'Sbloccata' : stateText(lock);
      return `<article class="nuki-lock-card"><header><span class="nuki-lock-icon">${glyph('lock')}</span><div class="nuki-lock-title"><h4>${esc(lock.name)}</h4><span>${esc(org.room_name || 'Serratura Nuki')}</span></div><span class="nuki-lock-state ${state==='unlocked'?'is-open':''}">${esc(label)}</span></header><div class="nuki-lock-summary"><span>${entries.length} ${entries.length===1?'autorizzazione':'autorizzazioni'}</span><span>${lock.sync_status==='error'?'Catalogo salvato':lock.last_synced_at?'Sincronizzato':'Catalogo Nuki'}</span></div><div class="nuki-lock-groups">${groups.map(([group,title,symbol])=>{
        const items = entries.filter(entry=>entry.group===group);
        if (!items.length) return '';
        const key = `${lock.device_id}:${group}`;
        return `<details class="nuki-auth-group" data-nuki-fold="${esc(key)}" ${view.closed.includes(key)?'':'open'}><summary>${glyph(symbol)}<span>${title}</span><b>${items.length}</b><span class="nuki-chevron">${glyph('chevron')}</span></summary><div>${items.map(entry=>authRow(entry,lock.device_id)).join('')}</div></details>`;
      }).join('') || '<p class="nuki-empty">Nessuna autorizzazione associata nel catalogo disponibile.</p>'}</div><footer>${lock.last_synced_at?`Ultima sincronizzazione · ${esc(dateText(lock.last_synced_at))}`:'Sincronizza Nuki Web per aggiornare le associazioni'}${lock.sync_status==='error'?'<span>Ultimo aggiornamento non riuscito</span>':''}</footer></article>`;
    }).filter(Boolean);
    const unassigned = directory.unassigned.filter(entry=>(view.filter==='all'||view.filter===entry.group)&&matches(entry));
    return `<div class="nuki-lock-grid">${cards.join('') || `<div class="nuki-directory-empty">${glyph('search')}<h4>${query || view.filter!=='all'?'Nessun risultato':'Le tue serrature, le loro autorizzazioni'}</h4><p>${query || view.filter!=='all'?'Prova un altro nome o seleziona Tutti.':'Sincronizza Nuki Web per visualizzare utenti, codici e accessori associati.'}</p></div>`}</div>${unassigned.length?`<details class="nuki-unassigned" data-nuki-expand="unassigned" ${view.expanded.includes('unassigned')?'open':''}><summary>${glyph('link')}<span>Associazioni da verificare</span><b>${unassigned.length}</b><span class="nuki-chevron">${glyph('chevron')}</span></summary><p>Nuki non ha fornito una serratura per questi record salvati. Non vengono assegnati in base al nome.</p><div>${unassigned.map(entry=>authRow(entry,'unassigned')).join('')}</div></details>`:''}`;
  }
  function directoryPanel(data, organization) {
    const counts = data.access_directory?.counts || {};
    return `<section class="nuki-directory" aria-labelledby="nukiDirectoryTitle"><div class="nuki-directory-heading"><div><span class="nuki-eyebrow">ACCESSI ASSOCIATI</span><h3 id="nukiDirectoryTitle">Utenti, codici e accessori</h3><p>Ogni serratura, con le autorizzazioni registrate in Nuki.</p></div><button type="button" class="btn secondary nuki-sync" data-nuki-directory-sync ${data.status?.token_configured?'':'disabled'}>${glyph('refresh')}<span>Sincronizza Nuki</span></button></div><div class="nuki-directory-stats">${[['locks','Serrature','lock'],['users','Utenti e app','user'],['codes','Codici keypad','key'],['accessories','Accessori','keypad']].map(([key,label,symbol])=>`<div><span>${glyph(symbol)}</span><strong>${Number(counts[key] || 0)}</strong><small>${label}</small></div>`).join('')}</div><div class="nuki-directory-toolbar"><label class="nuki-search">${glyph('search')}<input type="search" data-nuki-search aria-label="Cerca serratura, utente, codice o accessorio" placeholder="Cerca serratura, utente o codice…" value="${esc(view.query)}"></label><div class="nuki-directory-filters" aria-label="Filtra autorizzazioni">${[['all','Tutti'],['users','Utenti e app'],['codes','Codici'],['accessories','Accessori'],['other','Altro']].map(([key,label])=>`<button type="button" data-nuki-filter="${key}" aria-pressed="${view.filter===key}">${label}</button>`).join('')}</div></div><p class="nuki-directory-message" data-nuki-directory-message role="status"></p><div id="nukiDirectoryBody">${directoryCards(data,organization)}</div></section>`;
  }
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
  function deviceCard(device, organization = {}) {
    const actions = [['unlock','Sblocca'],['lock','Blocca'],['unlatch','Apri porta'],['lockngo','Lock n Go']];
    const icon = organization.icon_override || organization.icon_auto || 'mdi:lock-smart';
    return `<article class="adminFutureCard"><div class="flex"><div><b>${esc(device.name)}</b><div class="muted">ID ${esc(device.device_id)} · ${esc(transport(device))}</div><span data-icon-preview-value="${esc(icon)}"></span></div><span class="spacer"></span><label><input type="checkbox" data-policy="eface" data-id="${esc(device.device_id)}" ${device.enabled?'checked':''}> e-Face</label><label><input type="checkbox" data-policy="commands" data-id="${esc(device.device_id)}" ${device.read_only?'':'checked'}> Comandi</label></div><div class="adminFutureGrid" style="margin-top:12px;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px"><div><span class="muted">Stato</span><br><b>${esc(stateText(device))}</b></div><div><span class="muted">Batteria</span><br><b>${esc(batteryText(device))}</b></div><div><span class="muted">Porta</span><br><b>${esc(doorText(device))}</b></div><div><span class="muted">Connessione</span><br><b>${device.available?'Online':'Non raggiungibile'}</b></div></div><form data-nuki-icon-form data-id="${esc(device.device_id)}" class="flex" style="margin-top:12px"><label style="min-width:min(100%,280px)">Icona MDI<input name="icon_override" value="${esc(organization.icon_override || '')}" placeholder="${esc(organization.icon_auto || 'mdi:lock-smart')}"></label><button class="btn secondary small" type="submit">Salva icona</button><span class="muted" data-icon-msg></span></form><div class="flex" style="margin-top:12px">${actions.map(([action,label])=>`<button class="btn secondary small" data-command="${action}" data-id="${esc(device.device_id)}" ${device.read_only||!device.available?'disabled':''}>${label}</button>`).join('')}</div></article>`;
  }
  function eventRow(event) {
    const stamp = event.timestamp ? new Date(typeof event.timestamp === 'number' ? event.timestamp * 1000 : event.timestamp).toLocaleString('it-IT') : '—';
    return `<tr><td>${esc(stamp)}</td><td><b>${esc(event.device_name || event.device_id || 'Nuki')}</b></td><td>${esc(event.person || 'Origine non identificata')}</td><td>${esc(event.action_name || event.action)}</td><td>${esc(event.origin || event.trigger_name || event.trigger || '—')}</td><td>${esc(event.auth_id || '—')}</td><td>${esc(event.code_id || '—')}</td></tr>`;
  }
  async function render() {
    const root = document.getElementById('nukiRoot');
    if (!root) return;
    try {
      const [data, organization] = await Promise.all([json('api/integrations/nuki'), json('api/organization')]);
      const status = data.status || {}, config = data.config || {};
      root.innerHTML = `<div class="flex" style="align-items:center"><img src="static/hub/brands/nuki.svg" alt="Nuki" style="width:100px;height:63px;object-fit:contain"><div><b>Nuki Smart Access</b><div class="muted">Integrazione nativa e-Control · nessuna dipendenza da Home Assistant</div></div><span class="spacer"></span><span class="hub-badge">${status.bridge_token_configured?'BRIDGE LOCALE':'BRIDGE NON ASSOCIATO'}</span></div>
      <div class="notice" style="margin-top:14px"><b>Funzionamento locale:</b> Nuki Bridge o MQTT gestiscono stati e comandi anche senza Internet. La Web API è opzionale e serve per persone, autorizzazioni e storico accessi.</div>
      ${directoryPanel(data,organization)}
      <details class="nuki-connection-panel" data-nuki-expand="connections" ${view.expanded.includes('connections')?'open':''}><summary>${glyph('link')}<span>Connessioni e configurazione</span><span class="nuki-chevron">${glyph('chevron')}</span></summary><form id="nukiConfig" class="adminFutureCard" style="margin-top:16px"><h3>Nuki Bridge locale</h3><div class="notice"><b>Associazione:</b> premi prima <b>Associa Bridge</b> e subito dopo premi il pulsante fisico del Bridge entro 30 secondi. Attendi la conferma senza cambiare pagina.</div><p class="muted">Rileva Bridge compila automaticamente indirizzo e porta. Il token resta protetto nel dispositivo e non viene mostrato.</p><div class="adminFutureGrid"><label><input type="checkbox" name="bridge_enabled" ${config.bridge_enabled?'checked':''}> Abilita Nuki Bridge locale</label><label>Indirizzo Bridge<input name="bridge_host" value="${esc(config.bridge_host || '')}" placeholder="es. 192.168.1.50"></label><label>Porta<input name="bridge_port" type="number" min="1" max="65535" value="${esc(config.bridge_port || 8080)}"></label></div><div class="flex"><button class="btn secondary" id="nukiDetectBridge" type="button">Rileva Bridge</button><button class="btn" id="nukiPairBridge" type="button">Associa Bridge</button><button class="btn secondary" id="nukiSyncBridge" type="button" ${status.bridge_token_configured?'':'disabled'}>Aggiorna dispositivi locali</button></div>
      <h3 style="margin-top:22px">MQTT locale e Web API opzionale</h3><div class="adminFutureGrid"><label><input type="checkbox" name="enabled" ${config.enabled?'checked':''}> Abilita integrazione MQTT locale</label><label>Prefisso MQTT<input name="mqtt_prefix" value="${esc(config.mqtt_prefix || 'nuki')}" required></label><label><input type="checkbox" name="cloud_enabled" ${config.cloud_enabled?'checked':''}> Abilita arricchimento Nuki Web API</label><label>Token Web API<input name="api_token" type="password" autocomplete="new-password" placeholder="${status.token_configured?'Configurato — lascia vuoto per mantenerlo':'Token opzionale'}"></label></div><div class="flex"><button class="btn" type="submit">Salva configurazione</button><button class="btn secondary" id="nukiSync" type="button" ${status.token_configured?'':'disabled'}>Sincronizza persone e accessi</button><button class="btn danger" id="nukiReset" type="button">Azzera configurazione Nuki</button><span class="muted" id="nukiMsg"></span></div></form>
      </details><h3>Dispositivi (${(data.devices||[]).length})</h3><p class="muted">L'icona si modifica direttamente qui; piano, stanza, pagine e permessi restano centralizzati in Dispositivi e presentazione.</p><div class="adminFutureGrid">${(data.devices||[]).map(device=>deviceCard(device,(organization.devices||{})[`nuki:${device.device_id}`]||{})).join('') || '<div class="notice">Nessuna Nuki rilevata. Associa il Bridge locale oppure attiva MQTT nell’app Nuki.</div>'}</div>
      <h3>Registro accessi</h3><div style="overflow:auto"><table><thead><tr><th>Data</th><th>Serratura</th><th>Persona</th><th>Azione</th><th>Origine</th><th>Auth ID</th><th>Code ID</th></tr></thead><tbody>${(data.events||[]).map(eventRow).join('') || '<tr><td colspan="7" class="muted">Nessun evento registrato</td></tr>'}</tbody></table></div>`;
      bind(root, data, organization);
    } catch (error) { root.innerHTML = `<div class="notice">Errore Nuki: ${esc(error.message)}</div>`; }
  }
  function configPayload(form) {
    return {enabled:form.enabled.checked,mqtt_prefix:form.mqtt_prefix.value,cloud_enabled:form.cloud_enabled.checked,api_token:form.api_token.value,bridge_enabled:form.bridge_enabled.checked,bridge_host:form.bridge_host.value,bridge_port:Number(form.bridge_port.value || 8080)};
  }
  function bind(root, data, organization) {
    const form = root.querySelector('#nukiConfig'), msg = root.querySelector('#nukiMsg');
    const rememberFolds = () => {
      root.querySelectorAll('[data-nuki-fold],[data-nuki-expand]').forEach(details => {
        if (details.dataset.nukiBound) return;
        details.dataset.nukiBound = 'true';
        details.addEventListener('toggle', () => {
        const expanded = !!details.dataset.nukiExpand;
        const field = expanded ? 'expanded' : 'closed';
        const key = details.dataset.nukiExpand || details.dataset.nukiFold;
        view[field] = view[field].filter(item=>item!==key);
        if (expanded ? details.open : !details.open) view[field].push(key);
        saveView();
        });
      });
    };
    rememberFolds();
    root.querySelectorAll('form').forEach(draft=>draft.addEventListener('input',()=>{draft.dataset.nukiDirty='true';}));
    function updateDirectory() {
      root.querySelector('#nukiDirectoryBody').innerHTML = directoryCards(data,organization);
      root.querySelectorAll('[data-nuki-filter]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.nukiFilter===view.filter)));
      rememberFolds(); saveView();
    }
    root.querySelector('[data-nuki-search]')?.addEventListener('input', event=>{view.query=event.target.value;updateDirectory();});
    root.querySelectorAll('[data-nuki-filter]').forEach(button=>button.addEventListener('click',()=>{view.filter=button.dataset.nukiFilter;updateDirectory();}));
    root.querySelector('[data-nuki-directory-sync]')?.addEventListener('click', async event=>{
      const button=event.currentTarget, message=root.querySelector('[data-nuki-directory-message]');
      button.disabled=true; message.textContent='Aggiornamento delle associazioni da Nuki…';
      try { await json('api/integrations/nuki/sync',{method:'POST'}); await render(); }
      catch(error) { button.disabled=false; message.textContent=error.message; }
    });
    form?.addEventListener('submit', async event => { event.preventDefault(); try { await json('api/integrations/nuki/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(configPayload(form))}); await render(); } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiDetectBridge')?.addEventListener('click', async () => { try { msg.textContent='Ricerca Bridge...'; const result=await json('api/integrations/nuki/bridges'); const bridge=(result.items||[])[0]; if(!bridge) throw new Error('Nessun Nuki Bridge rilevato'); form.bridge_host.value=bridge.ip||bridge.host||''; form.bridge_port.value=bridge.port||8080; form.bridge_enabled.checked=true; msg.textContent=`Bridge rilevato: ${form.bridge_host.value}`; } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiPairBridge')?.addEventListener('click', async event => { const button=event.currentTarget; try { button.disabled=true; button.textContent='Premi ora il pulsante fisico'; msg.textContent='Finestra di associazione aperta: premi ora il pulsante fisico del Bridge entro 30 secondi...'; await new Promise(resolve=>setTimeout(resolve,100)); await json('api/integrations/nuki/bridge/pair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:form.bridge_host.value,port:Number(form.bridge_port.value||8080)})}); await render(); } catch(error) { button.disabled=false; button.textContent='Associa Bridge'; msg.textContent=error.message; } });
    root.querySelector('#nukiSyncBridge')?.addEventListener('click', async () => { try { msg.textContent='Aggiornamento Bridge...'; await json('api/integrations/nuki/bridge/sync',{method:'POST'}); await render(); } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiSync')?.addEventListener('click', async () => { try { msg.textContent='Sincronizzazione...'; await json('api/integrations/nuki/sync',{method:'POST'}); await render(); } catch(error) { msg.textContent=error.message; } });
    root.querySelector('#nukiReset')?.addEventListener('click', async () => { if (!confirm('Azzerare configurazione, catalogo ed eventi Nuki locali? Le serrature e il broker MQTT non verranno modificati.')) return; if (String(prompt('Scrivi AZZERA per confermare')||'').trim().toUpperCase()!=='AZZERA') return; try { await json('api/integrations/nuki/reset',{method:'POST'}); await render(); } catch(error) { alert(error.message); } });
    root.querySelectorAll('[data-policy]').forEach(input => input.addEventListener('change', async () => { const id=input.dataset.id, card=input.closest('article'), eface=card.querySelector('[data-policy="eface"]').checked, commands=card.querySelector('[data-policy="commands"]').checked; try { await json(`api/integrations/nuki/devices/${encodeURIComponent(id)}/policy`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({eface,commands})}); await render(); } catch(error) { alert(error.message); await render(); } }));
    root.querySelectorAll('[data-nuki-icon-form]').forEach(iconForm => iconForm.addEventListener('submit', async event => { event.preventDefault(); const message=iconForm.querySelector('[data-icon-msg]'); try { await json(`api/integrations/nuki/devices/${encodeURIComponent(iconForm.dataset.id)}/configuration`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({icon_override:iconForm.icon_override.value.trim()})}); message.textContent='Salvata'; document.dispatchEvent(new CustomEvent('econtrol:organization-changed')); await render(); } catch(error) { message.textContent=error.message; } }));
    root.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', async () => { if (!confirm(`${button.textContent} ${button.dataset.id}?`)) return; try { await json(`api/integrations/nuki/devices/${encodeURIComponent(button.dataset.id)}/command`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:button.dataset.command})}); await render(); } catch(error) { alert(error.message); } }));
  }
  const observer = new MutationObserver(() => { if (document.getElementById('nukiRoot') && !document.getElementById('nukiConfig')) render(); });
  observer.observe(document.documentElement,{childList:true,subtree:true});
  window.addEventListener('load',render);
  window.setInterval(() => {
    const root = document.getElementById('nukiRoot');
    if (!root || root.contains(document.activeElement) || root.querySelector('[data-nuki-dirty]')) return;
    render();
  }, 5000);
})();
