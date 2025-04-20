import request from '../utils/request';
import type { ApiResponse } from '../types/api';
import type { SSHConfig, SSHCredential } from '../types/rpa';

// SSH配置API
export const sshConfigApi = {
  // 获取SSH配置列表
  getList: () => {
    return request.get<ApiResponse<SSHConfig[]>>('/rpa/atomic-components/device-connections');
  },

  // 获取SSH凭证列表
  getCredentials: () => {
    return request.get<ApiResponse<SSHCredential[]>>('/rpa/atomic-components/device-credentials');
  }
}; 