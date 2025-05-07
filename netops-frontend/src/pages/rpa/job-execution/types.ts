// 作业类型
export type JobType = 'network_config' | 'device_check' | 'data_collection';

// 作业状态
export type JobStatus = 'created' | 'active' | 'paused' | 'completed' | 'failed' | 'terminated';

// 调度类型
export type ScheduleType = 'manual' | 'cron' | 'interval' | 'calendar';

// 重试策略
export interface RetryPolicy {
  max_retries: number;
  retry_interval: number;
}

// 调度配置
export interface ScheduleConfig {
  enabled: boolean;
  type: ScheduleType;
  cron_expression?: string;
  interval_seconds?: number;
  calendar_rules?: string[];
  time?: string;
  timezone: string;
  retry_policy?: RetryPolicy;
  timeout?: number;
  concurrent_limit?: number;
}

// 作业表单数据
export interface JobFormData {
  name: string;
  description?: string;
  job_type: JobType;
  parameters?: Record<string, any>;
  schedule_config: ScheduleConfig;
}

// 作业执行记录
export interface JobExecution {
  id: number;
  job_id: number;
  status: JobStatus;
  start_time: string;
  end_time?: string;
  result?: Record<string, any>;
  error_message?: string;
  logs?: string;
  created_at: string;
  updated_at: string;
}

// 作业列表项
export interface JobListItem {
  id: number;
  name: string;
  description?: string;
  job_type: JobType;
  status: JobStatus;
  schedule_status: 'enabled' | 'disabled';
  parameters?: Record<string, any>;
  schedule_config: ScheduleConfig;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  next_run_at?: string;
  created_by: string;
  updated_by: string;
}

// 作业搜索参数
export interface JobSearchParams {
  name?: string;
  job_type?: JobType;
  status?: JobStatus;
  schedule_status?: 'enabled' | 'disabled';
  start_time?: string;
  end_time?: string;
  page: number;
  page_size: number;
}

// 作业列表响应
export interface JobListResponse {
  total: number;
  items: JobListItem[];
}

// 作业详情响应
export interface JobDetailResponse extends JobListItem {
  execution_history: JobExecution[];
}

// 兼容旧版本的Job类型
export type Job = JobListItem; 