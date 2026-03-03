import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Spin,
  message,
  Row,
  Col,
  Statistic,
  Typography,
  Space,
} from 'antd';
import {
  CloudServerOutlined,
  SaveOutlined,
  CalendarOutlined,
  SyncOutlined,
  PieChartOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { formatBeijingToSecond } from '@/utils/formatTime';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import request from '../../utils/request';

const { Title, Text } = Typography;

interface Stats {
  device_count: number;
  backup_24h_success: number;
  backup_24h_fail: number;
  backup_7d_success: number;
  backup_7d_fail: number;
  change_count_7d: number;
  compliance_pass_rate?: number;
}

interface RecentBackup {
  id: number;
  device_id: string;
  device_name?: string;
  device_host?: string;
  source?: string;
  created_at?: string;
}

const CHART_COLORS = ['#1890ff', '#52c41a', '#faad14', '#722ed1', '#eb2f96'];

const ConfigModuleSummary: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentBackups, setRecentBackups] = useState<RecentBackup[]>([]);
  const [byDay, setByDay] = useState<{ date: string; count: number }[]>([]);
  const [bySource, setBySource] = useState<{ name: string; value: number }[]>([]);

  useEffect(() => {
    const fetch = async () => {
      try {
        const [statsRes, recentRes, byDayRes, bySourceRes] = await Promise.all([
          request.get('/config-module/summary/stats'),
          request.get('/config-module/summary/recent-backups?limit=10'),
          request.get('/config-module/summary/backups-by-day?days=7'),
          request.get('/config-module/summary/backups-by-source?days=7'),
        ]);
        const s = statsRes.data?.data ?? statsRes.data;
        if (s && typeof s === 'object' && 'device_count' in s) setStats(s as Stats);
        else setStats(null);

        const list = recentRes.data?.data ?? recentRes.data;
        setRecentBackups(Array.isArray(list) ? list : []);

        const dayList = byDayRes.data?.data ?? byDayRes.data;
        setByDay(Array.isArray(dayList) ? dayList : []);

        const srcList = bySourceRes.data?.data ?? bySourceRes.data;
        setBySource(Array.isArray(srcList) ? srcList : []);
      } catch (e) {
        message.error('加载配置摘要失败');
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center', minHeight: 320 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        配置摘要
      </Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%)', border: 'none' }}>
            <Statistic
              title={<Space><CloudServerOutlined /> 已纳管设备数</Space>}
              value={stats?.device_count ?? 0}
              valueStyle={{ color: '#1890ff', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #f6ffed 0%, #b7eb8f 100%)', border: 'none' }}>
            <Statistic
              title={<Space><SaveOutlined /> 24h 备份数</Space>}
              value={stats?.backup_24h_success ?? 0}
              valueStyle={{ color: '#52c41a', fontSize: 28 }}
            />
            {(stats?.backup_24h_fail ?? 0) > 0 && (
              <Text type="secondary" style={{ fontSize: 12 }}>失败 {stats?.backup_24h_fail}</Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #fff7e6 0%, #ffd591 100%)', border: 'none' }}>
            <Statistic
              title={<Space><CalendarOutlined /> 7 天备份数</Space>}
              value={stats?.backup_7d_success ?? 0}
              valueStyle={{ color: '#fa8c16', fontSize: 28 }}
            />
            {(stats?.backup_7d_fail ?? 0) > 0 && (
              <Text type="secondary" style={{ fontSize: 12 }}>失败 {stats?.backup_7d_fail}</Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card size="small" style={{ background: 'linear-gradient(135deg, #f9f0ff 0%, #d3adf7 100%)', border: 'none' }}>
            <Statistic
              title={<Space><SyncOutlined /> 7 天变更次数</Space>}
              value={stats?.change_count_7d ?? 0}
              valueStyle={{ color: '#722ed1', fontSize: 28 }}
            />
          </Card>
        </Col>
        {stats?.compliance_pass_rate != null && (
          <Col xs={24} sm={12} md={8} lg={4}>
            <Card size="small" style={{ background: 'linear-gradient(135deg, #e6fffb 0%, #87e8de 100%)', border: 'none' }}>
              <Statistic
                title="合规通过率"
                value={((stats.compliance_pass_rate ?? 0) * 100).toFixed(1)}
                suffix="%"
                valueStyle={{ color: '#13c2c2', fontSize: 28 }}
              />
            </Card>
          </Col>
        )}
      </Row>

      {/* 图表区：趋势 + 来源分布 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card
            title={<Space><BarChartOutlined /> 近 7 天备份趋势</Space>}
            size="small"
            style={{ height: 320 }}
          >
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={byDay} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1890ff" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#1890ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value: number) => [value, '备份数']}
                  labelFormatter={(label) => `日期: ${label}`}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#1890ff"
                  fillOpacity={1}
                  fill="url(#colorCount)"
                  name="备份数"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            title={<Space><PieChartOutlined /> 近 7 天按来源分布</Space>}
            size="small"
            style={{ height: 320 }}
          >
            {bySource.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={bySource}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {bySource.map((_, index) => (
                      <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [value, '次数']} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                暂无数据
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 最近备份表格 */}
      <Card title="最近备份">
        <Table
          dataSource={recentBackups}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            { title: '设备标识', dataIndex: 'device_id', key: 'device_id', width: 120, ellipsis: true },
            { title: '设备名', dataIndex: 'device_name', key: 'device_name', width: 120, ellipsis: true },
            { title: '主机', dataIndex: 'device_host', key: 'device_host', width: 120, ellipsis: true },
            { title: '来源', dataIndex: 'source', key: 'source', width: 80 },
            { title: '备份时间', dataIndex: 'created_at', key: 'created_at', width: 180, render: (t: string) => formatBeijingToSecond(t) },
            {
              title: '操作',
              key: 'action',
              width: 80,
              render: (_, r) => (
                <a onClick={() => navigate(`/config-module/management?device_id=${encodeURIComponent(r.device_id)}`)}>
                  查看
                </a>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default ConfigModuleSummary;
