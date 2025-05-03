import request from '../utils/request';

// 流程定义接口
export interface ProcessDefinition {
  id: string;
  name: string;
  description?: string;
  version: number;
  status: 'draft' | 'published' | 'disabled';
  nodes: any[];
  edges: any[];
  variables: Record<string, any>;
  created_by: string;
  created_at: string;
  updated_by: string;
  updated_at: string;
  deleted_at?: string;
}

// 流程版本接口
export interface ProcessDefinitionVersion {
  id: string;
  process_id: string;
  version: number;
  nodes: any[];
  edges: any[];
  variables: Record<string, any>;
  created_by: string;
  created_at: string;
}

// 获取流程定义列表
export async function getProcessDefinitions() {
  return request.get('/process-definitions');
}

// 创建流程定义
export async function createProcessDefinition(data: Partial<ProcessDefinition>) {
  return request.post('/process-definitions', data);
}

// 更新流程定义
export async function updateProcessDefinition(id: string, data: Partial<ProcessDefinition>) {
  return request.put(`/process-definitions/${id}`, data);
}

// 删除流程定义
export async function deleteProcessDefinition(id: string) {
  return request.delete(`/process-definitions/${id}`);
}

// 发布流程定义
export async function publishProcessDefinition(id: string) {
  return request.post(`/process-definitions/${id}/publish`);
}

// 禁用流程定义
export async function disableProcessDefinition(id: string) {
  return request.post(`/process-definitions/${id}/disable`);
}

// 获取流程版本历史
export async function getProcessVersions(id: string) {
  return request.get(`/process-definitions/${id}/versions`);
}

// 回滚流程版本
export async function rollbackProcessVersion(id: string, version: number) {
  return request.post(`/process-definitions/${id}/rollback/${version}`);
} 