import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const ExecutionHistory: React.FC = () => {
  return (
    <div className="execution-history">
      <Card>
        <Title level={4}>执行历史分析</Title>
        <Empty description="执行历史分析暂无内容" />
      </Card>
    </div>
  );
};

export default ExecutionHistory; 