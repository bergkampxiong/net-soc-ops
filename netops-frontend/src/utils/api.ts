import axios from 'axios';
import { message } from 'antd';

// 创建 axios 实例
const api = axios.create({
  // 使用相对路径，这样请求会通过react-scripts dev server的代理转发
  baseURL: process.env.NODE_ENV === 'development' ? '' : process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      // 处理错误响应
      const { status, data } = error.response;
      switch (status) {
        case 401:
          // 未授权，清除 token 并跳转到登录页
          localStorage.removeItem('token');
          window.location.href = '/login';
          break;
        case 403:
          message.error('没有权限访问该资源');
          break;
        case 404:
          message.error('请求的资源不存在');
          break;
        case 500:
          message.error('服务器内部错误');
          break;
        default:
          // 处理detail字段，确保不会渲染对象
          let errorMessage = '请求失败';
          if (data && data.detail) {
            if (typeof data.detail === 'string') {
              errorMessage = data.detail;
            } else if (Array.isArray(data.detail)) {
              // 如果detail是数组，提取第一个错误信息
              const firstError = data.detail[0];
              if (firstError && typeof firstError === 'object') {
                // 如果是验证错误对象，尝试提取msg字段
                errorMessage = firstError.msg || JSON.stringify(firstError);
              } else {
                errorMessage = String(firstError);
              }
            } else if (typeof data.detail === 'object') {
              // 如果detail是对象，转换为字符串
              errorMessage = JSON.stringify(data.detail);
            }
          }
          message.error(errorMessage);
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      message.error('网络错误，请检查网络连接');
    } else {
      // 请求配置出错
      message.error('请求配置错误');
    }
    return Promise.reject(error);
  }
);

export { api }; 