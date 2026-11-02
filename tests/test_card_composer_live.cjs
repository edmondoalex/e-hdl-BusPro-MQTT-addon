/* Explicit --save-existing only re-saves an existing group. Never commands devices. */
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const base=process.argv[2],physical=process.argv[3],save=process.argv.includes('--save-existing');
if(!base||!physical)throw Error('Provide BASE_URL (trailing slash), physical ID, optional --save-existing');
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'mqtt-composer-live-'));
const wait=ms=>new Promise(r=>setTimeout(r,ms));let browser;
(async()=>{

  const endpoint=base+'api/integrations/mqtt/devices/'+encodeURIComponent(physical);
  const initial=await fetch(endpoint).then(r=>r.json()), primary=initial.presentation.primary_id;
  assert.equal(initial.presentation.grouped,true);
  const selected=initial.entities.filter(r=>r.enabled);assert.ok(selected.length>=2);
  const policy=await fetch(base+'api/integrations/device-policies').then(r=>r.json());
  browser=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless','--disable-gpu','--no-first-run','--remote-debugging-port=9346',`--user-data-dir=${path.join(directory,'profile')}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
  process.on('exit',()=>browser?.kill());
  let target;for(let i=0;i<100;i++){try{target=await fetch('http://127.0.0.1:9346/json/new?about:blank',{method:'PUT'}).then(r=>r.json());break}catch{await wait(100)}}
  assert.ok(target);const socket=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>socket.addEventListener('open',r,{once:true}));
  const pending=new Map(),errors=[];let seq=0;
  socket.addEventListener('message',m=>{const p=JSON.parse(m.data);if(p.id){const v=pending.get(p.id);pending.delete(p.id);p.error?v?.[1](Error(p.error.message)):v?.[0](p.result)}else if(p.method==='Runtime.exceptionThrown')errors.push(p.params.exceptionDetails.exception?.description||p.params.exceptionDetails.text)});
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,[resolve,reject]);socket.send(JSON.stringify({id,method,params}))});
  const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value};
  const ready=async expression=>{for(let i=0;i<150;i++){if(await evaluate(expression))return;await wait(100)}throw Error('Timeout '+expression+' '+JSON.stringify(errors))};
  const shot=async name=>{const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(directory,name+'.png'),Buffer.from(r.data,'base64'))};
  await call('Runtime.enable');await call('Page.enable');
  await call('Page.addScriptToEvaluateOnNewDocument',{source:'window.confirm=()=>false'});
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});

  await call('Page.navigate',{url:base+'index.html#device_organization'});
  await ready("document.querySelector('#orgDevices [data-compose]')");
  await evaluate("(()=>{const field=document.querySelector('#orgSearch');field.value="+JSON.stringify(primary)+";field.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#orgDevices [data-compose]').click()})()");
  await ready("document.querySelector('[data-card-composer] [data-selected]')");
  assert.equal(await evaluate("document.querySelectorAll('[data-card-composer] [data-selected]:checked').length"),selected.length);
  assert.equal(await evaluate("document.querySelector('[data-primary]').value"),primary);
  assert.ok(await evaluate("location.hash==='#device_organization'"));
  const saveVisible="(()=>{const r=document.querySelector('[data-save-composition]').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})()";
  assert.ok(await evaluate(saveVisible));
  if(save){
    await evaluate("document.querySelector('[data-save-composition]').click()");
    await ready("document.querySelector('[data-result]').textContent.includes('Salvataggio verificato')");
    assert.equal(await evaluate("document.querySelector('[data-result]').classList.contains('error')"),false);
  }
  await shot('composer-desktop');
  await evaluate("document.querySelector('[data-card-composer] [data-close]').click()");
  await evaluate("document.querySelector('#orgDevices [data-compose]').click()");
  await ready("document.querySelector('[data-card-composer] [data-selected]')");
  assert.equal(await evaluate("document.querySelectorAll('[data-selected]:checked').length"),selected.length);
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await wait(250);
  assert.ok(await evaluate("document.querySelector('[data-card-composer]').scrollWidth<=document.querySelector('[data-card-composer]').clientWidth+1"));
  assert.ok(await evaluate(saveVisible));
  await shot('composer-mobile');
  const after=await fetch(endpoint).then(r=>r.json());
  assert.deepEqual(after.entities.map(r=>[r.device_id,r.enabled,r.read_only]),initial.entities.map(r=>[r.device_id,r.enabled,r.read_only]));
  assert.deepEqual(await fetch(base+'api/integrations/device-policies').then(r=>r.json()),policy);
  const snapshot=await fetch(base+'api/user/snapshot').then(r=>r.json());
  const group=snapshot.smart_home.devices.filter(row=>row.presentation_group?.primary_id==='mqtt:'+primary);
  assert.equal(group.length,selected.length);assert.ok(group.every(row=>row.visible));
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({result:'PASS',selected:group.length,saved:save,policiesUnchanged:true,screenshots:directory}));
  socket.close();browser.kill();
})().catch(error=>{console.error(error);browser?.kill();process.exitCode=1});
