import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// 导入CMDB子页面
import CMDBIndex from './CMDB/index';
import CMDBQuery from './CMDB/Query';
import CMDBDiscovery from './CMDB/Discovery';
import CMDBInventory from './CMDB/Inventory';
import CMDBModelManage from './CMDB/ModelManage';

/**
 * CMDB主组件
 * 负责CMDB相关路由的管理
 */
const CMDB: React.FC = () => {
  return (
    <Routes>
      {/* 当访问/cmdb时，重定向到/cmdb/query */}
      <Route path="/" element={<Navigate to="/cmdb/query" replace />} />
      <Route path="query" element={<CMDBQuery />} />
      <Route path="discovery" element={<CMDBDiscovery />} />
      <Route path="inventory" element={<CMDBInventory />} />
      <Route path="model" element={<CMDBModelManage />} />
      <Route path="*" element={<Navigate to="/cmdb/query" replace />} />
    </Routes>
  );
};

export default CMDB; 