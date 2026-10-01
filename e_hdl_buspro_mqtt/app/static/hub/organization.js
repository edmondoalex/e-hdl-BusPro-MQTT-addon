(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug = value => String(value || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const apiUrl = path => new URL(path, window.location.href).toString();
  async function json(path, options) {
    const response = await fetch(apiUrl(path), options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }
  function option(rows, selected, empty) {
    return `<option value="">${esc(empty)}</option>` + rows.map(row => `<option value="${esc(row.id)}"${row.id === selected ? ' selected' : ''}>${esc(row.name)}</option>`).join('');
  }
  const presentationCategories = ['lights','extra','covers','comfort','sensors','security','scenarios'];
  function categoryOptions(selected) {
    const active = new Set(selected || []);
    return presentationCategories.map(value => `<option value="${value}"${active.has(value) ? ' selected' : ''}>${value}</option>`).join('');
  }
  function multiOptions(rows, selected) {
    const active = new Set(selected || []);
    return rows.map(row => `<option value="${esc(row.id)}"${active.has(row.id) ? ' selected' : ''}>${esc(row.name)}</option>`).join('');
  }
  function start() {
    const page = document.querySelector('.adminPage[data-page="rooms"]');
    if (!page || document.getElementById('globalOrganization')) return;
    const panel = document.createElement('section');
    panel.id = 'globalOrganization';
    panel.className = 'adminMovedPanel';
    panel.innerHTML = `
      <style>
        #globalOrganization .orgToolbar{display:grid;grid-template-columns:repeat(3,minmax(190px,1fr));gap:12px;margin:14px 0}
        #globalOrganization .orgBox{padding:12px;border:1px solid var(--border);border-radius:12px;background:rgba(0,0,0,.12)}
        #globalOrganization .orgBox input,#globalOrganization select{width:100%;margin-top:7px}
        #globalOrganization .orgTable{width:100%;border-collapse:collapse;margin-top:12px}
        #globalOrganization .orgTable th,#globalOrganization .orgTable td{padding:9px 7px;border-bottom:1px solid var(--border);text-align:left;vertical-align:middle}
        #globalOrganization .orgTable select,#globalOrganization .orgTable input{min-width:130px}
        #globalOrganization .orgSource{font-size:11px;text-transform:uppercase;color:var(--muted)}
        #globalOrganization .orgOrphan{opacity:.55}
        @media(max-width:850px){#globalOrganization .orgToolbar{grid-template-columns:1fr}.orgTable{display:block;overflow-x:auto}}
      </style>
      <h2>Organizzazione globale multi-bus</h2>
      <p class="muted">Piani, stanze, gruppi, categorie/pagine, ordine, visibilità e icone condivisi da HDL BusPro, Ksenia e driver futuri. Le associazioni usano identificativi stabili e restano conservate quando un dispositivo è offline.</p>
      <div class="orgToolbar">
        <div class="orgBox"><b>Nuovo piano</b><input id="orgFloorName" placeholder="Es. Piano terra"><button class="btn secondary small" id="orgAddFloor">Aggiungi</button></div>
        <div class="orgBox"><b>Nuova stanza</b><input id="orgRoomName" placeholder="Es. Cucina"><select id="orgRoomFloor"></select><button class="btn secondary small" id="orgAddRoom">Aggiungi</button></div>
        <div class="orgBox"><b>Nuovo gruppo</b><input id="orgGroupName" placeholder="Es. Illuminazione esterna"><button class="btn secondary small" id="orgAddGroup">Aggiungi</button></div>
      </div>
      <div class="flex"><button class="btn secondary" id="orgReload">Aggiorna cataloghi</button><span id="orgMessage" class="muted"></span></div>
      <div id="orgDevices"></div>`;
    page.prepend(panel);
    let model = null;
    const message = text => { document.getElementById('orgMessage').textContent = text; };
    async function load() {
      message('Caricamento…');
      try { model = await json('api/organization'); render(); message(''); }
      catch (error) { message(error.message); }
    }
    function render() {
      const floors = model.floors || [], rooms = model.rooms || [], groups = model.groups || [];
      document.getElementById('orgRoomFloor').innerHTML = option(floors, '', 'Seleziona piano');
      const rows = Object.entries(model.devices || {}).sort((a,b) => String(a[1].name).localeCompare(String(b[1].name))).map(([key, device]) => {
        const [source, ...idParts] = key.split(':');
        const roomsForFloor = rooms.filter(room => !device.floor_id || room.floor_id === device.floor_id);
        return `<tr class="${device.orphaned ? 'orgOrphan' : ''}" data-source="${esc(source)}" data-id="${esc(idParts.join(':'))}">
          <td><b>${esc(device.name || device.device_id)}</b><div class="orgSource">${esc(source)} · ${esc(device.device_class)}${device.orphaned ? ' · non presente' : ''}</div></td>
          <td><select data-field="floor_id">${option(floors, device.floor_id, 'Nessun piano')}</select></td>
          <td><select data-field="room_id">${option(roomsForFloor, device.room_id, 'Nessuna stanza')}</select></td>
          <td><select data-field="group_ids" multiple size="3">${multiOptions(groups, device.group_ids)}</select></td>
          <td><select data-field="categories" multiple size="3">${categoryOptions(device.categories)}</select></td>
          <td><input data-field="order" type="number" min="0" value="${esc(Object.values(device.orders || {})[0] || 0)}"></td>
          <td><label><input data-field="visible" type="checkbox"${device.visible !== false ? ' checked' : ''}> Visibile</label><br><label><input data-field="favorite" type="checkbox"${device.favorite ? ' checked' : ''}> Preferito</label><br><label><input data-field="shortcut" type="checkbox"${device.shortcut ? ' checked' : ''}> Scorciatoia</label></td>
          <td><input data-field="icon_override" value="${esc(device.icon_override || '')}" placeholder="${esc(device.icon_auto || 'mdi:devices')}"></td>
          <td><button class="btn secondary small" data-save>Salva</button></td></tr>`;
      }).join('');
      document.getElementById('orgDevices').innerHTML = `<table class="orgTable"><thead><tr><th>Dispositivo</th><th>Piano</th><th>Stanza</th><th>Gruppo</th><th>Categorie / pagine</th><th>Ordine</th><th>Presentazione</th><th>Icona MDI</th><th></th></tr></thead><tbody>${rows || '<tr><td colspan="9">Nessun dispositivo disponibile</td></tr>'}</tbody></table>`;
    }
    async function saveStructure() {
      model = await json('api/organization/structure', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({floors:model.floors, rooms:model.rooms, groups:model.groups})});
      render();
    }
    document.getElementById('orgAddFloor').onclick = async () => { const input=document.getElementById('orgFloorName'), name=input.value.trim(); if(!name)return; model.floors.push({id:`floor-${slug(name)}`,name}); await saveStructure(); input.value=''; };
    document.getElementById('orgAddRoom').onclick = async () => { const input=document.getElementById('orgRoomName'), name=input.value.trim(), floor_id=document.getElementById('orgRoomFloor').value; if(!name||!floor_id)return message('Seleziona il piano'); model.rooms.push({id:`room-${slug(name)}`,name,floor_id}); await saveStructure(); input.value=''; };
    document.getElementById('orgAddGroup').onclick = async () => { const input=document.getElementById('orgGroupName'), name=input.value.trim(); if(!name)return; model.groups.push({id:`group-${slug(name)}`,name}); await saveStructure(); input.value=''; };
    document.getElementById('orgReload').onclick = load;
    panel.addEventListener('change', event => { if(event.target.dataset.field !== 'floor_id')return; const row=event.target.closest('tr'), room=row.querySelector('[data-field="room_id"]'), rooms=(model.rooms||[]).filter(x=>!event.target.value||x.floor_id===event.target.value); room.innerHTML=option(rooms,'','Nessuna stanza'); });
    panel.addEventListener('click', async event => {
      const button=event.target.closest('[data-save]'); if(!button)return;
      const row=button.closest('tr'), get=field=>row.querySelector(`[data-field="${field}"]`).value;
      try {
        const categories = Array.from(row.querySelector('[data-field="categories"]').selectedOptions).map(x => x.value);
        if (!categories.length) throw new Error('Seleziona almeno una categoria');
        const order = Number(get('order')) || 0, orders = Object.fromEntries(categories.map(category => [category, order]));
        const group_ids = Array.from(row.querySelector('[data-field="group_ids"]').selectedOptions).map(x => x.value);
        await json('api/organization/device',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:row.dataset.source,device_id:row.dataset.id,floor_id:get('floor_id'),room_id:get('room_id'),group_ids,categories,orders,visible:row.querySelector('[data-field="visible"]').checked,favorite:row.querySelector('[data-field="favorite"]').checked,shortcut:row.querySelector('[data-field="shortcut"]').checked,icon_override:get('icon_override').trim()})});
        message('Associazione salvata'); setTimeout(()=>message(''),1500); await load();
      } catch(error){message(error.message);}
    });
    load();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
