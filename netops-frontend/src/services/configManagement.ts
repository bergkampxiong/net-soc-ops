import request from '../utils/request';
import type { ConfigFile, Version } from '../types/config';

export const configManagementService = {
  getConfigs: () => {
    return request.get<ConfigFile[]>('config/files');
  },

  getConfig: (id: string) => {
    return request.get<ConfigFile>(`config/files/${id}`);
  },

  createConfig: (config: Partial<ConfigFile>) => {
    return request.post<ConfigFile>('config/files', config);
  },

  updateConfig: (id: string, config: Partial<ConfigFile>) => {
    return request.put<ConfigFile>(`config/files/${id}`, config);
  },

  deleteConfig: (id: string) => {
    return request.delete(`config/files/${id}`);
  },

  getVersions: (configId: string) => {
    return request.get<Version[]>(`config/files/${configId}/versions`);
  },

  createVersion: (configId: string, content: string, comment: string) => {
    return request.post<Version>(`config/files/${configId}/versions`, {
      content,
      comment,
    });
  },

  renderTemplate: (templateName: string, variables: Record<string, any>) => {
    return request.post<{ content: string }>('config/render-template', {
      template_name: templateName,
      variables,
    });
  },

  parseConfig: (templateName: string, rawText: string) => {
    return request.post<{ result: any[] }>('config/parse-config', {
      template_name: templateName,
      raw_text: rawText,
    });
  },
}; 