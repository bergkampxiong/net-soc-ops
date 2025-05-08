import React from 'react';
import { Routes, Route } from 'react-router-dom';
import AtomicComponents from './AtomicComponents';
import ProcessOrchestration from './ProcessOrchestration';
import TaskJobManagement from './TaskJobManagement';
import JobExecution from './JobExecution';
import JobMonitoring from './JobMonitoring';
import SystemIntegration from './SystemIntegration';

const RPA: React.FC = () => {
  return (
    <Routes>
      <Route path="atomic-components/*" element={<AtomicComponents />} />
      <Route path="process-orchestration/*" element={<ProcessOrchestration />} />
      <Route path="task-job-management/*" element={<TaskJobManagement />}>
        <Route path="job-execution" element={<JobExecution />} />
        <Route path="job-monitoring" element={<JobMonitoring />} />
      </Route>
      <Route path="system-integration/*" element={<SystemIntegration />} />
    </Routes>
  );
};

export default RPA; 