import { afterEach, expect, test, vi } from 'vitest';
import apiClient from '../client';
import { waitForJob } from '../analysisJobs';
import { BackgroundJob } from '../../types/api';

vi.mock('../client', () => ({ default: { get: vi.fn() } }));
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });
const job: BackgroundJob = { job_id: 'a', kind: 'analysis', status: 'running', stage: 'reading', elapsed_seconds: 1 };

test('polls the existing job and preserves session ownership', async () => {
  vi.useFakeTimers();
  vi.mocked(apiClient.get).mockResolvedValue({ data: { ...job, status: 'ready' } });
  const update = vi.fn();
  const promise = waitForJob(job, 'tab-a', update);
  await vi.advanceTimersByTimeAsync(1000);
  expect((await promise).status).toBe('ready');
  expect(apiClient.get).toHaveBeenCalledWith('/jobs/a', { params: { client_session_id: 'tab-a' }, timeout: 30_000 });
  expect(update).toHaveBeenCalledTimes(2);
});

test('a terminal error includes the backend reason without polling', async () => {
  await expect(waitForJob({ ...job, status: 'failed', error: '原始資料已過期' }, 'a', vi.fn())).rejects.toThrow('原始資料已過期');
  expect(apiClient.get).not.toHaveBeenCalled();
});

test('ignores a response when its tab was removed during the request', async () => {
  vi.useFakeTimers();
  let active = true;
  let resolve!: (value: any) => void;
  vi.mocked(apiClient.get).mockImplementation(() => new Promise(r => { resolve = r; }));
  const update = vi.fn();
  const promise = waitForJob(job, 'a', update, () => active);
  const checked = expect(promise).rejects.toThrow('移除');
  await vi.advanceTimersByTimeAsync(1000);
  active = false;
  resolve({ data: { ...job, status: 'ready' } });
  await checked;
  expect(update).toHaveBeenCalledTimes(1);
});
