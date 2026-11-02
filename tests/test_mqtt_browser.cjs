/* Live client smoke. No broker changes, device commands or exposure changes.
   Publishes one non-retained diagnostic message to a unique test topic. */
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {randomUUID}=require('node:crypto');
const base=process.argv[2];if(!base)throw Error('Pass Hub admin base URL');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'econtrol-mqtt-browser-'));
const wait=ms=>new Promise(r=>setTimeout(r,ms));let browser,listenerId,flowId;
const api=async(p='',method='GET',body)=>{
  const r=await fetch(new URL('api/integrations/mqtt'+p,base),{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  const d=await r.json();assert.ok(r.ok,`HTTP ${r.status} ${p}`);return d;
};
(async()=>{
  browser=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless','--disable-gpu','--no-first-run','--remote-debugging-port=9344',`--user-data-dir=${path.join(dir,'profile')}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
  process.on('exit',()=>browser?.kill());
  let target;for(let i=0;i<100;i++){try{target=await fetch('http://127.0.0.1:9344/json/new?about:blank',{method:'PUT'}).then(r=>r.json());break}catch{await wait(100)}}
  assert.ok(target);const socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r=>socket.addEventListener('open',r,{once:true}));
  const pending=new Map(),errors=[];let seq=0;
  socket.addEventListener('message',m=>{const p=JSON.parse(m.data);if(p.id){const v=pending.get(p.id);pending.delete(p.id);p.error?v?.[1](Error(p.error.message)):v?.[0](p.result)}else if(p.method==='Runtime.exceptionThrown')errors.push(p.params.exceptionDetails.text)});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,[resolve,reject]);socket.send(JSON.stringify({id,method,params}))});
  const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value};
  const ready=async e=>{for(let i=0;i<250;i++){if(await evaluate(e))return;await wait(100)}console.error(await evaluate("JSON.stringify({ready:document.readyState,hash:location.hash,status:document.querySelector('#mqttManager [data-status]')?.textContent,entities:document.querySelector('#mqttManager [data-entities]')?.textContent,hidden:document.querySelector('.adminPage[data-page=mqtt]')?.hidden,flow:document.querySelector('#mqttManager [data-flow-box]')?.hidden})"),errors);throw Error('Timeout '+e)};
  await call('Runtime.enable');await call('Page.enable');
  if(process.argv.includes('--preview')){
    socket.addEventListener('message',async m=>{const p=JSON.parse(m.data);if(p.method==='Fetch.requestPaused'){const name=p.params.request.url.includes('/organization.js')?'organization.js':'mqtt.js';await call('Fetch.fulfillRequest',{requestId:p.params.requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/javascript'}],body:fs.readFileSync(path.join(__dirname,'../e_hdl_buspro_mqtt/app/static/hub',name)).toString('base64')});}});
    await call('Fetch.enable',{patterns:[{urlPattern:'*static/hub/organization.js*'},{urlPattern:'*static/hub/mqtt.js*'}]});
  }
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:new URL('index.html#mqtt',base).href});
  await ready("Number(document.querySelector('#mqttManager [data-entities]')?.textContent)>0");
  const model=await api();assert.ok(model.realtime);assert.ok(model.counts.devices>0);
  assert.equal(await evaluate("Number(document.querySelector('#mqttManager [data-exported]').textContent)"),model.counts.exported);
  assert.equal(model.counts.exported,0,'Initial release must not expose MQTT entities automatically');
  assert.ok(model.entities.every(e=>!e.enabled&&e.read_only));
  assert.ok(await evaluate("document.querySelector('#mqttManager [data-list]').querySelectorAll('tbody tr').length<=50"));
  assert.ok(await evaluate("document.querySelector('.hub-sidebar a[href$=\"#mqtt\"]')!==null"));
  assert.equal(await evaluate("document.querySelectorAll('#mqttManager [data-policy=commands]:not(:disabled)').length"),0);
  await evaluate("document.querySelector('#mqttManager [data-view=entities]').click()");
  await evaluate("document.querySelector('#mqttManager [data-filter]').value='duplicates';document.querySelector('#mqttManager [data-filter]').dispatchEvent(new Event('change',{bubbles:true}))");
  if(model.entities.some(e=>e.also_in.length))assert.ok(await evaluate("document.querySelector('#mqttManager [data-list]').textContent.includes('solo avviso')"));
  await evaluate("document.querySelector('#mqttManager [data-view=devices]').click()");
  await ready("document.querySelector('#mqttManager [data-list-title]').textContent==='Dispositivi MQTT'");
  // Read-only physical detail: never select exposure or execute controls here.
  const physical=model.devices.find(d=>/Motion Cantina/i.test(d.name_by_user||d.name||''))||model.devices[0];
  await evaluate(`document.querySelector('#mqttManager [data-search]').value=${JSON.stringify(physical.name_by_user||physical.name||physical.id)};document.querySelector('#mqttManager [data-search]').dispatchEvent(new Event('input',{bubbles:true}))`);
  await ready(`document.querySelector('[data-device="${physical.id}"]')`);
  await evaluate(`document.querySelector('[data-device="${physical.id}"]').click()`);
  await ready("document.querySelector('[data-physical-device] [data-save-physical]')");
  assert.equal(await evaluate("document.querySelector('[data-card-setup]').hidden"),true);
  assert.ok(await evaluate("!document.querySelector('#mqttManager').textContent.includes('HASSIO')"));
  await ready("document.querySelector('.adminPage[data-page=mqtt] .adminPageHead img[alt=MQTT]')?.naturalWidth>0");
  await evaluate("document.querySelector('[data-device-mode=presentation]').click()");
  assert.ok(await evaluate("document.querySelector('[data-card-preview]').textContent.includes('Nessuna scheda')"));
  await evaluate("document.querySelector('[data-device-mode=configuration]').click()");
  const detail=await api('/devices/'+physical.id);
  assert.equal(await evaluate("document.querySelectorAll('[data-physical-row]').length"),detail.entities.length);
  assert.equal(await evaluate("document.querySelectorAll('[data-member-enabled]:checked').length"),0);
  for(const category of ['config','diagnostic'])if(detail.entities.some(e=>e.entity_category===category))assert.ok(await evaluate(`document.querySelector('[data-physical-sections]').textContent.includes('${category==='config'?'Configurazione':'Diagnostica'}')`));
  await evaluate("document.querySelector('[data-physical-device]').scrollIntoView({block:'start'})");
  fs.writeFileSync(path.join(dir,'mqtt-physical-installed.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await evaluate("document.querySelector('[data-physical-close]').click();document.querySelector('#mqttManager [data-search]').value='';document.querySelector('#mqttManager [data-search]').dispatchEvent(new Event('input',{bubbles:true}))");
  await evaluate("document.querySelector('#mqttManager [data-view=entities]').click()");
  if(!process.argv.includes('--layout-only')){
  for(const kind of ['connection','options','device']){
    await evaluate(`document.querySelector('#mqttManager [data-flow=${kind}]').click()`);
    await ready("!document.querySelector('#mqttManager [data-flow-box]').hidden && !!document.querySelector('#mqttManager [data-flow-cancel]')");
    assert.ok(await evaluate("document.querySelectorAll('#mqttManager [data-fields] input,#mqttManager [data-fields] select').length>0"));
    assert.ok(await evaluate("[...document.querySelectorAll('#mqttManager [data-fields] input[type=password]')].every(e=>!e.value)"));
    await evaluate("document.querySelector('#mqttManager [data-flow-cancel]').click()");
    await ready("document.querySelector('#mqttManager [data-flow-box]').hidden");
  }
  await evaluate("document.querySelector('#mqttManager [data-updates]').open=true");
  await ready("document.querySelector('#mqttManager [data-client-version]').textContent.includes('Servizio MQTT')");
  assert.ok(await evaluate("document.querySelector('#mqttManager [data-client-version]').textContent.includes('Broker escluso')"));
  const testTopic='econtrol/diagnostic/client-smoke/'+randomUUID();
  await evaluate(`document.querySelector('#mqttManager [data-listen] [name=topic]').value=${JSON.stringify(testTopic)};document.querySelector('#mqttManager [data-listen]').requestSubmit()`);
  await ready("document.querySelector('#mqttManager [data-listen-status]').textContent.includes('In ascolto')");
  // Keep a second API subscription to verify true end-to-end HA delivery.
  listenerId=(await api('/listen','POST',{topic:testTopic,qos:0})).id;
  // HA's websocket acknowledgement registers a callback, not a broker SUBACK.
  // Its MQTT client batches new subscriptions (initial cooldown 0.5 seconds).
  await wait(1000);
  await api('/publish','POST',{topic:testTopic,payload:'{"client_smoke":"ok"}',qos:0,retain:false});
  await ready("document.querySelector('#mqttManager [data-logs]').textContent.includes('client_smoke')");
  const messages=await api('/listen/'+listenerId);assert.equal(messages.messages.at(-1).payload,'{"client_smoke":"ok"}');
  assert.equal(messages.messages.at(-1).retain,false);
  await api('/listen/'+listenerId,'DELETE');listenerId=null;
  await evaluate("document.querySelector('#mqttManager [data-pause]').click();document.querySelector('#mqttManager [data-clear]').click()");
  assert.equal(await evaluate("document.querySelector('#mqttManager [data-logs]').textContent"),'');
  await evaluate("document.querySelector('#mqttManager [data-stop]').click()");
  await ready("document.querySelector('#mqttManager [data-listen-status]').textContent.includes('fermato')");
  }
  await evaluate("document.querySelector('#mqttManager [data-updates]').open=false;window.scrollTo(0,0)");
  fs.writeFileSync(path.join(dir,'mqtt-desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await wait(300);
  fs.writeFileSync(path.join(dir,'mqtt-mobile.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
  if(!await evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"))console.error(await evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>391&&e.getBoundingClientRect().width>0).slice(0,15).map(e=>({tag:e.tagName,id:e.id,cls:e.className,width:e.getBoundingClientRect().width}))"),dir);
  assert.ok(await evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"),'Mobile page overflows');
  await evaluate("location.hash='device_organization'");
  await ready("document.querySelectorAll('#orgDevices [data-device-row]').length>0");
  assert.ok(await evaluate("document.querySelectorAll('#orgDevices [data-device-row]').length<=50"));
  await evaluate("document.querySelector('#orgSourceFilter').value='mqtt';document.querySelector('#orgSourceFilter').dispatchEvent(new Event('change',{bubbles:true}))");
  assert.ok(await evaluate("[...document.querySelectorAll('#orgDevices [data-device-row]')].every(r=>r.dataset.source==='mqtt')"));
  assert.ok(await evaluate("!document.querySelector('[data-org-next]').disabled"));
  await evaluate("document.querySelector('[data-org-next]').click()");
  assert.ok(await evaluate("document.querySelector('[data-org-pages]').textContent.startsWith('51')"));
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,preview:process.argv.includes('--preview'),counts:model.counts,browserErrors:errors,artifacts:dir,livePublish:process.argv.includes('--layout-only')?'skipped':'unique diagnostic topic, no retain'}));
  await call('Browser.close');socket.close();browser.kill();
})().catch(async e=>{console.error(e);if(listenerId)await api('/listen/'+listenerId,'DELETE').catch(()=>{});if(flowId)await api('/flow/'+flowId,'DELETE').catch(()=>{});browser?.kill();process.exit(1)});
