import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const MonitoringIntegration: React.FC = () => {
  return (
    <div className="monitoring-integration">
      <Card>
        <Title level={4}>监控系统集成</Title>
        <Empty description="监控系统集成暂无内容" />
      </Card>
    </div>
  );
};

export default MonitoringIntegration; 