(function(){
  'use strict';
  function url(path){return new URL(path,window.location.href).toString();}
  function current(){const p=location.pathname.replace(/\/$/,'');return p.split('/').pop()||'home';}
  function link(label,path,icon,key,extra){return '<a class="hub-nav-link '+(current()===key?'active ':'')+(extra||'')+'" href="'+url(path)+'"><span class="hub-nav-icon">'+icon+'</span><span>'+label+'</span></a>';}
  function init(){
    if(document.querySelector('.hub-sidebar'))return;
    document.body.classList.add('hub-shell-ready');
    const side=document.createElement('nav');side.className='hub-sidebar';side.setAttribute('aria-label','Navigazione e-Control Hub');
    side.innerHTML='<a class="hub-brand" href="'+url('home')+'"><img src="'+url('static/logo.png')+'" alt=""><span><strong>e-Control Hub</strong><span>Gateway multi-bus</span></span></a>'+
      '<div class="hub-nav-title">Generale</div>'+link('Home','home','⌂','home')+link('Scenari','scenarios','✦','scenarios')+
      '<div class="hub-nav-title">Dispositivi trasversali</div>'+link('Serrature','locks','▣','locks')+
      '<div class="hub-nav-title">Bus e integrazioni</div><div class="hub-driver"><div class="hub-driver-head"><span class="hub-driver-name"><span class="hub-nav-icon">↯</span>HDL BusPro</span><span class="hub-badge">ATTIVO</span></div><div class="hub-subnav">'+link('Luci','lights','•','lights')+link('Cover','covers','•','covers')+link('Extra','extra','•','extra')+'</div></div>'+
      ['KNX','BTicino','Tuya','Modbus','DALI'].map(n=>'<div class="hub-driver-head hub-planned" aria-disabled="true"><span class="hub-driver-name"><span class="hub-nav-icon">◇</span>'+n+'</span><span class="hub-badge">PIANIFICATO</span></div>').join('');
    const bar=document.createElement('div');bar.className='hub-mobilebar';bar.innerHTML='<button class="hub-menu-btn" type="button" aria-label="Apri menu" aria-expanded="false">☰</button><span class="hub-mobile-title">e-Control Hub</span>';
    const overlay=document.createElement('div');overlay.className='hub-overlay';
    document.body.prepend(overlay);document.body.prepend(side);document.body.prepend(bar);
    const btn=bar.querySelector('button');function close(){document.body.classList.remove('hub-shell-open');btn.setAttribute('aria-expanded','false');}
    btn.addEventListener('click',()=>{const open=document.body.classList.toggle('hub-shell-open');btn.setAttribute('aria-expanded',String(open));});overlay.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
