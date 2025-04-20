import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const JobExecution: React.FC = () => {
  return (
    <div className="job-execution">
      <Card>
        <Title level={4}>作业执行控制</Title>
        <Empty description="作业执行控制暂无内容" />
      </Card>
    </div>
  );
};

export default JobExecution; 