import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const ProcessExecution: React.FC = () => {
  return (
    <div className="process-execution">
      <Card>
        <Title level={4}>流程调度与执行</Title>
        <Empty description="流程调度与执行暂无内容" />
      </Card>
    </div>
  );
};

export default ProcessExecution; 