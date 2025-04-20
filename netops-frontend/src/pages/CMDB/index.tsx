import React, { useState } from 'react';
import { Tabs, Typography } from 'antd';
import { DatabaseOutlined, SearchOutlined, AppstoreOutlined, SettingOutlined } from '@ant-design/icons';
import Query from './Query';

const { Title } = Typography;

const CMDB: React.FC = () => {
  const [activeKey, setActiveKey] = useState('query');

  const items = [
    {
      key: 'query',
      label: (
        <span>
          <SearchOutlined />
          资产查询
        </span>
      ),
      children: <Query />
    },
    {
      key: 'management',
      label: (
        <span>
          <AppstoreOutlined />
          资产管理
        </span>
      ),
      disabled: true,
      children: (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <Title level={4}>资产管理功能正在开发中...</Title>
        </div>
      )
    },
    {
      key: 'basedata',
      label: (
        <span>
          <SettingOutlined />
          基础数据
        </span>
      ),
      disabled: true,
      children: (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <Title level={4}>基础数据管理功能正在开发中...</Title>
        </div>
      )
    }
  ];

  return (
    <div className="cmdb-page">
      <Title level={2}>
        <DatabaseOutlined /> 配置管理数据库 (CMDB)
      </Title>
      
      <Tabs 
        activeKey={activeKey} 
        onChange={setActiveKey}
        type="card"
        size="large"
        style={{ marginTop: 20 }}
        items={items}
      />
    </div>
  );
};

export default CMDB; 