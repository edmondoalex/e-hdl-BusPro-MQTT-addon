(() => {
  'use strict';
  const iconName = value => {
    const raw=String(value||'').trim();
    return raw.startsWith('mdi:') ? raw.slice(4) : '';
  };
  const iconUrl = value => {
    const name=iconName(value);
    return name ? new URL(`api/icons/mdi/${encodeURIComponent(name)}.svg`,window.location.href).toString() : '';
  };
  function ensureStyle(){
    if(document.getElementById('econtrolIconPreviewStyle'))return;
    const style=document.createElement('style');style.id='econtrolIconPreviewStyle';
    style.textContent='.econtrolIconPreview{display:inline-flex;align-items:center;gap:8px;margin-top:7px;color:var(--muted);font-size:12px}.econtrolIconPreviewBox{display:grid;place-items:center;width:38px;height:38px;border:1px solid var(--line,var(--border));border-radius:10px;background:rgba(255,255,255,.04)}.econtrolIconPreviewBox img{width:25px;height:25px;filter:brightness(0) saturate(100%) invert(87%) sepia(17%) saturate(1345%) hue-rotate(139deg) brightness(93%)}.econtrolIconPreview.invalid .econtrolIconPreviewBox{border-color:var(--danger,#ff596f)}';
    document.head.appendChild(style);
  }
  function update(preview,value){
    const url=iconUrl(value),img=preview.querySelector('img'),text=preview.querySelector(':scope > span:last-child');
    preview.classList.remove('invalid');
    preview.dataset.iconPreviewCurrent=String(value||'');
    if(!url){img.removeAttribute('src');img.hidden=true;text.textContent='Icona automatica';return;}
    img.hidden=false;img.src=url;text.textContent=String(value).trim();
    img.onerror=()=>{preview.classList.add('invalid');text.textContent='Icona non trovata';};
    img.onload=()=>preview.classList.remove('invalid');
  }
  function attachInput(input){
    if(input.dataset.iconPreviewAttached==='1'||input.type==='file')return;
    input.dataset.iconPreviewAttached='1';
    const preview=document.createElement('span');preview.className='econtrolIconPreview';preview.innerHTML='<span class="econtrolIconPreviewBox"><img alt="Anteprima icona"></span><span></span>';
    input.insertAdjacentElement('afterend',preview);
    preview._iconInput=input;
    const refresh=()=>update(preview,input.value||'');input.addEventListener('input',refresh);input.addEventListener('change',refresh);refresh();
  }
  function scan(root=document){
    ensureStyle();
    root.querySelectorAll('input[id*="icon" i],input[name*="icon" i]').forEach(attachInput);
    root.querySelectorAll('[data-icon-preview-value]').forEach(node=>{
      if(node.dataset.iconPreviewReady==='1')return;node.dataset.iconPreviewReady='1';node.classList.add('econtrolIconPreview');node.innerHTML='<span class="econtrolIconPreviewBox"><img alt="Anteprima icona"></span><span></span>';update(node,node.dataset.iconPreviewValue);
    });
  }
  const start=()=>{scan();new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{if(node.nodeType===1)scan(node);}))).observe(document.body,{childList:true,subtree:true});setInterval(()=>document.querySelectorAll('.econtrolIconPreview').forEach(preview=>{const input=preview._iconInput;if(input&&preview.dataset.iconPreviewCurrent!==String(input.value||''))update(preview,input.value||'');}),300);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
