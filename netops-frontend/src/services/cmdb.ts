import request from '../utils/request';

/**
 * CMDB服务
 * 提供CMDB相关的API调用
 */

// 数据查询相关API
export const getDeviceTypes = async (params?: any) => {
  try {
    const response = await request.get('/cmdb/base/device-types', { params });
    return response.data;
  } catch (error) {
    console.error('获取设备类型失败:', error);
    throw error;
  }
};

// 自动发现相关API
export const getDiscoveryTasks = async (params?: any) => {
  try {
    const response = await request.get('/cmdb/discovery/tasks', { params });
    return response.data;
  } catch (error) {
    console.error('获取发现任务失败:', error);
    throw error;
  }
};

export const createDiscoveryTask = async (data: any) => {
  try {
    const response = await request.post('/cmdb/discovery/tasks', data);
    return response.data;
  } catch (error) {
    console.error('创建发现任务失败:', error);
    throw error;
  }
};

// 资产盘点相关API
export const getInventoryTasks = async (params?: any) => {
  try {
    const response = await request.get('/cmdb/inventory/tasks', { params });
    return response.data;
  } catch (error) {
    console.error('获取盘点任务失败:', error);
    throw error;
  }
};

export const createInventoryTask = async (data: any) => {
  try {
    const response = await request.post('/cmdb/inventory/tasks', data);
    return response.data;
  } catch (error) {
    console.error('创建盘点任务失败:', error);
    throw error;
  }
}; 