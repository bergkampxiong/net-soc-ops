import request from './utils/request';

// API 基础配置
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// 请求超时时间（毫秒）
export const REQUEST_TIMEOUT = 10000;

// 刷新 token 的提前时间（毫秒）
export const REFRESH_TOKEN_BEFORE_EXPIRY = 5 * 60 * 1000; // 5分钟

// 会话超时时间（毫秒）
export const SESSION_TIMEOUT = 30 * 60 * 1000; // 30分钟

// 获取安全设置
export const getSecuritySettings = async () => {
  try {
    const response = await request.get('/security/settings');
    return response.data;
  } catch (error) {
    console.error('获取安全设置失败:', error);
    return null;
  }
};

// 获取系统配置
export const getSystemConfig = async () => {
  try {
    const response = await request.get('/system/config');
    return response.data;
  } catch (error) {
    console.error('获取系统配置失败:', error);
    return null;
  }
};

// 获取用户信息
export const getUserInfo = async () => {
  try {
    const response = await request.get('/auth/me');
    return response.data;
  } catch (error) {
    console.error('获取用户信息失败:', error);
    return null;
  }
}; 