import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const RealtimeDashboard: React.FC = () => {
  return (
    <div className="realtime-dashboard">
      <Card>
        <Title level={4}>实时监控仪表盘</Title>
        <Empty description="实时监控仪表盘暂无内容" />
      </Card>
    </div>
  );
};

export default RealtimeDashboard; 