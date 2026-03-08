/**
 * IP 管理布局：仅面包屑 + 当前子页内容，导航由侧栏完成（PRD-IP管理功能）
 */
import React from 'react';
import { Breadcrumb } from 'antd';
import { useLocation, Outlet, Link } from 'react-router-dom';

const IPManagementLayout: React.FC = () => {
  const location = useLocation();
  const path = location.pathname;

  const getBreadcrumb = (): { title: React.ReactNode }[] => {
    const items: { title: React.ReactNode }[] = [{ title: <Link to="/config-module/ip-management/aggregates">IP 管理</Link> }];
    if (path.includes('/config-module/ip-management/aggregates')) {
      items.push({ title: '聚合（Aggregates）' });
    } else if (path.includes('/config-module/ip-management/prefixes')) {
      items.push({ title: '网段（Prefixes）' });
    } else if (path.includes('/config-module/ip-management/import')) {
      items.push({ title: '网络导入' });
    } else if (path.includes('/config-module/ip-management/dhcp')) {
      items.push({ title: 'DHCP 服务管理' });
    } else {
      items.push({ title: '聚合（Aggregates）' });
    }
    return items;
  };

  return (
    <div style={{ padding: '16px 24px' }}>
      <Breadcrumb style={{ marginBottom: 16 }} items={getBreadcrumb()} />
      <Outlet />
    </div>
  );
};

export default IPManagementLayout;
