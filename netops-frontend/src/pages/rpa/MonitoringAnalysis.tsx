import React from 'react';
import { Card, Typography, Tabs } from 'antd';
import { Outlet } from 'react-router-dom';

const { Title } = Typography;
const { TabPane } = Tabs;

const MonitoringAnalysis: React.FC = () => {
  return (
    <div className="monitoring-analysis">
      <Card>
        <Title level={3}>执行监控与分析</Title>
        <div className="monitoring-content">
          <Outlet />
        </div>
      </Card>
    </div>
  );
};

export default MonitoringAnalysis; 