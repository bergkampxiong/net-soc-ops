import React, { useState, useEffect, useRef } from 'react';
import { Layout as AntLayout, Menu, Dropdown, Avatar, Button, message } from 'antd';
import type { MenuProps } from 'antd';
import {
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  RobotOutlined,
  BulbOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  KeyOutlined,
  RadarChartOutlined,
  ScanOutlined,
  DesktopOutlined,
  TagsOutlined,
  SafetyCertificateOutlined,
  AppstoreOutlined,
  CodeOutlined,
  BarChartOutlined,
  ScheduleOutlined,
  ApiOutlined,
  LineChartOutlined,
  LockOutlined,
  FileTextOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import request from '../utils/request';
import { setDisplayTimezone } from '../utils/formatTime';
import sessionManager from '../utils/sessionManager';
import { setSessionActivityCallback } from '../utils/sessionActivity';

const { Header, Sider, Content } = AntLayout;

const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [userRole, setUserRole] = useState<string>('');
  const [username, setUsername] = useState<string>('');
  const [openKeys, setOpenKeys] = useState<string[]>([]);
  const navigate = useNavigate();
  const location = useLocation();
  const menuRef = useRef<any>(null);

  // 获取用户信息
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const response = await request.get('/auth/me');
        if (response.status === 200) {
          setUserRole(response.data.role);
          setUsername(response.data.username);
        }
      } catch (error) {
        console.error('获取用户信息失败:', error);
      }
    };

    fetchUserInfo();
  }, []);

  // 使用系统管理-安全设置中的会话超时时间，初始化会话管理器
  useEffect(() => {
    sessionManager.init();
    setSessionActivityCallback(() => sessionManager.resetSessionTimer());
    return () => {
      setSessionActivityCallback(null);
      sessionManager.stop();
    };
  }, []);

  // 加载全局时钟时区（与系统管理-全局配置一致，所有时间展示使用此刻）
  useEffect(() => {
    const loadGlobalTimezone = async () => {
      try {
        const res = await request.get<Array<{ config_key: string; config_value: string }>>('/system/global-config');
        const list = Array.isArray(res.data) ? res.data : [];
        const tzItem = list.find((i) => i.config_key === 'GLOBAL_TIMEZONE');
        setDisplayTimezone(tzItem?.config_value ?? 'Asia/Shanghai');
      } catch {
        setDisplayTimezone('Asia/Shanghai');
      }
    };
    loadGlobalTimezone();
  }, []);

  // 初始化菜单展开状态
  useEffect(() => {
    setOpenKeys(getOpenKeys());
  }, [location.pathname]);

  const toggle = () => {
    setCollapsed(!collapsed);
  };

  const handleMenuClick = (key: string) => {
    navigate(key);
  };

  const handleLogout = async () => {
    try {
      await request.post('/auth/logout');
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      message.success('已退出登录');
      navigate('/login');
    } catch (error) {
      console.error('退出登录失败:', error);
      // 即使API调用失败，也清除本地存储并跳转
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      navigate('/login');
    }
  };

  // 获取当前选中的菜单项
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path === '/') return ['dashboard'];
    if (path.startsWith('/cmdb')) return ['cmdb'];
    if (path.startsWith('/device/category')) return ['device-category'];
    if (path.startsWith('/device/credentials')) return ['credential-management'];
    
    // RPA子菜单项选中状态
    if (path.startsWith('/rpa/atomic-components')) return ['rpa-atomic-components'];
    if (path.startsWith('/rpa/process-orchestration')) return ['rpa-process-orchestration'];
    if (path.startsWith('/rpa/monitoring-analysis')) return ['rpa-monitoring-analysis'];
    if (path.startsWith('/rpa/task-job-management')) return ['rpa-task-job-management'];
    if (path.startsWith('/rpa/system-integration')) return ['rpa-system-integration'];
    
    if (path.startsWith('/rpa')) return ['rpa'];
    if (path.startsWith('/config-module/summary')) return ['config-module/summary'];
    if (path.startsWith('/config-module/management')) return ['config-module/management'];
    if (path.startsWith('/config-module/compliance')) return ['config-module/compliance'];
    if (path.startsWith('/config-module/eos')) return ['config-module/eos'];
    if (path.startsWith('/config-module/ip-management/aggregates')) return ['ip-management/aggregates'];
    if (path.startsWith('/config-module/ip-management/prefixes')) return ['ip-management/prefixes'];
    if (path.startsWith('/config-module/ip-management/import')) return ['ip-management/import'];
    if (path.startsWith('/config-module/ip-management/dhcp')) return ['ip-management/dhcp'];
    if (path.startsWith('/config-module/ip-management')) return ['ip-management/aggregates'];
    if (path.startsWith('/config-module')) return ['config-module'];
    if (path.startsWith('/aiops')) return ['aiops'];
    if (path.startsWith('/system')) return ['system'];
    return ['dashboard'];
  };

  // 获取当前打开的子菜单
  const getOpenKeys = () => {
    const path = location.pathname;
    if (path.startsWith('/device')) {
      return ['device'];
    }
    if (path.startsWith('/cmdb')) return ['cmdb'];
    
    // 为RPA的子路径设置正确的openKeys
    if (path.startsWith('/rpa/atomic-components')) return ['rpa', 'rpa-atomic-components'];
    if (path.startsWith('/rpa/process-orchestration')) return ['rpa', 'rpa-process-orchestration'];
    if (path.startsWith('/rpa/monitoring-analysis')) return ['rpa', 'rpa-monitoring-analysis'];
    if (path.startsWith('/rpa/task-job-management')) return ['rpa', 'rpa-task-job-management'];
    if (path.startsWith('/rpa/system-integration')) return ['rpa', 'rpa-system-integration'];
    if (path.startsWith('/rpa')) return ['rpa'];
    if (path.startsWith('/config-module/ip-management')) return ['ip-management'];
    if (path.startsWith('/config-module')) return ['config-module'];

    return [];
  };

  // 处理菜单展开/收起
  const handleOpenChange = (keys: string[]) => {
    setOpenKeys(keys);
  };

  // 主菜单项
  const mainMenuItems: MenuProps['items'] = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: 'cmdb',
      icon: <DatabaseOutlined />,
      label: 'CMDB',
      children: [
        {
          key: 'cmdb/query',
          label: '数据查询',
          icon: <DatabaseOutlined />,
        },
        {
          key: 'cmdb/discovery',
          label: 'ADS自动发现',
          icon: <RadarChartOutlined />,
        },
        {
          key: 'cmdb/inventory',
          label: '资产盘点',
          icon: <ScanOutlined />,
        },
        {
          key: 'cmdb/model',
          label: '模型管理',
          icon: <SettingOutlined />,
        },
      ],
    },
    {
      key: 'device',
      icon: <DesktopOutlined />,
      label: '设备管理',
      children: [
        {
          key: 'device-category',
          label: '设备分类',
          icon: <TagsOutlined />,
        },
        {
          key: 'credential-management',
          label: '凭证管理',
          icon: <SafetyCertificateOutlined />,
        },
      ],
    },
    {
      key: 'rpa',
      icon: <RobotOutlined />,
      label: '自动化RPA',
      children: [
        {
          key: 'rpa-atomic-components',
          label: '原子功能组件库',
          icon: <AppstoreOutlined />,
          children: [
            {
              key: 'rpa/atomic-components/device-connections',
              label: '设备连接组件',
            },
            {
              key: 'rpa/atomic-components/config-management',
              label: '配置管理组件',
            },
            {
              key: 'rpa/atomic-components/config-generator',
              label: '配置生成组件',
            },
            {
              key: 'rpa/atomic-components/data-collection',
              label: '日常巡检组件',
            },
            {
              key: 'rpa/atomic-components/penetration-test',
              label: '渗透测试组件',
            },
          ],
        },
        {
          key: 'rpa-process-orchestration',
          label: '流程编排引擎',
          icon: <CodeOutlined />,
          children: [
            {
              key: 'rpa/process-orchestration/visual-designer',
              label: '可视化流程设计器',
            },
            {
              key: 'rpa/process-orchestration/process-management',
              label: '流程管理',
            },
          ],
        },
        {
          key: 'rpa-task-job-management',
          label: '任务作业管理',
          icon: <ScheduleOutlined />,
          children: [
            {
              key: 'rpa/task-job-management/job-execution',
              label: '作业执行控制',
            },
            {
              key: 'rpa/task-job-management/job-monitoring',
              label: '作业监控与报告',
            },
            {
              key: 'rpa/task-job-management/penetration-reports',
              label: '渗透测试报告',
            },
          ],
        },
        {
          key: 'rpa-system-integration',
          label: '系统集成',
          icon: <ApiOutlined />,
          children: [
            {
              key: 'rpa/system-integration/monitoring-integration',
              label: '监控系统集成',
            },
            {
              key: 'rpa/system-integration/ticket-integration',
              label: '工单系统集成',
            },
          ],
        },
      ],
    },
    {
      key: 'config-module',
      icon: <FileTextOutlined />,
      label: '配置管理',
      children: [
        { key: 'config-module/summary', label: '配置摘要', icon: <BarChartOutlined /> },
        { key: 'config-module/management', label: '配置管理', icon: <DatabaseOutlined /> },
        { key: 'config-module/compliance', label: '合规检查', icon: <SafetyCertificateOutlined /> },
        { key: 'config-module/eos', label: '服务终止', icon: <SettingOutlined /> },
      ],
    },
    {
      key: 'ip-management',
      icon: <GlobalOutlined />,
      label: 'IP 管理',
      children: [
        { key: 'ip-management/aggregates', label: '聚合（Aggregates）', icon: <DatabaseOutlined /> },
        { key: 'ip-management/prefixes', label: '网段（Prefixes）', icon: <DatabaseOutlined /> },
        { key: 'ip-management/dhcp', label: 'DHCP 服务管理', icon: <SettingOutlined /> },
        { key: 'ip-management/import', label: '网络导入', icon: <BarChartOutlined /> },
      ],
    },
    {
      key: 'aiops',
      icon: <BulbOutlined />,
      label: 'AIOPS',
    },
  ];

  // 只有管理员才能看到系统管理菜单
  if (userRole === 'admin') {
    mainMenuItems.push({
      key: 'system',
      icon: <SettingOutlined />,
      label: '系统管理',
    });
  }

  // 用户菜单项
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'change-password',
      icon: <KeyOutlined />,
      label: '修改密码',
      onClick: () => navigate('/change-password'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  return (
    <AntLayout className="site-layout">
      <Sider trigger={null} collapsible collapsed={collapsed} width={220}>
        <div className="logo" style={{
          position: 'relative',
          color: 'white',
          fontWeight: 'bold',
          fontSize: collapsed ? '18px' : '20px',
          textAlign: 'center',
          padding: '8px 0'
        }}>
          {!collapsed ? 'NetOps平台' : 'NO'}
          <div style={{
            position: 'absolute',
            bottom: '0',
            left: '16px',
            right: '16px',
            height: '3px',
            background: 'linear-gradient(90deg, #1890ff, #52c41a)',
            borderRadius: '3px',
            boxShadow: '0 1px 3px rgba(24, 144, 255, 0.3)'
          }}></div>
        </div>
        <Menu
          ref={menuRef}
          theme="dark"
          mode="inline"
          selectedKeys={getSelectedKey()}
          openKeys={openKeys}
          onOpenChange={handleOpenChange}
          onClick={({ key }) => {
            // 处理不同的路由
            if (key === 'dashboard') {
              handleMenuClick('/');
            } else if (key === 'device-category') {
              handleMenuClick('/device/category');
            } else if (key === 'credential-management') {
              handleMenuClick('/device/credentials');
            } else if (typeof key === 'string' && key.startsWith('ip-management/')) {
              handleMenuClick(`/config-module/${key}`);
            } else {
              // 导航到相应路由，但保持当前展开的菜单状态
              const currentOpenKeys = [...openKeys];
              handleMenuClick(`/${key}`);
              
              // 判断是否是三级菜单项（包含两个斜杠）
              if (key.split('/').length > 2) {
                // 确保对应的父级菜单保持展开
                const parentKey = key.split('/')[0] + '-' + key.split('/')[1];
                if (!currentOpenKeys.includes('rpa')) {
                  currentOpenKeys.push('rpa');
                }
                if (!currentOpenKeys.includes(parentKey)) {
                  currentOpenKeys.push(parentKey);
                }
                // 使用setTimeout确保在路由切换后依然保持菜单展开状态
                setTimeout(() => {
                  setOpenKeys(currentOpenKeys);
                }, 0);
              }
            }
          }}
          items={mainMenuItems}
        />
      </Sider>
      <AntLayout>
        <Header className="site-layout-background" style={{ padding: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 24px' }}>
            {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
              className: 'trigger',
              onClick: toggle,
              style: { fontSize: '18px' }
            })}
            <div className="header-menu">
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <Button type="text">
                  <Avatar icon={<UserOutlined />} style={{ marginRight: '8px' }} />
                  {username || '用户'}
                </Button>
              </Dropdown>
            </div>
          </div>
        </Header>
        <Content className="content-container page-container">
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout; 