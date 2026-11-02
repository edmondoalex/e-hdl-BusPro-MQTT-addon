/* Composition lives in organization, never in the MQTT configuration screen. */
(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  async function api(path, body) {
    const response = await fetch(new URL('api/'+path, location.href), {method:body ? 'PUT' : 'GET', cache:'no-store', headers:body ? {'Content-Type':'application/json'} : {}, body:body ? JSON.stringify(body) : undefined});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || `HTTP ${response.status}`);
    return data;
  }
  const value = row => `${row.state?.state ?? '—'} ${row.state?.attributes?.unit_of_measurement || ''}`.trim();
  window.EControlCardComposer = async (entityKey, organization, onSaved) => {
    if (document.querySelector('[data-card-composer]')) return;
    const dialog = document.createElement('dialog');
    dialog.dataset.cardComposer = ''; dialog.setAttribute('aria-label','Componi scheda multipla');
    dialog.innerHTML = '<p>Caricamento entità del dispositivo…</p><button type="button" data-close>Chiudi</button>';
    document.body.append(dialog); dialog.showModal();
    let dirty=false, saving=false;
    const close = () => {if (!saving && (!dirty || confirm('Chiudere senza salvare le modifiche alla scheda?'))) dialog.remove();};
    dialog.addEventListener('cancel', event => {event.preventDefault();close();});
    dialog.addEventListener('click', event => {if(event.target.closest('[data-close]'))close();});
    try {
      const catalog = await api('integrations/mqtt');
      const entity = catalog.entities.find(row => row.device_id === entityKey);
      if (!entity?.registry_device_id) throw Error('Questa entità non è associata a un dispositivo fisico MQTT.');
      const path = 'integrations/mqtt/devices/'+encodeURIComponent(entity.registry_device_id);
      const detail = await api(path), p = detail.presentation || {};
      const org = organization.devices || {};
      const oldOrder = p.member_order || [];
      const rows = [...detail.entities].sort((a,b) => (oldOrder.indexOf(a.device_id)<0?999:oldOrder.indexOf(a.device_id))-(oldOrder.indexOf(b.device_id)<0?999:oldOrder.indexOf(b.device_id)));
      const name = p.name || detail.device.name_by_user || detail.device.name;
      const title = row => org['mqtt:'+row.device_id]?.name_override || row.name;
      let primary = p.primary_id || (rows.find(r => r.enabled && r.device_id===entityKey) || rows.find(r=>r.enabled))?.device_id || '';
      dialog.innerHTML = `<style>
        [data-card-composer]{color:var(--text,#e8f2f4);background:var(--panel,#172126);border:1px solid #3b525c;border-radius:16px;width:min(960px,calc(100vw - 32px));max-height:90vh;box-sizing:border-box;padding:24px;overflow:auto}
        [data-card-composer]::backdrop{background:#0009}[data-card-composer] header,[data-card-composer] footer{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
        [data-card-composer] footer{position:sticky;bottom:-24px;margin:0 -24px -24px;padding:16px 24px;background:#172126;border-top:1px solid #3b525c;z-index:2}
        [data-card-composer] h2{margin:0}[data-card-composer] input:not([type=checkbox]),[data-card-composer] select{display:block;width:100%;box-sizing:border-box;margin:8px 0 16px;padding:12px;color:inherit;background:#10191d;border:1px solid #3b525c;border-radius:10px}
        [data-card-composer] input[type=checkbox]{width:20px;height:20px;flex-shrink:0}[data-card-composer] .composeMember{display:flex;align-items:center;gap:12px;padding:12px 0;border-top:1px solid #ffffff20}
        [data-card-composer] .composeMember label{display:flex;align-items:center;gap:12px;flex:1;min-width:0}[data-card-composer] small{display:block;overflow-wrap:anywhere;color:#a9bdc2}[data-card-composer] .composePreview{padding:18px;border:1px solid #3b525c;border-radius:12px;margin:16px 0}
        [data-card-composer] .composePreview div{display:flex;justify-content:space-between;gap:15px;margin-top:12px;overflow-wrap:anywhere}[data-card-composer] [data-result]{color:#6ee7b7}[data-card-composer] [data-result].error{color:#ffbd70}
        @media(max-width:600px){[data-card-composer]{padding:16px}[data-card-composer] footer{bottom:-16px;margin:0 -16px -16px;padding:12px 16px}.composeMember{flex-wrap:wrap}.composeMember label{flex-basis:100%!important}}
      </style><header><h2>Componi scheda multipla</h2><button type="button" class="btn secondary" data-close>Chiudi</button></header>
      <p>${esc(detail.device.name)} · scegli le entità da mostrare insieme. Le routine mantengono le entità separate.</p>
      <label>Nome della scheda<input data-name maxlength="160" value="${esc(name)}"></label>
      <details><summary>Opzioni facoltative</summary><label>Valore in evidenza<select data-primary></select></label><p>Scelto automaticamente. Piano, stanza, pagine e icona seguono questa entità.</p></details>
      <div data-members>${rows.map(row=>`<div class="composeMember" data-member="${esc(row.device_id)}"><label><input type="checkbox" data-selected ${row.enabled?'checked':''}><span>${esc(title(row))}<small>${esc(row.entity_id)}${row.disabled_by?' · Disabilitata':''}</small></span></label><b>${esc(value(row))}</b><button type="button" class="btn secondary" data-up aria-label="Sposta su ${esc(title(row))}">↑</button><button type="button" class="btn secondary" data-down aria-label="Sposta giù ${esc(title(row))}">↓</button></div>`).join('')}</div>
      <section class="composePreview" data-preview aria-label="Anteprima scheda"></section>
      <footer><button type="button" class="btn" data-save-composition>Salva scheda multipla</button><span data-result role="status" aria-live="polite"></span></footer>`;
      const selected = () => [...dialog.querySelectorAll('[data-member]')].filter(node=>node.querySelector('[data-selected]').checked).map(node=>node.dataset.member);
      const status = (text, error=false) => {const node=dialog.querySelector('[data-result]');node.textContent=text;node.classList.toggle('error',error);};
      function preview() {
        const keys=selected(), select=dialog.querySelector('[data-primary]');
        if (!keys.includes(primary)) primary=keys[0] || '';
        select.innerHTML=keys.map(key=>`<option value="${esc(key)}" ${key===primary?'selected':''}>${esc(title(rows.find(r=>r.device_id===key)))}</option>`).join('');
        dialog.querySelector('[data-preview]').innerHTML=`<strong>${esc(dialog.querySelector('[data-name]').value)}</strong><small>Una scheda · ${keys.length} valori</small>`+keys.map(key=>{const row=rows.find(r=>r.device_id===key);return `<div><span>${esc(title(row))}${key===primary?' · principale':''}</span><b>${esc(value(row))}</b></div>`;}).join('');
      }
      dialog.addEventListener('change', event=>{if(event.target.matches('[data-primary]'))primary=event.target.value;dirty=true;status('Modifiche non salvate');preview();});
      dialog.addEventListener('input', event=>{if(event.target.matches('[data-name]')){dirty=true;status('Modifiche non salvate');preview();}});
      dialog.addEventListener('click', async event=>{
        const button=event.target.closest('button');if(!button)return;
        const node=button.closest('[data-member]');
        if(node && (button.hasAttribute('data-up')||button.hasAttribute('data-down'))){
          if(button.hasAttribute('data-up')&&node.previousElementSibling)node.before(node.previousElementSibling);
          if(button.hasAttribute('data-down')&&node.nextElementSibling)node.after(node.nextElementSibling);
          dirty=true;status('Modifiche non salvate');preview();return;
        }
        if(!button.hasAttribute('data-save-composition')||saving)return;
        const keys=selected(), name=dialog.querySelector('[data-name]').value.trim();
        if(keys.length<2)return status('Seleziona almeno due entità per creare una scheda multipla.',true);
        if(!name)return status('Inserisci il nome della scheda.',true);
        const payload={name,grouped:true,primary_id:primary,member_order:keys,entities:Object.fromEntries(rows.map(row=>[row.device_id,{enabled:keys.includes(row.device_id),commands:keys.includes(row.device_id)&&!row.read_only}]))};
        saving=true;dialog.querySelectorAll('input,select,button').forEach(el=>el.disabled=true);status('Salvataggio e verifica…');
        try {
          await api(path+'/presentation',payload);
          const saved=await api(path), actual=saved.presentation;
          if(!actual.grouped || actual.name!==name || actual.primary_id!==primary || JSON.stringify(actual.member_order)!==JSON.stringify(keys) || saved.entities.some(row=>row.enabled!==payload.entities[row.device_id]?.enabled))throw Error('Verifica del salvataggio non riuscita. Riapri la scheda prima di riprovare.');
          const snapshot=await api('user/snapshot');
          const exported=(snapshot.smart_home?.devices||[]).filter(row=>keys.includes(row.id?.replace(/^mqtt:/,'')) && row.source==='mqtt');
          if(exported.length!==keys.length || exported.some(row=>row.presentation_group?.primary_id!=='mqtt:'+primary))throw Error('Selezione salvata, ma il catalogo eFace non contiene tutte le entità raggruppate.');
          dirty=false;await onSaved?.();
          const hidden=exported.some(row=>row.visible===false);
          status(`Salvataggio verificato: una scheda con ${keys.length} valori.${hidden?' Attenzione: alcune entità sono nascoste nelle pagine; controlla la visibilità.':''}`,hidden);
        }catch(error){status(error.message,true);}finally{saving=false;dialog.querySelectorAll('input,select,button').forEach(el=>el.disabled=false);}
      });
      preview();
    }catch(error){dialog.querySelector('p').textContent=error.message;}
  };
})();
