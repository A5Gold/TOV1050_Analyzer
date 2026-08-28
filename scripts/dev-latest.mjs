import { execFileSync, spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

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
  env: { ...process.env, NODE_USE_SYSTEM_CA: '1' },
  stdio: 'inherit',
});

child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
