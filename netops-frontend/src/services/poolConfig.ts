import request from '../utils/request';

export interface PoolConfig {
  id: number;
  connection_id: number;
  max_connections: number;
  min_idle: number;
  idle_timeout: number;
  connection_timeout: number;
  description: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface PoolConfigUpdate {
  max_connections?: number;
  min_idle?: number;
  idle_timeout?: number;
  connection_timeout?: number;
  description?: string;
  is_active?: boolean;
}

export interface PoolStats {
  total_connections: number;
  active_connections: number;
  idle_connections: number;
  waiting_connections: number;
  max_wait_time: number;
  avg_wait_time: number;
  created_at: string;
}

export interface PoolMetrics {
  timestamp: string;
  value: number;
}

export interface PoolMetricsResponse {
  connection_history: Array<{
    timestamp: string;
    value: number;
    type: string;
  }>;
  error_history: Array<{
    timestamp: string;
    value: number;
    type: string;
  }>;
  resource_usage: Array<{
    timestamp: string;
    value: number;
    type: string;
  }>;
}

export interface PoolConfigCreate {
  max_connections: number;
  connection_timeout: number;
  idle_timeout: number;
  max_lifetime: number;
  min_idle: number;
  max_idle: number;
}

/**
 * 获取连接池状态
 * @param poolType 连接池类型：'redis' | 'device'
 * @returns Promise<PoolStats> 连接池状态
 */
export const getPoolStats = async (poolType: string = 'redis'): Promise<PoolStats> => {
  try {
    const response = await request.get(`device/connections/pools/1/stats?pool_type=${poolType}`);
    return response.data;
  } catch (error) {
    console.error('获取连接池状态失败:', error);
    throw error;
  }
};

/**
 * 清理连接池中的连接
 * @param poolType 连接池类型：'redis' | 'device'
 * @returns Promise<void>
 */
export const cleanupConnections = async (poolType: string = 'redis'): Promise<void> => {
  try {
    await request.post(`device/connections/pools/1/cleanup?pool_type=${poolType}`);
  } catch (error) {
    console.error('清理连接池失败:', error);
    throw error;
  }
};

/**
 * 获取连接池指标
 * @param timeRange 时间范围，可选值：1h, 6h, 24h
 * @param poolType 连接池类型：'redis' | 'device'
 * @returns Promise<PoolMetrics[]> 连接池指标
 */
export const getPoolMetrics = async (timeRange: string = '1h', poolType: string = 'redis'): Promise<PoolMetrics[]> => {
  try {
    const response = await request.get(`device/connections/pools/1/metrics?time_range=${timeRange}&pool_type=${poolType}`);
    return response.data;
  } catch (error) {
    console.error('获取连接池指标失败:', error);
    throw error;
  }
}; 