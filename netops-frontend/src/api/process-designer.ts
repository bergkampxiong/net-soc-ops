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

export const processCodeGeneratorApi = {
  // 生成代码
  generate: (id: string) => {
    return request.post<ApiResponse<string>>(`process-definitions/${id}/generate-code`);
  },

  // 验证流程
  validate: (id: string) => {
    return request.post<ApiResponse<{ isValid: boolean; errors: string[] }>>(`process-definitions/${id}/validate`);
  },
};

// 流程设计器数据结构
export interface ProcessDesignerData {
  nodes: any[];
  edges: any[];
  variables: Record<string, any>;
}

// 流程设计器保存请求数据
export interface ProcessDesignerSaveRequest {
  name: string;
  description?: string;
  nodes: any[];
  edges: any[];
  variables: Record<string, any>;
}

/**
 * 保存流程设计
 * @param data 流程设计数据
 * @returns 保存后的流程定义
 */
export const saveProcessDesign = async (data: ProcessDesignerSaveRequest): Promise<ProcessDefinition> => {
  const response = await request.post<ProcessDefinition>('/process-definitions', data);
  return response.data;
};

/**
 * 更新流程设计
 * @param id 流程ID
 * @param data 流程设计数据
 * @returns 更新后的流程定义
 */
export const updateProcessDesign = async (id: string, data: ProcessDesignerSaveRequest): Promise<ProcessDefinition> => {
  const response = await request.put<ProcessDefinition>(`/process-definitions/${id}`, data);
  return response.data;
}; 