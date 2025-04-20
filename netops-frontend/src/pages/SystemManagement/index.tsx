import React from 'react';
import { Tabs } from 'antd';
import { 
  UserOutlined, SafetyOutlined, 
  AuditOutlined, LockOutlined, 
  ApiOutlined 
} from '@ant-design/icons';

import UserManagement from './UserManagement';
import LDAPConfig from './LDAPConfig';
import AuditLogs from './AuditLogs';
import SecuritySettings from './SecuritySettings';
import TwoFactorAuth from './TwoFactorAuth';

const SystemManagement: React.FC = () => {
  const items = [
    {
      key: 'users',
      label: <span><UserOutlined />用户管理</span>,
      children: <UserManagement />
    },
    {
      key: 'ldap',
      label: <span><ApiOutlined />LDAP配置</span>,
      children: <LDAPConfig />
    },
    {
      key: '2fa',
      label: <span><SafetyOutlined />双因素认证</span>,
      children: <TwoFactorAuth />
    },
    {
      key: 'security',
      label: <span><LockOutlined />安全设置</span>,
      children: <SecuritySettings />
    },
    {
      key: 'audit',
      label: <span><AuditOutlined />审计日志</span>,
      children: <AuditLogs />
    }
  ];

  return (
    <div className="system-management">
      <div className="page-header">
        <h2>系统管理</h2>
      </div>
      
      <Tabs defaultActiveKey="users" tabPosition="left" style={{ minHeight: 'calc(100vh - 200px)' }} items={items} />
    </div>
  );
};

export default SystemManagement; 