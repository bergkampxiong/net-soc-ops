import React from 'react';
import { Card, Typography, Tabs } from 'antd';
import { Outlet } from 'react-router-dom';

const { Title } = Typography;
const { TabPane } = Tabs;

const TaskJobManagement: React.FC = () => {
  return (
    <div className="task-job-management">
      <Card>
        <Title level={3}>任务作业管理</Title>
        <div className="job-management-content">
          <Outlet />
        </div>
      </Card>
    </div>
  );
};

export default TaskJobManagement; 