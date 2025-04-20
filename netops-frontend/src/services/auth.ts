import request from '../utils/request';

/**
 * 用户登录
 */
export const login = async (username: string, password: string) => {
  return request.post('/auth/login', { username, password });
};

/**
 * LDAP用户登录
 */
export const ldapLogin = async (username: string, password: string) => {
  return request.post('/auth/login', { username, password });
};

/**
 * 用户登出
 */
export const logout = async () => {
  return request.post('/auth/logout');
};

/**
 * 刷新令牌
 */
export const refreshToken = async (refreshToken: string) => {
  return request.post('/auth/refresh', { refresh_token: refreshToken });
};

/**
 * 获取当前用户信息
 */
export const getCurrentUser = async () => {
  return request.get('/auth/me');
};

/**
 * 修改密码
 */
export const changePassword = async (oldPassword: string, newPassword: string) => {
  return request.post('/auth/change-password', { oldPassword, newPassword });
};

// 导出默认对象
const auth = {
  login,
  ldapLogin,
  logout,
  refreshToken,
  getCurrentUser,
  changePassword
};

export default auth; 