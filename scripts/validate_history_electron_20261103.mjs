import { runHistoryPostchecks } from './history_postchecks_20261103.mjs';
import { _electron } from '../frontend/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, process.env.HISTORY_VALIDATION_OUTPUT ?? 'outputs/validation-2026-11-03/electron-history');
await fs.mkdir(output, { recursive: true });
const env = { ...process.env, NODE_ENV: 'development', TOV1050_DEV_PORT: '5193',
  NODE_USE_SYSTEM_CA: '1', DB_PATH: path.join(output, 'isolated.db') };
delete env.ELECTRON_RUN_AS_NODE;
const logs = [], evidence = { entry: 'real source Electron + real backend + Vite proxy, no intercepted API', status: 'running' };
const vite = spawn(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), '--strictPort'],
  { cwd: path.join(root, 'frontend'), env, windowsHide: true });
vite.stdout.on('data', data => logs.push(String(data)));
vite.stderr.on('data', data => logs.push(String(data)));
let application, page;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const capture = async name => {
  try { await page.screenshot({ path: path.join(output, name), fullPage: true, timeout: 5000 }); }
  catch (error) { (evidence.screenshot_warnings ??= []).push(String(error)); }
};
try {
  for (let i = 0; i < 120; i++) {
    try { if ((await fetch('http://localhost:5193')).ok) break; } catch {}
    await pause(500);
  }
  application = await _electron.launch({ executablePath: path.join(root, 'node_modules/electron/dist/electron.exe'),
    args: [root, `--user-data-dir=${path.join(output, 'user-data')}`], cwd: root, env, timeout: 90000 });
  application.process().stdout?.on('data', data => logs.push(String(data)));
  application.process().stderr?.on('data', data => logs.push(String(data)));
  for (let i = 0; i < 180; i++) {
    page = application.windows().find(window => !window.isClosed() && window.url().startsWith('http://localhost:5193'));
    if (page) break;
    await pause(500);
  }
  if (!page) throw new Error('Renderer unavailable');
  await application.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().forEach(window => window.webContents.closeDevTools()));
  page.setDefaultTimeout(90000);
  for (let i = 0; i < 180; i++) {
    try { if (await page.evaluate(() => fetch('/api/health').then(response => response.ok))) break; } catch {}
    await pause(500);
  }
  evidence.runtime = await page.evaluate(() => fetch('/api/diagnostics').then(response => response.json()));
  if (path.resolve(evidence.runtime.database_path) !== path.resolve(env.DB_PATH)) throw new Error('Database is not isolated');
  await page.getByRole('button', { name: /History/ }).first().click();
  if (await page.getByRole('button', { name: 'Start New Comparison', exact: true }).count()) {
    await page.getByRole('button', { name: 'Start New Comparison', exact: true }).click();
  }
  // Validate either the raw legacy reports or the median-report file chain.
  const sourceDirectory = path.join(root, process.env.HISTORY_REPORT_SOURCE ?? 'outputs/validation-2026-11-03/raw-integration');
  let sources;
  for (let i = 0; i < 1800; i++) {
    try {
      sources = JSON.parse(await fs.readFile(path.join(sourceDirectory, 'validation.json'), 'utf8')).filter(item => item.report);
      if (sources.length === 2) break;
    } catch {}
    await pause(1000);
  }
  if (sources?.length !== 2) throw new Error('Full raw reports did not finish');
  await page.locator('input[type=file]').nth(0).setInputFiles(sources[0].report);
  await page.locator('input[type=file]').nth(1).setInputFiles(sources[1].report);
  const started = performance.now();
  const submitted = page.waitForResponse(response => response.url().includes('/analyze/compare/jobs?') && response.request().method() === 'POST', { timeout: 120000 });
  await page.getByRole('button', { name: 'Compare', exact: true }).click();
  const response = await submitted;
  evidence.submit_http = response.status();
  evidence.submit_seconds = (performance.now() - started) / 1000;
  evidence.job = await response.json();
  await fs.writeFile(path.join(output, 'active-job.json'), JSON.stringify(evidence.job, null, 2));
  if (response.status() !== 202) throw new Error(JSON.stringify(evidence.job));
  const statusTimes = [];
  for (let i = 0; i < 1800; i++) {
    const tick = performance.now();
    const state = await page.evaluate(url => fetch(url).then(response => response.json()),
      `/api/jobs/${evidence.job.job_id}?client_session_id=${encodeURIComponent(evidence.job.client_session_id)}`);
    statusTimes.push((performance.now() - tick) / 1000);
    if (['ready', 'failed', 'cancelled'].includes(state.status)) { evidence.final_job = state; break; }
    await pause(1000);
  }
  if (evidence.final_job?.status !== 'ready') throw new Error(JSON.stringify(evidence.final_job));
  evidence.total_compare_seconds = (performance.now() - started) / 1000;
  statusTimes.sort((a, b) => a - b);
  evidence.status_p95_seconds = statusTimes[Math.floor(statusTimes.length * .95)];
  await page.getByRole('button', { name: 'Save to DB', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Save to Database' });
  await dialog.getByRole('combobox', { name: 'Line (Sub Tab)' }).click();
  evidence.line_options = await page.getByRole('option').allTextContents();
  if (evidence.line_options.length !== 9) throw new Error('Expected nine parent lines');
  await page.keyboard.press('Escape');
  await capture('nine-line-save-dialog.png');
  const saveResponse = page.waitForResponse(response => response.request().method() === 'POST' && response.url().includes('/database/repeated-records'));
  await dialog.getByRole('button', { name: 'Save', exact: true }).click();
  const saved = await saveResponse;
  evidence.save_http = saved.status();
  evidence.save_result = await saved.json();
  if (!saved.ok()) throw new Error(JSON.stringify(evidence.save_result));
  await capture('history-ready.png');
  evidence.postchecks = await runHistoryPostchecks(evidence.job, env.DB_PATH, path.join(output, 'postchecks'));
  evidence.status = 'passed';
} catch (error) {
  evidence.status = 'failed'; evidence.error = String(error.stack || error);
  if (page) { evidence.body = await page.locator('body').innerText().catch(() => 'unavailable');
    await page.screenshot({ path: path.join(output, 'failure.png'), timeout: 5000 }).catch(() => {}); }
  throw error;
} finally {
  await fs.writeFile(path.join(output, 'validation.json'), JSON.stringify(evidence, null, 2));
  await fs.writeFile(path.join(output, 'process.log'), logs.join('\n'));
  if (application) await application.close();
  vite.kill();
}
