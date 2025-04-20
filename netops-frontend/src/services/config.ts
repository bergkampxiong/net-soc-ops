import request from '../utils/request';

/**
 * 获取设备配置内容
 * @param deviceId 设备ID
 */
export const getConfigContent = async (deviceId: string) => {
  return request.get(`/api/v1/config/${deviceId}`);
};

/**
 * 保存设备配置
 * @param deviceId 设备ID
 * @param content 配置内容
 */
export const saveConfig = async (deviceId: string, content: string) => {
  return request.post(`/api/v1/config/${deviceId}`, { content });
};

/**
 * 获取配置历史记录
 * @param deviceId 设备ID
 */
export const getConfigHistory = async (deviceId: string) => {
  return request.get(`/api/v1/config/${deviceId}/history`);
};

/**
 * 回滚到指定版本
 * @param deviceId 设备ID
 * @param version 版本号
 */
export const rollbackConfig = async (deviceId: string, version: string) => {
  return request.post(`/api/v1/config/${deviceId}/rollback`, { version });
};

/**
 * 比较两个版本的配置
 * @param deviceId 设备ID
 * @param version1 版本1
 * @param version2 版本2
 */
export const compareConfigs = async (deviceId: string, version1: string, version2: string) => {
  return request.get(`/api/v1/config/${deviceId}/compare`, {
    params: { version1, version2 }
  });
}; 