// Exercise the packaged Electron UI and its bundled backend without API mocks.
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const portable = path.resolve(process.argv[2]);
const output = path.join(root, 'outputs/release-2026-11-06/portable-smoke');
await fs.mkdir(output, { recursive: true });
const base = 'http://127.0.0.1:8000';
const debuggerPort = 9337;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const request = async (url, options = {}) => {
  const { timeoutMs = 5000, ...fetchOptions } = options;
  const response = await fetch(url, { ...fetchOptions, signal: AbortSignal.timeout(timeoutMs) });
  if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
  return response.json();
};
try {
  await request(`${base}/api/health`);
  throw new Error('Port 8000 is already in use; stop before testing the bundled backend.');
} catch (error) {
  if (String(error).includes('already in use')) throw error;
}
const env = { ...process.env };
for (const key of ['NODE_ENV', 'NODE_OPTIONS', 'ELECTRON_RUN_AS_NODE', 'CONFIG_PATH', 'DB_PATH', 'PYTHONPATH']) delete env[key];
const application = spawn(path.join(portable, 'TOV1050 Analyzer.exe'),
  [`--remote-debugging-port=${debuggerPort}`, `--user-data-dir=${path.join(output, 'user-data')}`],
  { cwd: portable, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
const logs = [];
application.stdout.on('data', chunk => logs.push(String(chunk)));
application.stderr.on('data', chunk => logs.push(String(chunk)));
const evidence = { status: 'running', executable: path.join(portable, 'TOV1050 Analyzer.exe'), pid: application.pid };
let socket;
try {
  let health;
  for (let i = 0; i < 180; i++) {
    try { health = await request(`${base}/api/health`); break; } catch {}
    if (application.exitCode !== null) throw new Error(`Portable exited: ${application.exitCode}`);
    await sleep(1000);
  }
  if (health?.version !== '2.0.1') throw new Error(`Unexpected health: ${JSON.stringify(health)}`);
  evidence.health = health;
  const diagnostics = await request(`${base}/api/diagnostics`, { timeoutMs: 120000 });
  if (path.resolve(diagnostics.config_directory) !== path.join(portable, 'resources/config')) throw new Error('Wrong config directory');
  if (path.resolve(diagnostics.database_path) !== path.join(portable, 'data/analysis.db')) throw new Error('Wrong database path');
  evidence.diagnostics = diagnostics;
  let target;
  for (let i = 0; i < 90; i++) {
    try { target = (await request(`http://127.0.0.1:${debuggerPort}/json`)).find(item => item.type === 'page' && item.url.startsWith('file:')); } catch {}
    if (target) break;
    await sleep(1000);
  }
  if (!target) throw new Error('Packaged renderer unavailable');
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let nextId = 0;
  const pending = new Map();
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    const entry = pending.get(message.id);
    if (!entry) return;
    clearTimeout(entry.timer); pending.delete(message.id);
    if (message.error) entry.reject(new Error(JSON.stringify(message.error))); else entry.resolve(message.result);
  };
  const cdp = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 30000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const result = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const body = () => evaluate('document.body.innerText');
  const click = async label => {
    const clicked = await evaluate(`(() => { const b = [...document.querySelectorAll('button,[role="tab"]')].find(x => x.textContent.trim() === ${JSON.stringify(label)} || x.getAttribute('aria-label') === ${JSON.stringify(label)}); if (!b) return false; b.click(); return true; })()`);
    if (!clicked) throw new Error(`Button not found: ${label}`);
    await sleep(700);
  };
  // Re-enter About after backend readiness so diagnostics are fetched afresh.
  await click('Generate');
  await click('About');
  for (let i = 0; i < 60; i++) {
    if ((await body()).includes('Wide Excel') || (await body()).includes('Metadata 格式、區間與設定路徑')) break;
    await sleep(1000);
  }
  const about = await body();
  for (const text of ['Metadata 格式、區間與設定路徑', 'Interval Closed', 'Landmark FromM', 'resources\\config', '9.1']) {
    if (!about.includes(text)) throw new Error(`About missing: ${text}`);
  }
  evidence.about = 'wide format, interval rules and config paths visible';
  await evaluate("document.getElementById('operator-metadata').scrollIntoView()");
  await sleep(400);
  await fs.writeFile(path.join(output, 'about.png'), Buffer.from((await cdp('Page.captureScreenshot', { format: 'png' })).data, 'base64'));
  await click('開發者參考');
  for (let i = 0; i < 30 && !(await body()).includes(diagnostics.config_directory); i++) await sleep(1000);
  if (!(await body()).includes(diagnostics.config_directory)) throw new Error('Diagnostics path not shown in UI');
  evidence.developer_diagnostics = 'actual packaged config path visible';
  await click('Generate');
  await click('Logic');
  const exceptionLogic = await body();
  for (const text of ['Metadata 格式與補值規則', 'Landmark FromM', '完整清洗後 raw', '共用門檻絕對值']) {
    if (!exceptionLogic.includes(text)) throw new Error(`Exception Logic missing: ${text}`);
  }
  evidence.exception_logic = 'wide format and full raw detection descriptions visible';
  await click('了解 (Understood)');
  await click('History');
  await click('Logic');
  const historyLogic = await body();
  for (const text of ['輸入報表與 Metadata', '中位實測樣本', '不以目前 config 重新補算舊報表']) {
    if (!historyLogic.includes(text)) throw new Error(`History Logic missing: ${text}`);
  }
  evidence.history_logic = 'median report chain and preserved metadata descriptions visible';
  evidence.renderer_url = target.url;
  evidence.status = 'passed';
} catch (error) {
  evidence.status = 'failed'; evidence.error = String(error); process.exitCode = 1;
} finally {
  socket?.close();
  // Terminate only the process tree created above; this never touches other apps.
  if (application.pid && application.exitCode === null) {
    try { execFileSync('taskkill.exe', ['/PID', String(application.pid), '/T', '/F'], { windowsHide: true, stdio: 'pipe' }); } catch {}
  }
  await fs.writeFile(path.join(output, 'console.log'), logs.join(''));
  await fs.writeFile(path.join(output, 'result.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
}
