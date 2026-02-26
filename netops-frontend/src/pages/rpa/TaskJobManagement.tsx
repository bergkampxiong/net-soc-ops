import React from 'react';
import { Outlet } from 'react-router-dom';

const TaskJobManagement: React.FC = () => {
  return (
    <div className="task-job-management">
      <Outlet />
    </div>
  );
};

export default TaskJobManagement; 