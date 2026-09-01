import { execFileSync, spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import net from 'node:net';

const canListen = (port) => new Promise((resolve) => {
  const server = net.createServer();
  server.once('error', () => resolve(false));
  server.once('listening', () => server.close(() => resolve(true)));
  // Bind all local interfaces so IPv4/IPv6 listeners are both detected.
  server.listen(port);
});

let devPort = Number(process.env.TOV1050_DEV_PORT || 5174);
while (!(await canListen(devPort))) devPort += 1;
process.env.TOV1050_DEV_PORT = String(devPort);

const worktreeOutput = execFileSync(
  'git',
  ['worktree', 'list', '--porcelain'],
  { cwd: process.cwd(), encoding: 'utf8' },
);
const canonicalLine = worktreeOutput
  .split(/\r?\n/)
  .find((line) => line.startsWith('worktree '));

if (!canonicalLine) {
  throw new Error('Unable to resolve the canonical Git worktree.');
}

const canonicalRoot = path.resolve(canonicalLine.slice('worktree '.length));
if (process.argv.includes('--print-root')) {
  process.stdout.write(`${canonicalRoot}\n`);
  process.exit(0);
}

const targetScript = process.argv.slice(2).find(
  (argument) => argument !== '--print-root' && !argument.startsWith('-'),
) ?? 'dev:local';

if (path.resolve(process.cwd()) !== canonicalRoot) {
  process.stdout.write(`Starting latest code from ${canonicalRoot}\n`);
}

const npmCli = process.env.npm_execpath;
const npmCommand = npmCli ? process.execPath : (process.platform === 'win32' ? 'npm.cmd' : 'npm');
const npmArguments = npmCli ? [npmCli, 'run', targetScript] : ['run', targetScript];
const child = spawn(npmCommand, npmArguments, {
  cwd: canonicalRoot,
  env: { ...process.env, NODE_USE_SYSTEM_CA: '1', TOV1050_DEV_PORT: String(devPort) },
  stdio: 'inherit',
});

child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
