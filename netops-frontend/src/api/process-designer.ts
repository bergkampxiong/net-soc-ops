import request from '../utils/request';
import type { ProcessDefinition, ProcessInstance } from '../types/process-designer/pd-types';

interface ApiResponse<T> {
  data: T;
  total?: number;
  list?: T[];
}

export const processDefinitionApi = {
  // 获取流程定义列表
  getList: (params: any) => {
    return request.get<ApiResponse<ProcessDefinition[]>>('process-definitions', { params });
  },

  // 获取流程定义详情
  getDetail: (id: string) => {
    return request.get<ApiResponse<ProcessDefinition>>(`process-definitions/${id}`);
  },

  // 创建流程定义
  create: (data: Partial<ProcessDefinition>) => {
    return request.post<ApiResponse<ProcessDefinition>>('process-definitions', data);
  },

  // 更新流程定义
  update: (id: string, data: Partial<ProcessDefinition>) => {
    return request.put<ApiResponse<ProcessDefinition>>(`process-definitions/${id}`, data);
  },

  // 删除流程定义
  delete: (id: string) => {
    return request.delete<ApiResponse<void>>(`process-definitions/${id}`);
  },

  // 发布流程定义
  publish: (id: string) => {
    return request.post<ApiResponse<ProcessDefinition>>(`process-definitions/${id}/publish`);
  },

  // 禁用流程定义
  disable: (id: string) => {
    return request.post<ApiResponse<ProcessDefinition>>(`process-definitions/${id}/disable`);
  },
};

export const processInstanceApi = {
  // 获取流程实例列表
  getList: (params: any) => {
    return request.get<ApiResponse<ProcessInstance[]>>('process-instances', { params });
  },

  // 获取流程实例详情
  getDetail: (id: string) => {
    return request.get<ApiResponse<ProcessInstance>>(`process-instances/${id}`);
  },

  // 创建流程实例
  create: (data: Partial<ProcessInstance>) => {
    return request.post<ApiResponse<ProcessInstance>>('process-instances', data);
  },

  // 暂停流程实例
  suspend: (id: string) => {
    return request.post<ApiResponse<ProcessInstance>>(`process-instances/${id}/suspend`);
  },

  // 恢复流程实例
  resume: (id: string) => {
    return request.post<ApiResponse<ProcessInstance>>(`process-instances/${id}/resume`);
  },

  // 终止流程实例
  terminate: (id: string) => {
    return request.post<ApiResponse<ProcessInstance>>(`process-instances/${id}/terminate`);
  },
}; 