import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const CustomReports: React.FC = () => {
  return (
    <div className="custom-reports">
      <Card>
        <Title level={4}>自定义报表与仪表盘</Title>
        <Empty description="自定义报表与仪表盘暂无内容" />
      </Card>
    </div>
  );
};

export default CustomReports; 