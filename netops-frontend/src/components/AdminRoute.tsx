import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import request from '../utils/request';

interface AdminRouteProps {
  children: React.ReactNode;
}

const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const response = await request.get('/auth/me');
        setIsAdmin(response.data.role === 'admin');
      } catch (error) {
        setIsAdmin(false);
      }
    };

    checkAdminStatus();
  }, []);

  // 加载状态
  if (isAdmin === null) {
    return <div>加载中...</div>;
  }

  return isAdmin ? <>{children}</> : <Navigate to="/" />;
};

export default AdminRoute; 