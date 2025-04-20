import React, { useState } from 'react';
import { Card, Row, Col, Statistic, Typography, Tabs, Table, Tag, Progress, Button, Space, DatePicker, Select } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { AlertOutlined, BulbOutlined, RiseOutlined, FallOutlined, ExclamationCircleOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;
const { RangePicker } = DatePicker;
const { Option } = Select;

// 模拟数据 - 网络性能预测
const performanceData = [
  { name: '00:00', actual: 45, predicted: 48 },
  { name: '02:00', actual: 30, predicted: 32 },
  { name: '04:00', actual: 25, predicted: 24 },
  { name: '06:00', actual: 40, predicted: 38 },
  { name: '08:00', actual: 65, predicted: 62 },
  { name: '10:00', actual: 78, predicted: 80 },
  { name: '12:00', actual: 85, predicted: 83 },
  { name: '14:00', actual: 80, predicted: 82 },
  { name: '16:00', actual: 75, predicted: 78 },
  { name: '18:00', actual: 82, predicted: 80 },
  { name: '20:00', actual: 70, predicted: 72 },
  { name: '22:00', actual: 55, predicted: 58 },
  { name: '00:00', actual: null, predicted: 45 },
  { name: '02:00', actual: null, predicted: 32 },
  { name: '04:00', actual: null, predicted: 25 },
  { name: '06:00', actual: null, predicted: 42 },
];

// 模拟数据 - 异常检测
const anomalyData = [
  {
    key: '1',
    device: 'Core-Router-01',
    metric: 'CPU使用率',
    value: '92%',
    threshold: '80%',
    time: '2025-03-09 20:15:30',
    severity: '严重',
    status: '未处理',
  },
  {
    key: '2',
    device: 'Switch-Floor3-01',
    metric: '内存使用率',
    value: '85%',
    threshold: '80%',
    time: '2025-03-09 19:45:12',
    severity: '警告',
    status: '已处理',
  },
  {
    key: '3',
    device: 'Core-Router-01',
    metric: '网络延迟',
    value: '120ms',
    threshold: '100ms',
    time: '2025-03-09 18:30:45',
    severity: '警告',
    status: '未处理',
  },
];

// 模拟数据 - 根因分析
const rootCauseData = [
  {
    key: '1',
    issue: '网络延迟增加',
    time: '2025-03-09 18:30:45',
    affectedDevices: ['Core-Router-01', 'Switch-Floor3-01'],
    rootCause: '核心路由器CPU过载',
    confidence: 85,
    recommendation: '增加路由器资源或优化路由配置',
  },
  {
    key: '2',
    issue: '应用响应缓慢',
    time: '2025-03-08 14:20:10',
    affectedDevices: ['Server-App-01', 'Server-DB-01'],
    rootCause: '数据库连接池耗尽',
    confidence: 92,
    recommendation: '增加数据库连接池大小',
  },
];

const AIOPS: React.FC = () => {
  const [timeRange, setTimeRange] = useState('24h');
  const [deviceFilter, setDeviceFilter] = useState('all');

  const handleTimeRangeChange = (value: string) => {
    setTimeRange(value);
    // 实际项目中，这里应该根据时间范围重新获取数据
  };

  const handleDeviceFilterChange = (value: string) => {
    setDeviceFilter(value);
    // 实际项目中，这里应该根据设备筛选数据
  };

  const anomalyColumns = [
    {
      title: '设备',
      dataIndex: 'device',
      key: 'device',
    },
    {
      title: '指标',
      dataIndex: 'metric',
      key: 'metric',
    },
    {
      title: '当前值',
      dataIndex: 'value',
      key: 'value',
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
    },
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (text: string) => {
        const color = text === '严重' ? 'red' : text === '警告' ? 'orange' : 'blue';
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (text: string) => {
        const color = text === '未处理' ? 'red' : 'green';
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button type="link" size="small">
            查看详情
          </Button>
          {record.status === '未处理' && (
            <Button type="link" size="small">
              标记为已处理
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const rootCauseColumns = [
    {
      title: '问题',
      dataIndex: 'issue',
      key: 'issue',
    },
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
    },
    {
      title: '受影响设备',
      dataIndex: 'affectedDevices',
      key: 'affectedDevices',
      render: (devices: string[]) => (
        <>
          {devices.map(device => (
            <Tag key={device}>{device}</Tag>
          ))}
        </>
      ),
    },
    {
      title: '根本原因',
      dataIndex: 'rootCause',
      key: 'rootCause',
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (value: number) => (
        <Progress 
          percent={value} 
          size="small" 
          status={value > 80 ? 'success' : 'normal'} 
        />
      ),
    },
    {
      title: '建议',
      dataIndex: 'recommendation',
      key: 'recommendation',
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Button type="link" size="small">
          应用建议
        </Button>
      ),
    },
  ];

  return (
    <div className="page-container">
      <Title level={2}>AIOPS - AI运维</Title>
      
      <Row gutter={[16, 16]} className="section-container">
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="已检测异常"
              value={8}
              valueStyle={{ color: '#cf1322' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="预测准确率"
              value={92.5}
              precision={1}
              valueStyle={{ color: '#3f8600' }}
              prefix={<BulbOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="性能趋势"
              value="上升"
              valueStyle={{ color: '#3f8600' }}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="stat-card">
            <Statistic
              title="未解决问题"
              value={2}
              valueStyle={{ color: '#faad14' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>
      
      <Row gutter={[16, 16]} className="section-container">
        <Col span={12}>
          <Card title="异常检测" className="chart-card">
            <Table 
              columns={anomalyColumns} 
              dataSource={anomalyData} 
              pagination={false}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="性能预测" className="chart-card">
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <LineChart
                  data={performanceData}
                  margin={{
                    top: 5,
                    right: 30,
                    left: 20,
                    bottom: 5,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="actual" 
                    stroke="#8884d8" 
                    name="实际值" 
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 8 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="predicted" 
                    stroke="#ff7300" 
                    name="预测值" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>
      
      <Row gutter={[16, 16]} className="section-container">
        <Col span={24}>
          <Card title="告警分析" className="list-card custom-table">
            <Table 
              columns={rootCauseColumns} 
              dataSource={rootCauseData} 
              pagination={false}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AIOPS; 