/**
 * IP 管理布局：仅当前子页内容，导航由侧栏完成；顶部不展示面包屑（PRD-IP管理功能）
 */
import React from 'react';
import { Outlet } from 'react-router-dom';

const IPManagementLayout: React.FC = () => {
  return (
    <div style={{ padding: '16px 24px' }}>
      <Outlet />
    </div>
  );
};

export default IPManagementLayout;
