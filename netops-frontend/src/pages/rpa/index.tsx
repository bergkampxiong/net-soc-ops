import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// 导入组件
import AtomicComponents from './AtomicComponents';
import DeviceConnections from './DeviceConnections';
import ConfigManagement from './ConfigManagement';
import ConfigGenerator from './atomic-components/config-generator';
import DataCollection from './DataCollection';
import SecurityAudit from './SecurityAudit';
import AlertReporting from './AlertReporting';

import ProcessOrchestration from './ProcessOrchestration';
import VisualDesigner from './VisualDesigner';
import ProcessManagement from './ProcessManagement';
import ProcessExecution from './ProcessExecution';

import MonitoringAnalysis from './MonitoringAnalysis';
import RealtimeDashboard from './RealtimeDashboard';
import ExecutionHistory from './ExecutionHistory';
import CustomReports from './CustomReports';

import TaskJobManagement from './TaskJobManagement';
import JobExecution from './JobExecution';
import JobScheduling from './JobScheduling';
import TaskQueue from './TaskQueue';
import JobMonitoring from './JobMonitoring';

import SystemIntegration from './SystemIntegration';
import MonitoringIntegration from './MonitoringIntegration';
import TicketIntegration from './TicketIntegration';

const RPARouter: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="atomic-components/device-connections" />} />
      
      {/* 原子功能组件库 */}
      <Route path="atomic-components" element={<AtomicComponents />}>
        <Route index element={<Navigate to="device-connections" />} />
        <Route path="device-connections" element={<DeviceConnections />} />
        <Route path="config-management" element={<ConfigManagement />} />
        <Route path="config-generator" element={<ConfigGenerator />} />
        <Route path="data-collection" element={<DataCollection />} />
        <Route path="security-audit" element={<SecurityAudit />} />
        <Route path="alert-reporting" element={<AlertReporting />} />
      </Route>
      
      {/* 流程编排引擎 */}
      <Route path="process-orchestration" element={<ProcessOrchestration />}>
        <Route index element={<Navigate to="visual-designer" />} />
        <Route path="visual-designer" element={<VisualDesigner />} />
        <Route path="process-management" element={<ProcessManagement />} />
        <Route path="process-execution" element={<ProcessExecution />} />
      </Route>
      
      {/* 执行监控与分析 */}
      <Route path="monitoring-analysis" element={<MonitoringAnalysis />}>
        <Route index element={<Navigate to="realtime-dashboard" />} />
        <Route path="realtime-dashboard" element={<RealtimeDashboard />} />
        <Route path="execution-history" element={<ExecutionHistory />} />
        <Route path="custom-reports" element={<CustomReports />} />
      </Route>
      
      {/* 任务作业管理 */}
      <Route path="task-job-management" element={<TaskJobManagement />}>
        <Route index element={<Navigate to="job-execution" />} />
        <Route path="job-execution" element={<JobExecution />} />
        <Route path="job-scheduling" element={<JobScheduling />} />
        <Route path="task-queue" element={<TaskQueue />} />
        <Route path="job-monitoring" element={<JobMonitoring />} />
      </Route>
      
      {/* 系统集成 */}
      <Route path="system-integration" element={<SystemIntegration />}>
        <Route index element={<Navigate to="monitoring-integration" />} />
        <Route path="monitoring-integration" element={<MonitoringIntegration />} />
        <Route path="ticket-integration" element={<TicketIntegration />} />
      </Route>
      
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default RPARouter; 