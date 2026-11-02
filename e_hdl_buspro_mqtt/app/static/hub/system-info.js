/* Read-only diagnostics. Poll only while Info is visible; do not persist samples. */
(() => {
  function start() {
    const page = document.querySelector('.adminPage[data-page="info"]');
    if (!page) return;
    const panel = document.createElement('section');
    panel.className = 'adminMovedPanel';
    panel.innerHTML = `<div class="flex"><h3>Mini PC · risorse globali</h3><button type="button" class="btn secondary" data-refresh>Aggiorna</button><span class="muted" data-time></span></div>
      <div class="adminFutureGrid" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))">
        <article class="adminFutureCard"><b>CPU totale mini PC</b><span data-cpu-model>—</span><strong data-cpu>—</strong><meter data-cpu-meter min="0" max="100" low="70" high="90" optimum="0" style="width:100%"></meter></article>
        <article class="adminFutureCard"><b>RAM globale mini PC</b><strong data-ram>—</strong><meter data-ram-meter min="0" max="100" low="70" high="90" optimum="0" style="width:100%"></meter></article>
        <article class="adminFutureCard"><b>Disco dati globale</b><strong data-disk>—</strong><meter data-disk-meter min="0" max="100" low="70" high="90" optimum="0" style="width:100%"></meter></article>
        <article class="adminFutureCard"><b>Buffer e-Control</b><span data-buffer>—</span><small class="muted">Trasporto temporaneo, massimo 24 ore / 10.000 eventi. Non è una seconda copia dello storico completo.</small></article>
        <article class="adminFutureCard"><b>Stato host e servizio</b><span data-host-uptime>—</span><span data-service>—</span><small class="muted" data-process></small><small class="muted">Queste misure non vengono archiviate. Aggiornamento ogni 10 secondi solo con Info visibile. In una VM i dati globali si riferiscono alla macchina assegnata a Home Assistant.</small></article>
      </div><p class="muted" data-error role="status"></p>`;
    page.querySelector('.adminPageHead').after(panel);
    const set = (name, text) => { panel.querySelector(`[data-${name}]`).textContent = text; };
    const bytes = value => value == null ? 'non disponibile' : value < 1048576 ? `${(value / 1024).toFixed(1)} KB` : value < 1073741824 ? `${(value / 1048576).toFixed(2)} MB` : `${(value / 1073741824).toFixed(2)} GB`;
    const percent = value => value == null ? 'in attesa del prossimo campione' : `${value.toFixed(1)}%`;
    const meter = (name, value) => { const el=panel.querySelector(`[data-${name}-meter]`);el.hidden=value==null;if(value!=null){el.value=value;el.setAttribute('aria-label',`${name} ${percent(value)}`);} };
    const pressure = value => value == null ? '' : value >= 90 ? ' · SATURAZIONE ALTA' : value >= 70 ? ' · Utilizzo elevato' : ' · Nella norma';
    let loading = false;
    async function refresh() {
      if (loading || page.hidden || document.hidden) return;
      loading = true;set('error', '');
      const button = panel.querySelector('[data-refresh]');button.disabled = true;
      try {
        const r = await fetch(new URL('api/system/resources', location.href), {cache:'no-store'});
        if (!r.ok) throw Error('Risorse non disponibili: verifica accesso amministrativo e collegamento.');
        const d = await r.json();
        set('cpu-model', `${d.cpu.model || 'Processore'} · ${d.cpu.logical_cores ?? '—'} core logici`);
        set('cpu', `${percent(d.cpu.host_percent)}${pressure(d.cpu.host_percent)}`);meter('cpu',d.cpu.host_percent);
        const ramUsed=d.memory.host_total!=null && d.memory.host_available!=null?d.memory.host_total-d.memory.host_available:null;
        const ramPercent=ramUsed!=null && d.memory.host_total?100*ramUsed/d.memory.host_total:null;
        set('ram', `${bytes(ramUsed)} usati / ${bytes(d.memory.host_total)} · ${bytes(d.memory.host_available)} disponibili · ${percent(ramPercent)}${pressure(ramPercent)}`);meter('ram',ramPercent);
        const disk = d.data_filesystem;
        set('disk', disk ? `${bytes(disk.free)} liberi / ${bytes(disk.total)} · occupato ${percent(100 * disk.used / disk.total)}${disk.free < disk.total * .1 ? ' · ATTENZIONE: spazio basso' : ''}` : 'Non disponibile');
        meter('disk',disk?100*disk.used/disk.total:null);
        set('buffer', `${bytes(d.activity_buffer.bytes)} · ${d.activity_buffer.count} eventi · errori ${d.activity_buffer.errors}`);
        set('service', `e-Control ${d.version} · avviato da ${Math.floor(d.uptime_seconds / 3600)} h ${Math.floor(d.uptime_seconds % 3600 / 60)} min`);
        set('host-uptime',d.host_uptime_seconds==null?'Uptime host non disponibile':`Mini PC acceso da ${Math.floor(d.host_uptime_seconds/86400)} giorni ${Math.floor(d.host_uptime_seconds%86400/3600)} h`);
        set('process',`Solo processo e-Control: RAM ${bytes(d.memory.process_rss)}, CPU ${percent(d.cpu.process_percent)} (100% = un core).`);
        set('time', `Aggiornato ${new Date(d.sampled_at * 1000).toLocaleTimeString('it-IT')}`);
      } catch (error) { set('error', error.message); }
      try {
        const r = await fetch(new URL('api/system/integrations', location.href), {cache:'no-store'});
        if (!r.ok) throw Error();
        const d = await r.json(), host = document.getElementById('infoIntegrationCards');
        host.replaceChildren();
        for (const item of d.items) {
          const card=document.createElement('article');card.className='adminFutureCard';
          const name=document.createElement('b');name.textContent=item.name;
          const status=document.createElement('span');status.textContent=item.registered?'Driver registrato':'Sorgente presente nello storico del catalogo';
          const health=item.exported>0?(item.available>=item.exported?'online':item.available>0?'partial':item.unknown>0?'unknown':'offline'):'empty';
          card.dataset.availability=health;
          const colors={online:'#4ee0a4',partial:'#ffd166',offline:'#ff758f',empty:'#a8b4ba',unknown:'#a8b4ba'};
          const badge=document.createElement('span');badge.textContent={online:'● ONLINE',partial:'◐ PARZIALE',offline:'○ NON DISPONIBILI',unknown:'— DISPONIBILITÀ NON NOTA',empty:'— NESSUN DISPOSITIVO ESPORTATO'}[health];
          badge.title='Disponibilità dichiarata dei dispositivi esportati; distinta dalla data del loro ultimo stato';
          badge.style.cssText=`display:block;width:fit-content;font-weight:750;font-size:11px;padding:4px 8px;border-radius:8px;background:#101619;color:${colors[health]};margin:7px 0`;
          if(health!=='empty'){card.style.borderColor=colors[health];card.style.borderLeftWidth='4px';card.style.background=`linear-gradient(120deg,${colors[health]}18,var(--hub-panel,#1c2428) 80%)`;}
          const counts=document.createElement('span');counts.textContent=`${item.detected ?? 'Dato non disponibile:'} rilevati · ${item.exported} esportati in eFace · ${item.visible} visibili`;
          const available=document.createElement('span');available.textContent=`${item.available} / ${item.exported} esportati disponibili · ${item.excluded ?? '—'} esclusi`;
          card.append(name,badge,status,counts,available);
          if(item.stale){const note=document.createElement('small');note.className='muted';note.textContent=`${item.stale} stati non recenti o non ancora ricevuti (non significa disconnessione)`;card.append(note);}
          if(item.unknown){const note=document.createElement('small');note.textContent=`Disponibilità non dichiarata: ${item.unknown}`;card.append(note);}
          if(item.unavailable_devices?.length){const detail=document.createElement('details');const summary=document.createElement('summary');summary.textContent=`Dispositivi non disponibili (${item.unavailable_devices.length})`;detail.append(summary);const list=document.createElement('ul');for(const label of item.unavailable_devices){const row=document.createElement('li');row.textContent=label;list.append(row);}detail.append(list);card.append(detail);}
          host.append(card);
        }
        document.getElementById('infoPlannedIntegrations').textContent=d.planned.join(' · ') || 'Nessuna';
      } catch { set('error','Elenco integrazioni non aggiornato: verifica il collegamento.'); }
      finally { loading = false;button.disabled = false; }
    }
    panel.querySelector('[data-refresh]').onclick = refresh;
    new MutationObserver(refresh).observe(page, {attributes:true, attributeFilter:['hidden']});
    document.addEventListener('visibilitychange', refresh);
    setInterval(refresh, 10000);refresh();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
