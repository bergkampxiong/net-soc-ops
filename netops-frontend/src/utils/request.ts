import axios, { AxiosResponse, AxiosInstance } from 'axios';
import { message } from 'antd';
import { notifySessionActivity } from './sessionActivity';

// 标准响应格式
export interface StandardResponse<T> {
  status: number;  // HTTP状态码
  code?: number;   // 业务状态码
  message?: string;
  data: T;
  total?: number;
}

// 扩展AxiosInstance类型，使其返回标准响应格式
interface CustomAxiosInstance extends Omit<AxiosInstance, 'get' | 'delete' | 'post' | 'put' | 'patch'> {
  get<T = any>(url: string, config?: any): Promise<StandardResponse<T>>;
  delete<T = any>(url: string, config?: any): Promise<StandardResponse<T>>;
  post<T = any>(url: string, data?: any, config?: any): Promise<StandardResponse<T>>;
  put<T = any>(url: string, data?: any, config?: any): Promise<StandardResponse<T>>;
  patch<T = any>(url: string, data?: any, config?: any): Promise<StandardResponse<T>>;
  (config: any): Promise<any>;  // 添加request方法的类型定义
}

// 长时间任务（如渗透测试、作业执行）使用的超时时间（毫秒），默认 10 分钟
export const LONG_REQUEST_TIMEOUT = 600000;

// 创建axios实例
// baseURL设置为/api，这样：
// 1. 调用 request.get('user/list') 会自动变成 /api/user/list
// 2. httpproxy 会保留/api前缀转发到后端
// 3. 代码中不需要手动添加/api
const request = axios.create({
  baseURL: '/api',  // 自动添加/api前缀
  timeout: 20000,   // 20 秒，减少慢环境下的超时
  headers: {
    'Content-Type': 'application/json'
  }
}) as CustomAxiosInstance;

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 强制使用相对路径 /api，避免被改为绝对地址（如 https://127.0.0.1:8000）导致跨域或协议错误
    if (config.baseURL && (config.baseURL.includes('127.0.0.1') || config.baseURL.includes('localhost:8000'))) {
      config.baseURL = '/api';
    }

    // 从localStorage获取token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 确保URL不会重复添加/api前缀
    if (config.url?.startsWith('/api/')) {
      config.url = config.url.substring(4); // 移除重复的/api前缀
    }

    // 确保URL不会以斜杠开头，避免与baseURL重复
    if (config.url?.startsWith('/')) {
      config.url = config.url.substring(1);
    }

    // 添加调试日志（baseURL 与 url 之间补斜杠，避免显示成 /apicmdb/...）
    const fullUrl = config.baseURL && config.url
      ? (config.baseURL.replace(/\/+$/, '') + (config.url.startsWith('/') ? '' : '/') + config.url.replace(/^\/+/, ''))
      : (config.url || '');
    console.log(`发送请求: ${config.method?.toUpperCase()} ${fullUrl}`);
    if (config.data) {
      // 不记录敏感信息
      const logData = {...config.data};
      if (logData.bind_password) logData.bind_password = '********';
      if (logData.password) logData.password = '********';
      console.log('请求数据:', logData);
    }

    return config;
  },
  (error) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse) => {
    // 添加调试日志
    console.log(`收到响应: ${response.status} ${response.config.url}`);
    console.log('响应数据:', response.data);
    
    // 构造标准响应格式
    const standardResponse = {
      status: response.status,
      code: response.data.code || 0,
      message: response.data.message || '',
      data: response.data.data || response.data,
      total: response.data.total
    } as StandardResponse<any>;
    
    // 返回原始响应，但添加标准响应格式
    (response as any).standardResponse = standardResponse;
    return response;
  },
  async (error) => {
    // 添加调试日志
    console.error('响应错误:', error);
    if (error.response) {
      console.error('错误状态:', error.response.status);
      console.error('错误数据:', error.response.data);
    }
    
    const originalRequest = error.config;
    const isLoginRequest = originalRequest?.url?.includes('auth/login') ?? false;

    // 登录接口的 401 不尝试刷新 token，直接交给业务层展示错误（如“用户名或密码错误”）
    // 仅对已登录后的接口 401 尝试用 refresh_token 刷新
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/token/refresh') &&
      !isLoginRequest
    ) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        const response = await request.post('/auth/token/refresh', { refresh_token: refreshToken });

        if (response.status === 200) {
          const newToken = response.data.access_token;
          localStorage.setItem('token', newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          notifySessionActivity(); // 刷新成功视为活动，重置会话超时计时器
          return request(originalRequest);
        }
      } catch (refreshError) {
        console.error('刷新令牌失败:', refreshError);
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    // 处理其他错误
    if (error.response) {
      // 服务器返回了错误响应
      const { status, data } = error.response;
      
      // 显示错误消息（FastAPI 使用 detail，部分接口使用 message）
      const errorMsg = data?.detail ?? data?.message;
      if (errorMsg) {
        message.error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
      } else if (status === 404) {
        message.error('请求的资源不存在');
      } else if (status === 403) {
        message.error('没有权限执行此操作');
      } else if (status === 500) {
        message.error('服务器内部错误');
      } else {
        message.error(`请求失败: ${status}`);
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      message.error('无法连接到服务器，请检查网络连接');
    } else {
      // 请求设置时出错
      message.error(`请求错误: ${error.message}`);
    }
    
    return Promise.reject(error);
  }
);

// 重写request的方法，使其返回标准响应格式
const originalGet = request.get;
request.get = async function<T>(url: string, config?: any): Promise<StandardResponse<T>> {
  const response = await originalGet.call(this, url, config);
  return (response as any).standardResponse;
};

const originalPost = request.post;
request.post = async function<T>(url: string, data?: any, config?: any): Promise<StandardResponse<T>> {
  const response = await originalPost.call(this, url, data, config);
  return (response as any).standardResponse;
};

const originalPut = request.put;
request.put = async function<T>(url: string, data?: any, config?: any): Promise<StandardResponse<T>> {
  const response = await originalPut.call(this, url, data, config);
  return (response as any).standardResponse;
};

const originalDelete = request.delete;
request.delete = async function<T>(url: string, config?: any): Promise<StandardResponse<T>> {
  const response = await originalDelete.call(this, url, config);
  return (response as any).standardResponse;
};

const originalPatch = request.patch;
request.patch = async function<T>(url: string, data?: any, config?: any): Promise<StandardResponse<T>> {
  const response = await originalPatch.call(this, url, data, config);
  return (response as any).standardResponse;
};

export default request; 