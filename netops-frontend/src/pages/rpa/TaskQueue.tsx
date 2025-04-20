import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const TaskQueue: React.FC = () => {
  return (
    <div className="task-queue">
      <Card>
        <Title level={4}>任务队列管理</Title>
        <Empty description="任务队列管理暂无内容" />
      </Card>
    </div>
  );
};

export default TaskQueue; 