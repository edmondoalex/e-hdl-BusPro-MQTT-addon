const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { pathToFileURL } = require('node:url');

const indexPath = process.argv[2];
if (!indexPath) throw new Error('Provide the absolute path to static/index.html');
const payloadPath = process.argv[3];

const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'scenario-json-sync-'));
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const debuggingPort = 9300 + (process.pid % 500);
let browser;

(async () => {
  browser = spawn(
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    [
      '--headless',
      '--disable-gpu',
      '--allow-file-access-from-files',
      '--no-first-run',
      `--remote-debugging-port=${debuggingPort}`,
      `--user-data-dir=${path.join(directory, 'profile')}`,
      'about:blank',
    ],
    { windowsHide: true, stdio: 'ignore' },
  );
  process.on('exit', () => browser?.kill());

  let target;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      target = await fetch(`http://127.0.0.1:${debuggingPort}/json/new?about:blank`, { method: 'PUT' }).then((r) => r.json());
      break;
    } catch {
      await wait(100);
    }
  }
  assert.ok(target, 'Edge DevTools endpoint not available');

  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve) => socket.addEventListener('open', resolve, { once: true }));
  const pending = new Map();
  let sequence = 0;
  socket.addEventListener('message', (message) => {
    const packet = JSON.parse(message.data);
    if (!packet.id) return;
    const callbacks = pending.get(packet.id);
    pending.delete(packet.id);
    if (!callbacks) return;
    packet.error ? callbacks[1](new Error(packet.error.message)) : callbacks[0](packet.result);
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    pending.set(id, [resolve, reject]);
    socket.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    }
    return result.result.value;
  };

  await call('Runtime.enable');
  await call('Page.enable');
  await call('Page.navigate', { url: `${pathToFileURL(path.resolve(indexPath)).href}#scenarios_config` });
  let pageReady = false;
  for (let attempt = 0; attempt < 200; attempt += 1) {
    pageReady = await evaluate("document.readyState === 'complete' && !!document.querySelector('#scCfgJson')");
    if (pageReady) break;
    await wait(50);
  }
  assert.equal(pageReady, true, 'admin editor did not finish loading');
  await wait(100);

  const defaultPayload = {
    id: 'scenario-off-test',
    name: 'ALL Castle Light OFF',
    items: [{ subnet_id: 1, device_id: 150, channel: 1, state: 'OFF', brightness: 255 }],
    covers: [],
    combination_targets: [],
    run_enabled: false,
    onoff_enabled: true,
    ha_trigger_enabled: false,
    ha_trigger_id: '',
  };
  const payload = payloadPath
    ? JSON.parse(fs.readFileSync(path.resolve(payloadPath), 'utf8'))
    : defaultPayload;
  const verifiedName = `${payload.name} verified`;
  const result = await evaluate(`(() => {
    const textarea = document.querySelector('#scCfgJson');
    textarea.value = ${JSON.stringify(JSON.stringify(payload))};
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    const importedState = document.querySelector('#scCfgSelected [data-field="state"]')?.value;
    const importedBrightness = document.querySelector('#scCfgSelected [data-field="brightness"]')?.value;
    const name = document.querySelector('#scCfgName');
    name.value = ${JSON.stringify(verifiedName)};
    name.dispatchEvent(new Event('input', { bubbles: true }));
    const serialized = JSON.parse(textarea.value);
    document.querySelector('#btnScCfgValidate').click();
    return {
      importedState,
      importedBrightness,
      state: serialized.items[0].state,
      brightness: serialized.items[0].brightness,
      itemCount: serialized.items.length,
      allOff: serialized.items.every((item) => item.state === 'OFF'),
      allBrightnessNull: serialized.items.every((item) => item.brightness === null),
      name: serialized.name,
      message: document.querySelector('#scCfgMsg').textContent,
    };
  })()`);

  assert.deepEqual(result, {
    importedState: 'OFF',
    importedBrightness: '',
    state: 'OFF',
    brightness: null,
    itemCount: payload.items.length,
    allOff: true,
    allBrightnessNull: true,
    name: verifiedName,
    message: 'JSON valido e applicato',
  });
  console.log(JSON.stringify({ result: 'PASS', state: result.state, brightness: result.brightness }));
  socket.close();
  browser.kill();
})().catch((error) => {
  console.error(error);
  browser?.kill();
  process.exitCode = 1;
});
