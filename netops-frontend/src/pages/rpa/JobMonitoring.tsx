import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const JobMonitoring: React.FC = () => {
  return (
    <div className="job-monitoring">
      <Card>
        <Title level={4}>作业监控与报告</Title>
        <Empty description="作业监控与报告暂无内容" />
      </Card>
    </div>
  );
};

export default JobMonitoring; 