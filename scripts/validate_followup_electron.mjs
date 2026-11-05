// Real Electron renderer + real local backend. No intercepted API responses.
import { _electron } from '../frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.resolve(root, 'outputs/followup-electron-2026-10-29');
await fs.mkdir(output, { recursive: true });
const env = { ...process.env, NODE_ENV: 'development', TOV1050_DEV_PORT: '5192',
  DB_PATH: path.join(output, 'isolated-validation.db'), NODE_USE_SYSTEM_CA: '1' };
delete env.ELECTRON_RUN_AS_NODE;
const application = await _electron.launch({
  executablePath: path.join(root, 'node_modules/electron/dist/electron.exe'),
  args: [root, `--user-data-dir=${path.join(output, 'electron-user-data')}`], cwd: root, env, timeout: 90000,
});
const evidence = { entry: 'real source Electron, real backend HTTP multipart upload; no API fixtures', result: 'running' };
let page;
const logs = [];
application.process().stdout?.on('data', data => logs.push(data.toString()));
application.process().stderr?.on('data', data => logs.push(data.toString()));
try {
  await application.firstWindow();
  // Development opens DevTools automatically, whose Page can arrive first.
  // Select the application renderer by its URL before closing DevTools.
  for (let attempt = 0; attempt < 180; attempt++) {
    page = application.windows().find(window => !window.isClosed() && window.url().startsWith('http://localhost:5192'));
    if (page) break;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (!page) throw new Error('Application renderer did not open');
  await application.evaluate(({ BrowserWindow }) => {
    for (const window of BrowserWindow.getAllWindows()) window.webContents.closeDevTools();
  });
  page.setDefaultTimeout(120000);
  page.on('pageerror', error => logs.push(`Renderer error: ${error.message}`));
  await page.getByRole('button', { name: /Stagger/ }).first().click();
  let ready = false;
  for (let attempt = 0; attempt < 120; attempt++) {
    try { ready = await page.evaluate(() => fetch('/api/health').then(response => response.ok)); } catch {}
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (!ready) throw new Error('Backend health did not become ready');
  evidence.runtime = await page.evaluate(() => fetch('/api/diagnostics').then(response => response.json()));
  if (path.resolve(evidence.runtime.database_path) !== path.resolve(env.DB_PATH)) throw new Error('Backend DB is not isolated');
  const workbook = path.join(root, '02 Output Document/AEL/20260603_AEL_UT_MAINLINE_SHR_AWE_Exception_Report_MedianSample.xlsx');
  await page.locator('input[type=file]').first().setInputFiles(workbook);
  const responsePromise = page.waitForResponse(response => response.url().includes('/calculation/stagger') && response.request().method() === 'POST');
  await page.getByRole('button', { name: '開始分析', exact: true }).click();
  const response = await responsePromise;
  evidence.http_status = response.status();
  evidence.response = await response.json();
  await page.getByText('診斷代碼：STAGGER_CONFIG_UNAVAILABLE', { exact: true }).waitFor();
  await page.getByText('診斷詳情', { exact: true }).click();
  evidence.displayed_diagnostic = await page.getByLabel('可複製診斷詳情').inputValue();
  if (evidence.http_status !== 422 || !evidence.displayed_diagnostic.includes('AEL')) throw new Error('Unexpected Stagger diagnostic');
  await page.screenshot({ path: path.join(output, 'stagger-real-electron.png'), fullPage: true });
  evidence.result = 'passed';
} catch (error) {
  evidence.result = 'failed';
  evidence.error = String(error.stack || error);
  if (page) {
    evidence.url = page.url();
    evidence.body = await page.locator('body').innerText({ timeout: 3000 }).catch(() => 'unavailable');
    await page.screenshot({ path: path.join(output, 'failure.png'), timeout: 5000 }).catch(() => {});
  }
  throw error;
} finally {
  await fs.writeFile(path.join(output, 'validation.json'), JSON.stringify(evidence, null, 2));
  await fs.writeFile(path.join(output, 'process.log'), logs.join('\n'));
  await application.close();
}
