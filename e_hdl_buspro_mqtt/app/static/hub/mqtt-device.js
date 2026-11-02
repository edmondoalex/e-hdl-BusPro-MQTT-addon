/* Physical association comes from the registry. Presentation lives in organization. */
(() => {
  'use strict';
  window.EControlMqttDevice = ({panel, api, esc, status, editEntity}) => {
    const host = document.createElement('section');
    host.className='mqBox';host.hidden=true;host.dataset.physicalDevice='';
    panel.querySelector('[data-editor]').before(host);
    let current='', detail=null, polling=false;
    const stateText = row => `${row.state?.state ?? '—'} ${row.state?.attributes?.unit_of_measurement || ''}`.trim();
    function controls(row) {
      const a=row.state?.attributes||{}, disabled=row.available?'':'disabled', key=esc(row.device_id);
      const input=(html,action)=>`<form data-entity-command="${key}" data-command="${action}" class="mqToolbar">${html}<button class="btn secondary" ${disabled}>Applica</button></form>`;
      if(row.domain==='number')return input(`<input name="value" aria-label="Valore ${esc(row.name)}" type="number" min="${esc(a.min)}" max="${esc(a.max)}" step="${esc(a.step||'any')}" value="${esc(row.state?.state)}" required ${disabled}>`,'level');
      if(row.domain==='select')return input(`<select name="value" aria-label="Opzione ${esc(row.name)}" ${disabled}>${(a.options||[]).map(v=>`<option ${v===row.state?.state?'selected':''}>${esc(v)}</option>`).join('')}</select>`,'mode');
      if(row.domain==='update')return '<button type="button" class="btn secondary" data-device-updates>Aggiornamenti</button>';
      const names={on:'Accendi',off:'Spegni',execute:'Esegui',open:'Apri',close:'Chiudi',stop:'Stop',lock:'Blocca',unlock:'Sblocca'};
      const buttons=(row.capabilities||[]).filter(action=>names[action]).map(action=>`<button type="button" class="btn secondary" data-admin-command="${key}" data-command="${action}" ${disabled}>${names[action]}</button>`).join('');
      const level=row.domain==='light'&&row.capabilities?.includes('level')?input('<input name="value" aria-label="Luminosità percentuale" type="number" min="0" max="100" required>','level'):'';
      const position=row.domain==='cover'&&row.capabilities?.includes('position')?input('<input name="value" aria-label="Posizione percentuale" type="number" min="0" max="100" required>','position'):'';
      const temperature=row.domain==='climate'?input(`<input name="value" aria-label="Temperatura" type="number" min="${esc(a.min_temp)}" max="${esc(a.max_temp)}" step="any" value="${esc(a.temperature)}" required ${disabled}>`,'temperature'):'';
      return `<div class="mqToolbar">${buttons}</div>${level}${position}${temperature}`;
    }
    async function open(id) {
      detail=await api('/devices/'+encodeURIComponent(id));current=id;
      const d=detail.device;
      host.innerHTML=`<div class="mqToolbar"><h3>${esc(d.name_by_user||d.name||d.id)}</h3><button type="button" class="btn secondary" data-physical-close>Chiudi dispositivo</button><button type="button" class="btn secondary" data-debug-device="${esc(d.id)}">Topic e diagnostica MQTT</button></div><p class="mqMuted">${esc(d.manufacturer||'')} ${esc(d.model||'')} · ${detail.entities.length} entità MQTT</p><div data-physical-sections>${[['Sensori e comandi',null],['Configurazione','config'],['Diagnostica','diagnostic']].map(([title,category])=>{
        const rows=detail.entities.filter(r=>(r.entity_category||null)===category||(category===null&&!['config','diagnostic'].includes(r.entity_category)));
        return rows.length?`<section class="mqBox"><h3>${title}</h3><div class="mqScroll"><table><thead><tr><th>Entità</th><th>Stato / configurazione</th><th>Icona e nome</th></tr></thead><tbody>${rows.map(r=>`<tr data-physical-row="${esc(r.device_id)}"><td><b>${esc(r.name)}</b><div class="mqMuted">${esc(r.entity_id)}</div>${r.disabled_by?'<div class="mqWarn">Disabilitata</div>':''}</td><td><span data-live-state>${esc(stateText(r))}</span><small data-live-availability>${r.available?'':' · Non disponibile'}</small>${controls(r)}</td><td><button type="button" class="btn secondary" data-member-edit="${esc(r.device_id)}">Icona e nome</button></td></tr>`).join('')}</tbody></table></div></section>`:'';
      }).join('')}</div><p class="mqMuted">I comandi amministrativi agiscono subito sul dispositivo. Esposizione, posizione e schede multiple si gestiscono in Dispositivi e presentazione.</p>`;
      host.hidden=false;panel.querySelector('[data-editor]').hidden=true;host.scrollIntoView({behavior:'smooth',block:'start'});
    }
    async function execute(key, action, value, button) {
      const row=detail.entities.find(r=>r.device_id===key);
      if(!row||!confirm(`Applicare ${action}${value==null?'':' = '+value} a ${row.name}? Il comando viene inviato al dispositivo.`))return;
      if(button)button.disabled=true;
      try{await api('/entities/'+encodeURIComponent(key)+'/command','POST',{action,value});status('Comando accettato; attendo lo stato restituito dal dispositivo');}
      finally{if(button)button.disabled=false;}
    }
    host.addEventListener('submit',event=>{
      if(!event.target.hasAttribute('data-entity-command'))return;
      event.preventDefault();event.stopPropagation();const form=event.target;
      execute(form.dataset.entityCommand,form.dataset.command,new FormData(form).get('value'),event.submitter).catch(e=>status(e.message,true));
    });
    host.addEventListener('click',event=>{
      const b=event.target.closest('button');if(!b)return;
      (async()=>{
        if(b.hasAttribute('data-physical-close')){host.hidden=true;current='';panel.querySelector('[data-editor]').hidden=true;}
        if(b.dataset.memberEdit)return editEntity(b.dataset.memberEdit);
        if(b.hasAttribute('data-device-updates')){const box=panel.querySelector('[data-updates]');box.open=true;box.scrollIntoView({behavior:'smooth'});}
        if(b.dataset.adminCommand)return execute(b.dataset.adminCommand,b.dataset.command,null,b);
      })().catch(e=>status(e.message,true));
    });
    setInterval(async()=>{
      if(!current||host.hidden||document.hidden||panel.closest('[data-page]').hidden||polling)return;
      polling=true;const id=current;
      try{const fresh=await api('/devices/'+encodeURIComponent(id));if(id!==current)return;detail.entities=fresh.entities;
        for(const row of fresh.entities){const node=[...host.querySelectorAll('[data-physical-row]')].find(el=>el.dataset.physicalRow===row.device_id);if(node){node.querySelector('[data-live-state]').textContent=stateText(row);node.querySelector('[data-live-availability]').textContent=row.available?'':' · Non disponibile';}}
      }catch(e){status(e.message,true);}finally{polling=false;}
    },5000);
    return {open,isOpen:()=>!host.hidden};
  };
})();
