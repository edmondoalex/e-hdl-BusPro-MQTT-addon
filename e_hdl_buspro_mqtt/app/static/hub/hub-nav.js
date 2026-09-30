(function(){
  'use strict';
  function url(path){return new URL(path,window.location.href).toString();}
  function current(){const p=location.pathname.replace(/\/$/,'');return p.split('/').pop()||'home';}
  function link(label,path,icon,key,extra){return '<a class="hub-nav-link '+(current()===key?'active ':'')+(extra||'')+'" href="'+url(path)+'"><span class="hub-nav-icon">'+icon+'</span><span>'+label+'</span></a>';}
  function adminUrl(view){return new URL('.',window.location.href).toString()+'#'+view;}
  function init(){
    if(document.querySelector('.hub-sidebar'))return;
    document.body.classList.add('hub-shell-ready');
    const side=document.createElement('nav');side.className='hub-sidebar';side.setAttribute('aria-label','Navigazione e-Control Hub');
    const tree=(title,icon,content,open)=>'<details class="hub-tree" '+(open?'open':'')+'><summary><span class="hub-nav-icon">'+icon+'</span>'+title+'</summary><div class="hub-tree-items">'+content+'</div></details>';
    const planned=['KNX','BTicino','Tuya','Modbus','DALI'].map(n=>'<div class="hub-driver-head hub-planned" aria-disabled="true"><span>'+n+'</span><span class="hub-badge">PIANIFICATO</span></div>').join('');
    const adminLink=(label,view)=>'<a class="hub-nav-link" href="'+adminUrl(view)+'"><span class="hub-nav-icon">•</span><span>'+label+'</span></a>';
    side.innerHTML='<a class="hub-brand" href="'+url('home')+'"><img src="'+url('static/logo.png')+'" alt=""><span><strong>e-Control Hub</strong><span>Amministrazione multi-bus</span></span></a>'+
      '<div class="hub-nav-title">Amministrazione</div>'+link('Home','home','⌂','home')+
      tree('Dispositivi trasversali','◇',link('Illuminazione','lights','•','lights')+link('Motorizzazioni','covers','•','covers')+link('Serrature','locks','•','locks')+'<div class="hub-tree-note">Clima · Sensori · Sicurezza · Energia</div>',false)+
      tree('Scenari e automazioni','✦',link('Scenari multi-bus','scenarios','•','scenarios')+adminLink('Configurazione e trigger','scenarios'),false)+
      adminLink('Entità da e-Control','entities')+
      tree('Esposizione verso altre UI','↗',adminLink('Configurazione esposizione','exposure')+link('Home2','home2','•','home2')+link('e-Face','e-face','•','e-face')+link('Luci','lights','•','lights')+link('Cover','covers','•','covers')+link('Extra','extra','•','extra'),false)+
      tree('Organizzazione globale','▦',adminLink('Azioni Home','organization')+adminLink('Stanze, piani e gruppi · JSON','rooms'),false)+
      '<div class="hub-nav-title">Bus e integrazioni</div>'+tree('HDL BusPro','↯',adminLink('Panoramica e dispositivi','devices')+link('Luci e dimmer','lights','•','lights')+link('Cover','covers','•','covers')+link('Extra e sensori','extra','•','extra')+adminLink('Diagnostica HDL','tools'),true)+planned+
      '<div class="hub-nav-title">Sistema</div>'+adminLink('Manutenzione globale','maintenance')+adminLink('Strumenti','tools')+adminLink('Info','info');
    const bar=document.createElement('div');bar.className='hub-mobilebar';bar.innerHTML='<button class="hub-menu-btn" type="button" aria-label="Apri menu" aria-expanded="false">☰</button><span class="hub-mobile-title">e-Control Hub</span>';
    const overlay=document.createElement('div');overlay.className='hub-overlay';
    document.body.prepend(overlay);document.body.prepend(side);document.body.prepend(bar);
    const treeKey='econtrol.hub.tree.v1';let saved={};try{saved=JSON.parse(localStorage.getItem(treeKey)||'{}')||{};}catch(e){}
    side.querySelectorAll('.hub-tree').forEach((node,index)=>{const key=(node.querySelector(':scope>summary')?.textContent||String(index)).trim();const active=[...node.querySelectorAll('a')].some(a=>a.href===location.href);if(active)node.open=true;else if(Object.prototype.hasOwnProperty.call(saved,key))node.open=!!saved[key];node.addEventListener('toggle',()=>{saved[key]=node.open;try{localStorage.setItem(treeKey,JSON.stringify(saved));}catch(e){}});});
    const btn=bar.querySelector('button');function close(){document.body.classList.remove('hub-shell-open');btn.setAttribute('aria-expanded','false');}
    btn.addEventListener('click',()=>{const open=document.body.classList.toggle('hub-shell-open');btn.setAttribute('aria-expanded',String(open));});overlay.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
