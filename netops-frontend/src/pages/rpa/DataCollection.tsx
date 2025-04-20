import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

const DataCollection: React.FC = () => {
  return (
    <div className="data-collection">
      <Card>
        <Title level={4}>数据采集组件</Title>
        <Empty description="数据采集组件暂无内容" />
      </Card>
    </div>
  );
};

export default DataCollection; 