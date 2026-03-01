import request, { LONG_REQUEST_TIMEOUT } from '../utils/request';

/** 非渗透类作业执行请求超时（毫秒），避免默认 20s 过早报错 */
export const NORMAL_JOB_EXECUTE_TIMEOUT = 120000;

/**
 * 按作业类型返回执行接口超时：渗透任务不设短超时（不进行延迟告警），其他 120 秒
 */
export function getExecuteTimeout(jobType?: string): number {
  return jobType === 'penetration_task' ? LONG_REQUEST_TIMEOUT : NORMAL_JOB_EXECUTE_TIMEOUT;
}

/**
 * 执行作业；渗透任务使用长超时，其他任务使用 120 秒
 */
export function executeJob(jobId: string, jobType?: string): ReturnType<typeof request.post> {
  return request.post(`jobs/${jobId}/execute`, {}, { timeout: getExecuteTimeout(jobType) });
}

export const jobApi = {
  execute: executeJob,
  getExecuteTimeout,
};
