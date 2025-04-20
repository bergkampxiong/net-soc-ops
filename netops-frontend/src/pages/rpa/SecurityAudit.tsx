import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const SecurityAudit: React.FC = () => {
  return (
    <div className="security-audit">
      <Card>
        <Title level={4}>安全审计组件</Title>
        <Empty description="安全审计组件暂无内容" />
      </Card>
    </div>
  );
};

export default SecurityAudit; 