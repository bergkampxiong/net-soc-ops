import React from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  extra?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, extra }) => {
  return (
    <div 
      style={{
        background: 'linear-gradient(90deg, #1890ff, #52c41a)',
        padding: '12px 20px',
        borderRadius: '6px',
        marginBottom: '20px',
        boxShadow: '0 2px 6px rgba(24, 144, 255, 0.3)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <div>
        <Title level={2} style={{ color: 'white', margin: 0 }}>{title}</Title>
        {subtitle && <div style={{ color: 'rgba(255, 255, 255, 0.85)', marginTop: '4px' }}>{subtitle}</div>}
      </div>
      {extra && <div>{extra}</div>}
    </div>
  );
};

export default PageHeader; 