import { apiErrorMessage } from './errorMessage';
import apiClient from './client';
import { BackgroundJob } from '../types/api';

export const JOB_REQUEST_TIMEOUT = 30_000;
export const isActiveJob = (job?: BackgroundJob | null) => (
  !!job && ['queued', 'running', 'cancelling'].includes(job.status)
);

// Network errors retry the existing identity, never create another expensive job.
export async function waitForJob(
  initial: BackgroundJob,
  sessionId: string,
  onProgress: (job: BackgroundJob) => void,
  shouldContinue: () => boolean = () => true,
): Promise<BackgroundJob> {
  let job = initial;
  let failures = 0;
  while (shouldContinue()) {
    onProgress(job);
    if (job.status === 'ready') return job;
    if (!isActiveJob(job)) throw new Error(job.error || `工作狀態：${job.status}`);
    await new Promise(resolve => setTimeout(resolve, Math.min(1_000 * 2 ** failures, 5_000)));
    if (!shouldContinue()) throw new Error('工作已從此分頁移除。');
    try {
      const response = await apiClient.get<BackgroundJob>(`/jobs/${job.job_id}`, {
        params: { client_session_id: sessionId }, timeout: JOB_REQUEST_TIMEOUT,
      });
      job = response.data;
      failures = 0;
    } catch (error: any) {
      const status = error.response?.status;
      if (status && status < 500 && status !== 429) throw error;
      if (++failures >= 4) throw new Error('暫時無法取得工作狀態；工作可能仍在執行。請按「重試查詢」繼續同一工作。');
    }
  }
  throw new Error('工作已從此分頁移除。');
}

export async function jobErrorMessage(error: any, fallback: string): Promise<string> {
  let body = error.response?.data;
  if (body instanceof Blob) {
    try { body = JSON.parse(await body.text()); } catch { /* use the HTTP message */ }
  }
  return apiErrorMessage({ ...error, message: error.message, response: { ...error.response, data: body } }, fallback);
}
