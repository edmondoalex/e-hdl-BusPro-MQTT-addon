(function(){
  'use strict';
  function url(path){return new URL(path,window.location.href).toString();}
  function current(){const p=location.pathname.replace(/\/$/,'');return p.split('/').pop()||'home';}
  function mdi(name){const asset=url('api/icons/mdi/'+name+'.svg');return '<span class="hub-nav-icon hub-mdi" style="-webkit-mask-image:url(\''+asset+'\');mask-image:url(\''+asset+'\')" aria-hidden="true"></span>';}
  function navIcon(icon){if(icon==='')return '';return icon&&icon.startsWith('mdi:')?mdi(icon.slice(4)):'<span class="hub-nav-icon">'+(icon||'•')+'</span>';}
  function busBrand(label,file){return '<span class="hub-bus-name"><span class="hub-bus-mark"><img src="'+url('static/hub/brands/'+file)+'" alt=""></span><span>'+label+'</span></span>';}
  function link(label,path,icon,key,extra){return '<a class="hub-nav-link '+(current()===key?'active ':'')+(extra||'')+'" href="'+url(path)+'">'+navIcon(icon)+'<span>'+label+'</span></a>';}
  function adminUrl(view){return url('index.html')+'#'+view;}
  function init(){
    if(document.querySelector('.hub-sidebar'))return;
    document.body.classList.add('hub-shell-ready');
    const side=document.createElement('nav');side.className='hub-sidebar';side.setAttribute('aria-label','Navigazione e-Control Hub');
    const tree=(title,icon,content,open)=>'<details class="hub-tree" '+(open?'open':'')+'><summary>'+navIcon(icon)+title+'</summary><div class="hub-tree-items">'+content+'</div></details>';
    const planned=[['KNX','knx.png','PIANIFICATO'],['BTicino','bticino.png','PIANIFICATO'],['Tuya','tuya.png','PIANIFICATO'],['Modbus','modbus.png','PIANIFICATO'],['DALI','dali.png','PIANIFICATO']].map(([n,file,status])=>'<div class="hub-driver-head hub-planned" aria-disabled="true">'+busBrand(n,file)+'<span class="hub-badge">'+status+'</span></div>').join('');
    const adminLink=(label,view,icon)=>'<a class="hub-nav-link" href="'+adminUrl(view)+'">'+navIcon(icon||'•')+'<span>'+label+'</span></a>';
    const integrationLink=(label,view,icon,status)=>'<a class="hub-driver-head hub-integration-link" href="'+adminUrl(view)+'">'+navIcon(icon)+'<span class="hub-integration-name">'+label+'</span><span class="hub-badge">'+status+'</span></a>';
    const kseniaLink=(label,section,icon)=>'<a class="hub-nav-link" href="'+url('ksenia')+(section?'#'+section:'')+'">'+navIcon(icon)+'<span>'+label+'</span></a>';
    side.innerHTML='<a class="hub-brand" href="'+url('home')+'"><img src="'+url('static/logo.png')+'" alt=""><span><strong>e-Control Hub</strong><small class="hub-version" id="hubVersion">v…</small><span>Amministrazione multi-bus</span></span></a>'+
      '<div class="hub-nav-title">Amministrazione</div>'+link('Home','home','mdi:home-analytics','home')+
      tree('Dispositivi trasversali','mdi:application-outline',link('Illuminazione','lights','mdi:lightbulb-group-outline','lights')+link('Motorizzazioni','covers','mdi:window-shutter-cog','covers')+link('Serrature','locks','mdi:lock-smart','locks')+'<div class="hub-tree-note">Clima · Sensori · Sicurezza · Energia</div>',false)+
      tree('Scenari e automazioni','mdi:vector-arrange-above',link('Scenari multi-bus','scenarios','mdi:creation','scenarios')+adminLink('Configurazione e trigger','scenarios','mdi:source-branch'),false)+
      tree('Esposizione verso altre UI','mdi:cookie-cog-outline',adminLink('Configurazione esposizione','exposure','mdi:share-variant-outline')+link('Home2','home2','mdi:home-automation','home2')+link('e-Face','e-face','mdi:tablet-dashboard','e-face')+link('Luci','lights','mdi:lightbulb-group','lights')+link('Cover','covers','mdi:window-shutter','covers')+link('Extra','extra','mdi:shape-outline','extra'),false)+
      tree('Organizzazione globale','mdi:application-braces',adminLink('Azioni Home','organization','mdi:gesture-tap-button')+adminLink('Stanze, piani e gruppi · JSON','rooms','mdi:floor-plan'),false)+
      '<div class="hub-nav-title">Bus e integrazioni</div>'+tree(busBrand('HDL BusPro','hdl.png'),'',adminLink('Panoramica e dispositivi','devices','mdi:view-dashboard-outline')+link('Luci e dimmer','lights','mdi:lightbulb-on-outline','lights')+link('Cover','covers','mdi:window-shutter','covers')+link('Extra e sensori','extra','mdi:access-point','extra')+adminLink('Diagnostica HDL','tools','mdi:pulse'),true)+tree(busBrand('Ksenia','ksenia.png'),'',kseniaLink('Panoramica','','mdi:view-dashboard-outline')+kseniaLink('Uscite e luci','light','mdi:lightbulb-on-outline')+kseniaLink('Cover e varchi','cover','mdi:window-shutter')+kseniaLink('Sensori ambientali','sensor','mdi:access-point')+kseniaLink('Termostati','climate','mdi:home-automation')+kseniaLink('Scenari Smart Home','scene','mdi:creation')+kseniaLink('Diagnostica','diagnostics','mdi:pulse'),false)+integrationLink('Home Assistant','entities','mdi:home-assistant','ATTIVO')+planned+
      '<div class="hub-nav-title">Sistema</div>'+adminLink('Manutenzione globale','maintenance','mdi:pin-outline')+adminLink('Strumenti','tools','mdi:tools')+adminLink('Info','info','mdi:information-variant');
    const bar=document.createElement('div');bar.className='hub-mobilebar';bar.innerHTML='<button class="hub-menu-btn" type="button" aria-label="Apri menu" aria-expanded="false">☰</button><span class="hub-mobile-title">e-Control Hub</span>';
    const overlay=document.createElement('div');overlay.className='hub-overlay';
    document.body.prepend(overlay);document.body.prepend(side);document.body.prepend(bar);
    fetch(url('api/meta')).then(r=>r.ok?r.json():Promise.reject()).then(meta=>{const el=document.getElementById('hubVersion');if(el&&meta.version)el.textContent='v'+meta.version;}).catch(()=>{});
    const treeKey='econtrol.hub.tree.v1';let saved={};try{saved=JSON.parse(localStorage.getItem(treeKey)||'{}')||{};}catch(e){}
    side.querySelectorAll('.hub-tree').forEach((node,index)=>{const key=(node.querySelector(':scope>summary')?.textContent||String(index)).trim();const active=[...node.querySelectorAll('a')].some(a=>a.href===location.href);if(active)node.open=true;else if(Object.prototype.hasOwnProperty.call(saved,key))node.open=!!saved[key];node.addEventListener('toggle',()=>{saved[key]=node.open;try{localStorage.setItem(treeKey,JSON.stringify(saved));}catch(e){}});});
    const btn=bar.querySelector('button');function close(){document.body.classList.remove('hub-shell-open');btn.setAttribute('aria-expanded','false');}
    btn.addEventListener('click',()=>{const open=document.body.classList.toggle('hub-shell-open');btn.setAttribute('aria-expanded',String(open));});overlay.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
    side.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();close();window.location.assign(a.href);});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
