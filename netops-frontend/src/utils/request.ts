import axios, { AxiosResponse, AxiosInstance } from 'axios';
import { message } from 'antd';

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

// 创建axios实例
// baseURL设置为/api，这样：
// 1. 调用 request.get('user/list') 会自动变成 /api/user/list
// 2. httpproxy 会保留/api前缀转发到后端
// 3. 代码中不需要手动添加/api
const request = axios.create({
  baseURL: '/api',  // 自动添加/api前缀
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
}) as CustomAxiosInstance;

// 请求拦截器
request.interceptors.request.use(
  (config) => {
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

    // 添加调试日志
    console.log(`发送请求: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
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
      data: response.data,
      ...response.data  // 保留原有的其他字段
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
    
    // 如果是401错误且不是刷新令牌的请求
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url.includes('/auth/refresh')) {
      originalRequest._retry = true;
      
      try {
        // 获取刷新令牌
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }
        
        // 尝试刷新令牌
        const response = await request.post('/auth/refresh', { refresh_token: refreshToken });
        
        if (response.status === 200) {
          // 更新访问令牌
          const newToken = response.data.access_token;
          localStorage.setItem('token', newToken);
          
          // 更新原始请求的Authorization头
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          
          // 重试原始请求
          return request(originalRequest);
        }
      } catch (refreshError) {
        console.error('刷新令牌失败:', refreshError);
        // 清除令牌并重定向到登录页面
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
      
      // 显示错误消息
      if (data && data.message) {
        message.error(data.message);
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