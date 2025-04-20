import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/lib/locale/zh_CN';
import request from './utils/request';

// 页面组件
import Login from './pages/Login';
import TwoFactorVerify from './pages/TwoFactorVerify';
import Setup2FA from './pages/Setup2FA';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CMDB from './pages/CMDB';
import RPA from './pages/RPA';
import AIOPS from './pages/AIOPS';
import SystemManagement from './pages/SystemManagement';
import AdminRoute from './components/AdminRoute';
import ChangePassword from './pages/ChangePassword';
import DeviceManagement from './pages/DeviceManagement';
import DeviceCategory from './pages/DeviceCategory';
import CredentialManagement from './pages/CredentialManagement';

// 样式
import './styles/App.css';

// 受保护的路由组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        console.log('Verifying authentication...');
        const response = await request.get('/api/auth/verify');
        const isAuth = response.status === 200;
        console.log('Authentication result:', isAuth);
        setIsAuthenticated(isAuth);
        if (!isAuth) {
          console.log('Not authenticated, redirecting to login');
          navigate('/login');
        }
      } catch (error) {
        console.error('验证身份时出错:', error);
        setIsAuthenticated(false);
        navigate('/login');
      }
    };

    verifyAuth();
  }, [navigate]);

  // 加载状态
  if (isAuthenticated === null) {
    return <div>加载中...</div>;
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/2fa-verify" element={<TwoFactorVerify />} />
        <Route path="/setup-2fa" element={<Setup2FA />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="cmdb/*" element={<CMDB />} />
          <Route path="device/*" element={<DeviceManagement />}>
            <Route path="category" element={<DeviceCategory />} />
            <Route path="credentials" element={<CredentialManagement />} />
          </Route>
          <Route path="rpa/*" element={<RPA />} />
          <Route path="aiops" element={<AIOPS />} />
          <Route path="system" element={
            <AdminRoute>
              <SystemManagement />
            </AdminRoute>
          } />
          <Route path="change-password" element={<ChangePassword />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ConfigProvider>
  );
};

export default App; 