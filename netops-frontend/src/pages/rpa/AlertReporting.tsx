import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const AlertReporting: React.FC = () => {
  return (
    <div className="alert-reporting">
      <Card>
        <Title level={4}>告警与报告组件</Title>
        <Empty description="告警与报告组件暂无内容" />
      </Card>
    </div>
  );
};

export default AlertReporting; 