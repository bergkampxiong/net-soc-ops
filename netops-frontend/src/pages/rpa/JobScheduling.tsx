import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const JobScheduling: React.FC = () => {
  return (
    <div className="job-scheduling">
      <Card>
        <Title level={4}>作业调度管理</Title>
        <Empty description="作业调度管理暂无内容" />
      </Card>
    </div>
  );
};

export default JobScheduling; 