import { api } from '../utils/api';

export interface ApiConfig {
  id: number;
  name: string;
  type: string;
  endpoint: string;
  auth_type: string;
  timeout: number;
  headers: Record<string, string>;
  created_at: string;
  updated_at: string;
}

// 模拟数据
const mockApiConfigs: ApiConfig[] = [
  {
    id: 1,
    name: '测试API配置1',
    type: 'REST',
    endpoint: 'http://example.com/api/v1',
    auth_type: 'Basic',
    timeout: 30,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    name: '测试API配置2',
    type: 'NETCONF',
    endpoint: 'http://example.com/netconf',
    auth_type: 'Token',
    timeout: 60,
    headers: {
      'Authorization': 'Bearer token123'
    },
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z'
  }
];

// 模拟API调用
export const getApiConfigs = async (): Promise<ApiConfig[]> => {
  const response = await api.get('/api/device/api_configs');
  return response.data;
};

export const createApiConfig = async (data: Omit<ApiConfig, 'id' | 'created_at' | 'updated_at'>): Promise<ApiConfig> => {
  const response = await api.post('/api/device/api_config', data);
  return response.data;
};

export const updateApiConfig = async (id: number, data: Partial<ApiConfig>): Promise<ApiConfig> => {
  const response = await api.put(`/api/device/api_config/${id}`, data);
  return response.data;
};

export const deleteApiConfig = async (id: number): Promise<void> => {
  await api.delete(`/api/device/api_config/${id}`);
}; 