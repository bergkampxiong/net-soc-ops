import request from '../utils/request';
import type { ApiResponse } from '../types/api';
import type { DeviceGroup, DeviceMember } from '../types/device';

// 设备分组API
export const deviceGroupApi = {
  // 获取设备分组列表
  getList: () => {
    return request.get<ApiResponse<DeviceGroup[]>>('device/category');
  },

  // 获取分组成员
  getMembers: (groupId: string) => {
    return request.get<ApiResponse<DeviceMember[]>>(`device/category/${groupId}/members`);
  }
}; 