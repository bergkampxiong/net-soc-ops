import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ConfigModuleSummary from './Summary';
import ConfigModuleManagement from './Management';
import ConfigModuleCompliance from './Compliance';
import ConfigModuleEos from './Eos';
import IPManagementLayout from './IPManagement/Layout';
import IPManagementAggregates from './IPManagement/Aggregates';
import IPManagementAggregateDetail from './IPManagement/AggregateDetail';
import IPManagementPrefixes from './IPManagement/Prefixes';
import IPManagementPrefixDetail from './IPManagement/PrefixDetail';
import IPManagementImport from './IPManagement/Import';
import IPManagementDhcpServers from './IPManagement/DhcpServers';
import IPManagementDhcpScopes from './IPManagement/DhcpScopes';
import IPManagementDhcpScopeIps from './IPManagement/DhcpScopeIps';

/**
 * 配置管理模块：配置摘要、配置管理、IP 管理、合规检查、服务终止
 */
const ConfigModule: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/config-module/summary" replace />} />
      <Route path="summary" element={<ConfigModuleSummary />} />
      <Route path="management" element={<ConfigModuleManagement />} />
      <Route path="ip-management" element={<IPManagementLayout />}>
        <Route index element={<Navigate to="/config-module/ip-management/aggregates" replace />} />
        <Route path="aggregates" element={<IPManagementAggregates />} />
        <Route path="aggregates/:id" element={<IPManagementAggregateDetail />} />
        <Route path="prefixes" element={<IPManagementPrefixes />} />
        <Route path="prefixes/:id" element={<IPManagementPrefixDetail />} />
        <Route path="import" element={<IPManagementImport />} />
        <Route path="dhcp" element={<IPManagementDhcpServers />} />
        <Route path="dhcp/servers/:serverId" element={<IPManagementDhcpScopes />} />
        <Route path="dhcp/scopes/:scopeId" element={<IPManagementDhcpScopeIps />} />
      </Route>
      <Route path="compliance" element={<ConfigModuleCompliance />} />
      <Route path="eos" element={<ConfigModuleEos />} />
      <Route path="*" element={<Navigate to="/config-module/summary" replace />} />
    </Routes>
  );
};

export default ConfigModule;
