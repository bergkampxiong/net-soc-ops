export interface Job {
  id: number;
  name: string;
  description?: string;
  job_type: string;
  status: 'created' | 'active' | 'paused' | 'terminated';
  parameters?: Record<string, any>;
  schedule_config?: Record<string, any>;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  next_run_at?: string;
  created_by: string;
  updated_by: string;
}

export interface JobExecution {
  id: number;
  job_id: number;
  status: 'running' | 'completed' | 'failed';
  start_time: string;
  end_time?: string;
  result?: Record<string, any>;
  error_message?: string;
  logs?: string;
  created_at: string;
  updated_at: string;
}

export interface JobFormData {
  name: string;
  description?: string;
  job_type: string;
  parameters?: Record<string, any>;
  schedule_config?: {
    type: 'manual' | 'cron' | 'interval';
    cron_expression?: string;
    interval_seconds?: number;
    start_time?: string;
    end_time?: string;
    timezone?: string;
  };
}

export interface JobSearchParams {
  name?: string;
  job_type?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
} 