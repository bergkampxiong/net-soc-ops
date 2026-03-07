import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ConfigModuleSummary from './Summary';
import ConfigModuleManagement from './Management';
import ConfigModuleCompliance from './Compliance';
import ConfigModuleEos from './Eos';

/**
 * 配置管理模块：配置摘要、配置管理、合规检查、服务终止
 */
const ConfigModule: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/config-module/summary" replace />} />
      <Route path="summary" element={<ConfigModuleSummary />} />
      <Route path="management" element={<ConfigModuleManagement />} />
      <Route path="compliance" element={<ConfigModuleCompliance />} />
      <Route path="eos" element={<ConfigModuleEos />} />
      <Route path="*" element={<Navigate to="/config-module/summary" replace />} />
    </Routes>
  );
};

export default ConfigModule;
