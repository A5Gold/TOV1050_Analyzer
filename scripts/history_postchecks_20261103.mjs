// Call while the existing Electron/backend is still alive and its History job is ready.
// This starts only the short Python post-check client; it never starts a server or exporter.
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs/promises';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export async function runHistoryPostchecks(job, expectedDatabase, outputDirectory,
  baseUrl = 'http://127.0.0.1:8000') {
  if (!job?.job_id || !job?.client_session_id) throw new Error('History job identity is required');
  const output = path.resolve(outputDirectory);
  await fs.mkdir(output, { recursive: true });
  const log = [];
  const child = spawn(path.join(root, 'venv/Scripts/python.exe'), [
    path.join(root, 'scripts/validate_history_postchecks_20261103.py'),
    '--base-url', baseUrl, '--job-id', job.job_id, '--session-id', job.client_session_id,
    '--expected-db', path.resolve(expectedDatabase), '--output-dir', output,
  ], { cwd: root, env: process.env, windowsHide: true });
  child.stdout.on('data', value => log.push(String(value)));
  child.stderr.on('data', value => log.push(String(value)));
  await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', async code => {
      await fs.writeFile(path.join(output, 'process.log'), log.join(''));
      if (code === 0) resolve();
      else reject(new Error('History postchecks failed (' + code + '): ' + log.join('')));
    });
  });
  return JSON.parse(await fs.readFile(path.join(output, 'validation.json'), 'utf8'));
}
