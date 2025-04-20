import React from 'react';
import { Card, Typography, Tabs } from 'antd';
import { Outlet } from 'react-router-dom';

const { Title } = Typography;
const { TabPane } = Tabs;

const SystemIntegration: React.FC = () => {
  return (
    <div className="system-integration">
      <Card>
        <Title level={3}>系统集成</Title>
        <div className="integration-content">
          <Outlet />
        </div>
      </Card>
    </div>
  );
};

export default SystemIntegration; 