import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const TicketIntegration: React.FC = () => {
  return (
    <div className="ticket-integration">
      <Card>
        <Title level={4}>工单系统集成</Title>
        <Empty description="工单系统集成暂无内容" />
      </Card>
    </div>
  );
};

export default TicketIntegration; 