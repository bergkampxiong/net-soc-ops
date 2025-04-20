import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const ProcessManagement: React.FC = () => {
  return (
    <div className="process-management">
      <Card>
        <Title level={4}>流程管理</Title>
        <Empty description="流程管理暂无内容" />
      </Card>
    </div>
  );
};

export default ProcessManagement; 