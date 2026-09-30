(function(){
  'use strict';
  function url(path){return new URL(path,window.location.href).toString();}
  function current(){const p=location.pathname.replace(/\/$/,'');return p.split('/').pop()||'home';}
  function link(label,path,icon,key,extra){return '<a class="hub-nav-link '+(current()===key?'active ':'')+(extra||'')+'" href="'+url(path)+'"><span class="hub-nav-icon">'+icon+'</span><span>'+label+'</span></a>';}
  function init(){
    if(document.querySelector('.hub-sidebar'))return;
    document.body.classList.add('hub-shell-ready');
    const side=document.createElement('nav');side.className='hub-sidebar';side.setAttribute('aria-label','Navigazione e-Control Hub');
    const tree=(title,icon,content,open)=>'<details class="hub-tree" '+(open?'open':'')+'><summary><span class="hub-nav-icon">'+icon+'</span>'+title+'</summary><div class="hub-tree-items">'+content+'</div></details>';
    const planned=['KNX','BTicino','Tuya','Modbus','DALI'].map(n=>'<div class="hub-driver-head hub-planned" aria-disabled="true"><span>'+n+'</span><span class="hub-badge">PIANIFICATO</span></div>').join('');
    side.innerHTML='<a class="hub-brand" href="'+url('home')+'"><img src="'+url('static/logo.png')+'" alt=""><span><strong>e-Control Hub</strong><span>Gateway multi-bus</span></span></a>'+
      '<div class="hub-nav-title">Navigazione</div>'+link('Home','home','⌂','home')+
      tree('UI generate','▣',link('Home2','home2','•','home2')+link('e-Face','e-face','•','e-face')+link('Luci','lights','•','lights')+link('Cover','covers','•','covers')+link('Extra','extra','•','extra'),true)+
      tree('Dispositivi trasversali','◇',link('Illuminazione','lights','•','lights')+link('Motorizzazioni','covers','•','covers')+link('Serrature','locks','•','locks')+'<div class="hub-tree-note">Clima · Sensori · Energia</div>',false)+
      tree('Scenari globali','✦',link('Scenari multi-bus','scenarios','•','scenarios')+'<div class="hub-tree-note">Trigger · Azioni · Programmazioni</div>',false)+
      tree('Esposizione e organizzazione','↗','<a class="hub-nav-link" href="'+url('./#entities')+'"><span class="hub-nav-icon">•</span><span>Entità da e-Control</span></a><a class="hub-nav-link" href="'+url('./#exposure')+'"><span class="hub-nav-icon">•</span><span>Esposizione UI</span></a><a class="hub-nav-link" href="'+url('./#rooms')+'"><span class="hub-nav-icon">•</span><span>Stanze, piani e gruppi</span></a>',false)+
      '<div class="hub-nav-title">Bus e integrazioni</div>'+tree('HDL BusPro','↯',link('Luci e dimmer','lights','•','lights')+link('Cover','covers','•','covers')+link('Extra e sensori','extra','•','extra')+'<a class="hub-nav-link" href="'+url('./#tools')+'"><span class="hub-nav-icon">•</span><span>Diagnostica e strumenti</span></a>',true)+planned;
    const bar=document.createElement('div');bar.className='hub-mobilebar';bar.innerHTML='<button class="hub-menu-btn" type="button" aria-label="Apri menu" aria-expanded="false">☰</button><span class="hub-mobile-title">e-Control Hub</span>';
    const overlay=document.createElement('div');overlay.className='hub-overlay';
    document.body.prepend(overlay);document.body.prepend(side);document.body.prepend(bar);
    const btn=bar.querySelector('button');function close(){document.body.classList.remove('hub-shell-open');btn.setAttribute('aria-expanded','false');}
    btn.addEventListener('click',()=>{const open=document.body.classList.toggle('hub-shell-open');btn.setAttribute('aria-expanded',String(open));});overlay.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
