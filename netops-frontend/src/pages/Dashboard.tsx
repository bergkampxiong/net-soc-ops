import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Typography, Badge, Progress, Divider, Avatar, List, Tag, Tooltip, Space } from 'antd';
import { 
  DashboardOutlined, 
  DatabaseOutlined, 
  RobotOutlined, 
  BulbOutlined,
  AlertOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  WarningOutlined,
  LineChartOutlined,
  CloudOutlined,
  DesktopOutlined,
  WifiOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import PageHeader from '../components/PageHeader';

const { Title, Text } = Typography;

// 模拟数据 - 告警
const alertData = [
  {
    key: '1',
    level: '严重',
    device: 'Core-Router-01',
    message: 'CPU使用率超过90%',
    time: '2025-03-09 20:15:30',
  },
  {
    key: '2',
    level: '警告',
    device: 'Switch-Floor3-01',
    message: '内存使用率超过80%',
    time: '2025-03-09 19:45:12',
  },
  {
    key: '3',
    level: '信息',
    device: 'Firewall-Main',
    message: '配置已更改',
    time: '2025-03-09 18:30:45',
  },
];

// 模拟数据 - 网络流量
const networkData = [
  { name: '00:00', 入站流量: 120, 出站流量: 110 },
  { name: '02:00', 入站流量: 100, 出站流量: 90 },
  { name: '04:00', 入站流量: 80, 出站流量: 85 },
  { name: '06:00', 入站流量: 150, 出站流量: 120 },
  { name: '08:00', 入站流量: 280, 出站流量: 250 },
  { name: '10:00', 入站流量: 320, 出站流量: 310 },
  { name: '12:00', 入站流量: 350, 出站流量: 330 },
  { name: '14:00', 入站流量: 310, 出站流量: 290 },
  { name: '16:00', 入站流量: 290, 出站流量: 270 },
  { name: '18:00', 入站流量: 270, 出站流量: 250 },
  { name: '20:00', 入站流量: 220, 出站流量: 210 },
  { name: '22:00', 入站流量: 150, 出站流量: 140 },
];

// 模拟数据 - 设备类型分布
const deviceTypeData = [
  { name: '路由器', value: 35 },
  { name: '交换机', value: 120 },
  { name: '防火墙', value: 18 },
  { name: '服务器', value: 83 },
];

// 模拟数据 - 最近任务
const recentTasksData = [
  { 
    id: 1, 
    name: '网络设备配置备份', 
    status: 'success', 
    time: '2025-03-09 20:00:00',
    icon: <CloudOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
  },
  { 
    id: 2, 
    name: '带宽使用率监控', 
    status: 'success', 
    time: '2025-03-09 19:00:00',
    icon: <LineChartOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
  },
  { 
    id: 3, 
    name: '防火墙规则更新', 
    status: 'processing', 
    time: '2025-03-09 18:30:00',
    icon: <SyncOutlined style={{ fontSize: '24px', color: '#faad14' }} />
  },
  { 
    id: 4, 
    name: '网络设备固件升级', 
    status: 'waiting', 
    time: '2025-03-09 21:00:00',
    icon: <ClockCircleOutlined style={{ fontSize: '24px', color: '#722ed1' }} />
  },
];

// 告警表格列定义
const columns = [
  {
    title: '级别',
    dataIndex: 'level',
    key: 'level',
    render: (text: string) => {
      let color = '';
      let icon = null;
      
      if (text === '严重') {
        color = 'red';
        icon = <AlertOutlined />;
      } else if (text === '警告') {
        color = 'orange';
        icon = <WarningOutlined />;
      } else {
        color = 'blue';
        icon = <InfoCircleOutlined />;
      }
      
      return (
        <Tag color={color} icon={icon}>
          {text}
        </Tag>
      );
    },
  },
  {
    title: '设备',
    dataIndex: 'device',
    key: 'device',
    render: (text: string) => (
      <Text strong>{text}</Text>
    ),
  },
  {
    title: '消息',
    dataIndex: 'message',
    key: 'message',
  },
  {
    title: '时间',
    dataIndex: 'time',
    key: 'time',
    render: (text: string) => (
      <Text type="secondary">{text}</Text>
    ),
  },
];

// 设备类型饼图颜色
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

// 任务状态图标映射
const statusIcons = {
  success: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  processing: <SyncOutlined spin style={{ color: '#1890ff' }} />,
  waiting: <ClockCircleOutlined style={{ color: '#faad14' }} />,
};

const Dashboard: React.FC = () => {
  const [currentTime, setCurrentTime] = useState(new Date());

  // 更新当前时间
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => {
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="page-container">
      <Title level={2}>仪表盘</Title>
      
      <Row gutter={[16, 16]} className="section-container">
        <Col span={24}>
          <Card className="card-container welcome-card">
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <DashboardOutlined style={{ fontSize: '36px', color: '#1890ff', marginRight: '16px' }} />
              <div>
                <Title level={4} style={{ margin: 0 }}>欢迎使用NetOps平台</Title>
                <Text>网络运维自动化平台，提高网络运维效率和可靠性</Text>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="section-container">
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="设备总数"
              value={256}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable className="stat-card">
            <Statistic
              title={<span style={{ fontSize: 16 }}>自动化任务</span>}
              value={42}
              prefix={<RobotOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a', fontWeight: 'bold' }}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">
                <ArrowUpOutlined style={{ color: '#52c41a' }} /> 本周执行 12 次
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable className="stat-card">
            <Statistic
              title={<span style={{ fontSize: 16 }}>AI预测</span>}
              value={18}
              prefix={<BulbOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#722ed1', fontWeight: 'bold' }}
            />
            <div style={{ marginTop: 8 }}>
              <Badge status="processing" text="预测准确率 92%" />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable className="stat-card">
            <Statistic
              title={<span style={{ fontSize: 16 }}>活跃告警</span>}
              value={3}
              prefix={<AlertOutlined style={{ color: '#f5222d' }} />}
              valueStyle={{ color: '#f5222d', fontWeight: 'bold' }}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="danger">
                <ArrowDownOutlined /> 较昨日减少 2 个
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="section-container">
        <Col xs={24} lg={12}>
          <Card title="网络流量趋势" className="chart-card">
            <div style={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={networkData}
                  margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <RechartsTooltip />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="入站流量" 
                    stroke="#8884d8" 
                    fill="#8884d8" 
                    fillOpacity={0.3} 
                  />
                  <Area 
                    type="monotone" 
                    dataKey="出站流量" 
                    stroke="#82ca9d" 
                    fill="#82ca9d" 
                    fillOpacity={0.3} 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="设备类型分布" className="chart-card">
            <div style={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={deviceTypeData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  >
                    {deviceTypeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="section-container">
        <Col xs={24} lg={12}>
          <Card title="最近告警" className="list-card custom-table">
            <Table 
              columns={columns} 
              dataSource={alertData} 
              pagination={false}
              size="middle"
              className="custom-table"
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="最近任务" className="list-card">
            <List
              itemLayout="horizontal"
              dataSource={recentTasksData}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    avatar={item.icon}
                    title={<a href="#">{item.name}</a>}
                    description={
                      <Space>
                        <Badge 
                          status={
                            item.status === 'success' ? 'success' : 
                            item.status === 'processing' ? 'processing' : 'warning'
                          } 
                          text={
                            item.status === 'success' ? '已完成' : 
                            item.status === 'processing' ? '进行中' : '等待中'
                          } 
                        />
                        <Divider type="vertical" />
                        <Text type="secondary">{item.time}</Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard; 