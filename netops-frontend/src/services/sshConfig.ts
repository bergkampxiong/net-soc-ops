import request from '../utils/request';

/**
 * SSH配置接口定义
 * 用于定义SSH连接的基本信息和Netmiko连接参数
 */
export interface SSHConfig {
  id: number;                    // 配置ID
  name: string;                  // 配置名称（用于流程设计器中的组件标识）
  device_type: string;           // 设备类型（Netmiko支持的设备类型名称）
  credential_id: number;         // 关联的凭证ID
  pool_config_id?: number;       // 关联的连接池配置ID
  // Netmiko特定参数
  port: number;                  // SSH端口号
  enable_secret?: string;        // Enable密码（仅用于思科设备）
  global_delay_factor: number;   // 全局延迟因子，用于调整命令执行延迟
  auth_timeout: number;          // SSH认证超时时间（秒）
  banner_timeout: number;        // 等待设备banner的超时时间（秒）
  fast_cli: boolean;            // 是否启用快速CLI模式
  session_timeout: number;       // SSH会话超时时间（秒）
  conn_timeout: number;          // 建立SSH连接的超时时间（秒）
  keepalive: number;            // SSH连接保活间隔（秒）
  verbose: boolean;             // 是否启用详细日志输出
  description?: string;         // 描述信息
  username: string;            // 用户名（从凭证中获取）
  password: string;            // 密码（从凭证中获取）
  created_at: string;           // 创建时间
  updated_at: string;           // 更新时间
}

/**
 * SSH配置创建接口
 * 用于创建新的SSH配置时的参数定义
 */
export interface SSHConfigCreate {
  name: string;
  device_type: string;
  credential_id: number;
  pool_config_id?: number;
  port?: number;
  enable_secret?: string;
  username: string;
  password: string;
  // Netmiko特定参数（可选）
  global_delay_factor?: number;
  auth_timeout?: number;
  banner_timeout?: number;
  fast_cli?: boolean;
  session_timeout?: number;
  conn_timeout?: number;
  keepalive?: number;
  verbose?: boolean;
  description?: string;
}

/**
 * Netmiko支持的设备类型列表
 * 这些类型与Netmiko库中的设备类型定义保持一致
 */
const deviceTypes = [
  'huawei_vrpv8',    // 华为VRPv8设备
  'cisco_ios',       // Cisco IOS设备
  'cisco_nxos',      // Cisco NX-OS设备
  'cisco_xr',        // Cisco XR设备
  'cisco_xe',        // Cisco XE设备
  'hp_comware',      // 惠普Comware设备
  'ruijie_os',       // 锐捷OS设备
  'paloalto_panos',  // Palo Alto PAN-OS设备
  'fortinet',        // Fortinet设备
  'linux'            // Linux设备
];

/**
 * 获取所有SSH配置
 * @returns Promise<SSHConfig[]> SSH配置列表
 */
export async function getSSHConfigs(): Promise<SSHConfig[]> {
  const response = await request.get('device/connections');
  return response.data;
}

/**
 * 创建新的SSH配置
 * @param data SSH配置创建参数
 * @returns Promise<SSHConfig> 新创建的SSH配置
 */
export async function createSSHConfig(data: SSHConfigCreate): Promise<SSHConfig> {
  try {
    // 验证必需字段
    if (!data.name || !data.device_type || !data.credential_id) {
      throw new Error('缺少必需字段：name、device_type 或 credential_id');
    }

    // 创建SSH连接配置
    const configData = {
      name: data.name,
      device_type: data.device_type,
      credential_id: data.credential_id,
      port: data.port || 22,
      enable_secret: data.enable_secret,
      global_delay_factor: data.global_delay_factor || 1,
      auth_timeout: data.auth_timeout || 60,
      banner_timeout: data.banner_timeout || 20,
      fast_cli: data.fast_cli || false,
      session_timeout: data.session_timeout || 60,
      conn_timeout: data.conn_timeout || 20,
      keepalive: data.keepalive || 60,
      verbose: data.verbose || false,
      description: data.description || ''
    };

    console.log('创建SSH连接配置，请求数据:', configData);
    const response = await request.post('device/connections', configData);
    console.log('创建SSH配置成功，响应数据:', response);
    return response.data;
  } catch (error: any) {
    console.error('创建SSH配置失败:', error);
    if (error.response) {
      // 服务器返回错误
      const errorMessage = error.response.data?.detail || error.response.data?.message || '创建SSH配置失败';
      throw new Error(errorMessage);
    } else if (error.request) {
      // 请求发送失败
      throw new Error('无法连接到服务器，请检查网络连接');
    } else {
      // 其他错误（包括验证错误）
      throw error;
    }
  }
}

/**
 * 更新现有SSH配置
 * @param id 要更新的配置ID
 * @param data 更新的配置数据
 * @returns Promise<SSHConfig> 更新后的SSH配置
 */
export async function updateSSHConfig(id: number, data: Partial<SSHConfigCreate>): Promise<SSHConfig> {
  try {
    console.log('更新SSH配置，ID:', id, '数据:', data);
    const response = await request.put(`device/connections/${id}`, data);
    console.log('更新SSH配置成功，响应数据:', response);
    return response.data;
  } catch (error: any) {
    console.error('更新SSH配置失败:', error);
    if (error.response) {
      // 服务器返回错误
      const errorMessage = error.response.data?.detail || error.response.data?.message || '更新SSH配置失败';
      throw new Error(errorMessage);
    } else if (error.request) {
      // 请求发送失败
      throw new Error('无法连接到服务器，请检查网络连接');
    } else {
      // 其他错误
      throw error;
    }
  }
}

/**
 * 删除SSH配置
 * @param id 要删除的配置ID
 */
export async function deleteSSHConfig(id: number): Promise<void> {
  await request.delete(`device/connections/${id}`);
}

/**
 * 获取SSH连接池状态
 * @param configId SSH配置ID
 * @returns Promise<{...}> 连接池状态信息
 */
export const getSSHPoolStatus = async (configId: number): Promise<{
  active_connections: number;    // 活动连接数
  idle_connections: number;      // 空闲连接数
  waiting_connections: number;   // 等待连接数
  connection_errors: number;     // 连接错误数
}> => {
  try {
    const response = await request.get(`device/connections/pools/${configId}/status`);
    return response.data;
  } catch (error) {
    console.error('获取连接池状态失败:', error);
    throw error;
  }
};

/**
 * 清理SSH连接池
 * @param configId SSH配置ID
 * @returns Promise<void>
 */
export const cleanupSSHPool = async (configId: number): Promise<void> => {
  try {
    await request.post(`device/connections/pools/${configId}/cleanup`);
  } catch (error) {
    console.error('清理连接池失败:', error);
    throw error;
  }
};

/**
 * 获取SSH连接池配置
 * @param configId SSH配置ID
 * @returns Promise<{...}> 连接池配置信息
 */
export const getSSHPoolConfig = async (configId: number): Promise<{
  max_connections: number;       // 最大连接数
  connection_timeout: number;    // 连接超时时间
  idle_timeout: number;         // 空闲超时时间
  max_lifetime: number;         // 最大生命周期
}> => {
  try {
    const response = await request.get(`device/connections/pools/${configId}`);
    return response.data;
  } catch (error) {
    console.error('获取连接池配置失败:', error);
    throw error;
  }
};

/**
 * 更新SSH连接池配置
 * @param configId SSH配置ID
 * @param data 更新的连接池配置数据
 */
export const updateSSHPoolConfig = async (
  configId: number,
  data: {
    max_connections?: number;
    connection_timeout?: number;
    idle_timeout?: number;
    max_lifetime?: number;
  }
): Promise<void> => {
  try {
    await request.put(`device/connections/pools/${configId}`, data);
  } catch (error) {
    console.error('更新连接池配置失败:', error);
    throw error;
  }
};

/**
 * 获取设备类型列表
 * @returns Promise<string[]> 设备类型列表
 */
export async function getDeviceTypes(): Promise<string[]> {
  return deviceTypes;
} 