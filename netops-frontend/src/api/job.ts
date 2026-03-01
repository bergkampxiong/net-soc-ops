import request, { LONG_REQUEST_TIMEOUT } from '../utils/request';

/**
 * 执行作业（如渗透测试等长时间任务）
 * 渗透测试可能需 8 小时以上，使用 8 小时超时，避免默认 20s 导致 ECONNABORTED
 */
export function executeJob(jobId: string): ReturnType<typeof request.post> {
  return request.post(`jobs/${jobId}/execute`, {}, { timeout: LONG_REQUEST_TIMEOUT });
}

export const jobApi = {
  execute: executeJob,
};
