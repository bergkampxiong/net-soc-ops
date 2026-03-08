import React, { useState, useEffect, useMemo } from 'react';
import { Row, Col, Card, Statistic, Table, Typography, Badge, List, Tag, Space, Spin, Empty } from 'antd';
import {
  DashboardOutlined,
  DatabaseOutlined,
  RobotOutlined,
  AlertOutlined,
  ArrowUpOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  WarningOutlined,
  LineChartOutlined,
  CloudOutlined,
  InfoCircleOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import request from '../utils/request';
import type { JobExecutionListItem, JobExecutionStatsResponse } from './rpa/job-execution/types';

const { Title, Text } = Typography;

// ---------- 类型定义 ----------
interface ConfigStats {
  device_count: number;
  backup_24h_success: number;
  backup_24h_fail: number;
  backup_7d_success: number;
  backup_7d_fail: number;
  change_count_7d: number;
  compliance_pass_rate?: number;
}

interface BackupsByDayItem {
  date: string;
  count: number;
}

interface BackupsBySourceItem {
  name: string;
  value: number;
}

interface RecentBackup {
  id: number;
  device_id: string;
  device_name?: string;
  device_host?: string;
  source?: string;
  created_at?: string;
}

interface AssetStatistics {
  total_assets: number;
  by_device_type: Record<string, number>;
  by_vendor?: Record<string, number>;
  by_department?: Record<string, number>;
  by_location?: Record<string, number>;
  by_status?: Record<string, number>;
}

interface AlertItem {
  id: number;
  severity?: string;
  alert_title?: string;
  message?: string;
  node_name?: string;
  alert_time?: string;
  created_at?: string;
}

// 设备类型饼图颜色
const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

// 最近 7 天日期范围，供作业统计使用
function getLast7Days(): { date_from: string; date_to: string } {
  const now = new Date();
  const to = now.toISOString().slice(0, 10);
  const from = new Date(now);
  from.setDate(from.getDate() - 6);
  return { date_from: from.toISOString().slice(0, 10), date_to: to };
}

// 告警严重性 -> 中文与颜色
function severityDisplay(severity: string | undefined): { text: string; color: string; icon: React.ReactNode } {
  const s = (severity || '').toLowerCase();
  if (s === 'critical' || s === '严重') {
    return { text: '严重', color: 'red', icon: <AlertOutlined /> };
  }
  if (s === 'warning' || s === '警告') {
    return { text: '警告', color: 'orange', icon: <WarningOutlined /> };
  }
  return { text: '信息', color: 'blue', icon: <InfoCircleOutlined /> };
}

// 作业执行状态 -> 展示
function jobStatusDisplay(status: string): { text: string; status: 'success' | 'processing' | 'warning' } {
  if (status === 'completed') return { text: '已完成', status: 'success' };
  if (status === 'running') return { text: '执行中', status: 'processing' };
  if (status === 'failed') return { text: '失败', status: 'warning' };
  return { text: status, status: 'warning' };
}

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [configStats, setConfigStats] = useState<ConfigStats | null>(null);
  const [backupsByDay, setBackupsByDay] = useState<BackupsByDayItem[]>([]);
  const [backupsBySource, setBackupsBySource] = useState<BackupsBySourceItem[]>([]);
  const [recentBackups, setRecentBackups] = useState<RecentBackup[]>([]);
  const [assetStats, setAssetStats] = useState<AssetStatistics | null>(null);
  const [jobStats, setJobStats] = useState<JobExecutionStatsResponse | null>(null);
  const [jobExecutions, setJobExecutions] = useState<JobExecutionListItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertsLoadError, setAlertsLoadError] = useState(false);
  const [cmdbLoadError, setCmdbLoadError] = useState(false);
  const [jobLoadError, setJobLoadError] = useState(false);

  useEffect(() => {
    const { date_from, date_to } = getLast7Days();
    const fetchAll = async () => {
      setLoading(true);
      setAlertsLoadError(false);
      setCmdbLoadError(false);
      setJobLoadError(false);

      try {
        const [
          configStatsRes,
          backupsByDayRes,
          backupsBySourceRes,
          recentBackupsRes,
          assetStatsRes,
          jobStatsRes,
          jobListRes,
          alertsRes,
        ] = await Promise.allSettled([
          request.get('/config-module/summary/stats'),
          request.get('/config-module/summary/backups-by-day?days=7'),
          request.get('/config-module/summary/backups-by-source?days=7'),
          request.get('/config-module/summary/recent-backups?limit=10'),
          request.get('/cmdb/assets/statistics'),
          request.get('/job-executions/stats', { params: { date_from, date_to } }),
          request.get('/job-executions', { params: { skip: 0, limit: 10 } }),
          request.get('/monitoring-integration/alerts', { params: { limit: 20 } }),
        ]);

        const unwrap = (r: PromiseSettledResult<any>) =>
          r.status === 'fulfilled' ? r.value?.data?.data ?? r.value?.data ?? r.value : null;

        const s = unwrap(configStatsRes);
        if (s && typeof s === 'object' && 'device_count' in s) setConfigStats(s as ConfigStats);
        else setConfigStats(null);

        const dayList = unwrap(backupsByDayRes);
        setBackupsByDay(Array.isArray(dayList) ? dayList : []);

        const srcList = unwrap(backupsBySourceRes);
        setBackupsBySource(Array.isArray(srcList) ? srcList : []);

        const recentList = unwrap(recentBackupsRes);
        setRecentBackups(Array.isArray(recentList) ? recentList : []);

        const asset = unwrap(assetStatsRes);
        if (asset && typeof asset === 'object') setAssetStats(asset as AssetStatistics);
        else {
          setAssetStats(null);
          if (assetStatsRes.status === 'rejected') setCmdbLoadError(true);
        }

        const jobS = unwrap(jobStatsRes);
        if (jobS && typeof jobS === 'object' && 'total' in jobS) setJobStats(jobS as JobExecutionStatsResponse);
        else {
          setJobStats(null);
          if (jobStatsRes.status === 'rejected') setJobLoadError(true);
        }

        const jobList = unwrap(jobListRes);
        const items = jobList?.items ?? (Array.isArray(jobList) ? jobList : []);
        setJobExecutions(Array.isArray(items) ? items : []);

        const alertsData = unwrap(alertsRes);
        const alertItems = alertsData?.items ?? (Array.isArray(alertsData) ? alertsData : []);
        setAlerts(Array.isArray(alertItems) ? alertItems : []);
        if (alertsRes.status === 'rejected') setAlertsLoadError(true);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const deviceTotal = assetStats?.total_assets ?? configStats?.device_count ?? 0;
  const alertTotal = alerts.length;
  const backupsByDayChartData = useMemo(
    () =>
      backupsByDay.map((d) => ({ name: d.date, 备份数: d.count })),
    [backupsByDay]
  );
  const deviceTypePieData = useMemo(() => {
    const by = assetStats?.by_device_type;
    if (!by || typeof by !== 'object') return [];
    return Object.entries(by).map(([name, value]) => ({ name, value })).filter((d) => d.value > 0);
  }, [assetStats]);
  const alertsBySeverityPieData = useMemo(() => {
    const map: Record<string, number> = {};
    alerts.forEach((a) => {
      const key = severityDisplay(a.severity).text;
      map[key] = (map[key] || 0) + 1;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [alerts]);

  const alertColumns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      render: (text: string) => {
        const { text: label, color, icon } = severityDisplay(text);
        return (
          <Tag color={color} icon={icon}>
            {label}
          </Tag>
        );
      },
    },
    {
      title: '节点',
      dataIndex: 'node_name',
      key: 'node_name',
      render: (t: string) => (t ? <Text strong>{t}</Text> : '-'),
    },
    {
      title: '消息',
      key: 'message',
      render: (_: unknown, r: AlertItem) => r.alert_title || r.message || '-',
    },
    {
      title: '时间',
      dataIndex: 'alert_time',
      key: 'alert_time',
      render: (t: string, r: AlertItem) => (
        <Text type="secondary">{t || r.created_at || '-'}</Text>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="page-container" style={{ padding: 24, textAlign: 'center', minHeight: 320 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="page-container">
      <Title level={2}>仪表盘</Title>

      <Row gutter={[16, 16]} className="section-container">
        <Col span={24}>
          <Card className="card-container welcome-card">
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <DashboardOutlined style={{ fontSize: '36px', color: '#1890ff', marginRight: '16px' }} />
              <div>
                <Title level={4} style={{ margin: 0 }}>欢迎使用 NetOps 平台</Title>
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
              value={deviceTotal}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable className="stat-card">
            <Statistic
              title={<span style={{ fontSize: 16 }}>配置备份（7 天）</span>}
              value={configStats?.backup_7d_success ?? 0}
              prefix={<SaveOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a', fontWeight: 'bold' }}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">
                <ArrowUpOutlined style={{ color: '#52c41a' }} /> 24h 内 {configStats?.backup_24h_success ?? 0} 次
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable className="stat-card">
            <Statistic
              title={<span style={{ fontSize: 16 }}>作业执行（7 天）</span>}
              value={jobStats?.total ?? 0}
              prefix={<RobotOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#722ed1', fontWeight: 'bold' }}
            />
            <div style={{ marginTop: 8 }}>
              <Badge
                status={jobLoadError ? 'error' : 'processing'}
                text={jobLoadError ? '加载失败' : `成功率 ${((jobStats?.success_rate ?? 0) * 100).toFixed(0)}%`}
              />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card hoverable className="stat-card">
            <Statistic
              title={<span style={{ fontSize: 16 }}>活跃告警</span>}
              value={alertTotal}
              prefix={<AlertOutlined style={{ color: alertTotal > 0 ? '#f5222d' : '#52c41a' }} />}
              valueStyle={{ color: alertTotal > 0 ? '#f5222d' : '#52c41a', fontWeight: 'bold' }}
            />
            <div style={{ marginTop: 8 }}>
              {alertsLoadError ? (
                <Text type="danger">告警接口加载失败</Text>
              ) : (
                <Text type={alertTotal > 0 ? 'danger' : 'secondary'}>
                  {alertTotal > 0 ? '请及时处理' : '当前无告警'}
                </Text>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="section-container">
        <Col xs={24} lg={12}>
          <Card title="配置备份趋势" className="chart-card">
            <div style={{ height: 300 }}>
              {backupsByDayChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={backupsByDayChartData}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <RechartsTooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="备份数"
                      stroke="#8884d8"
                      fill="#8884d8"
                      fillOpacity={0.3}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="暂无备份数据" style={{ marginTop: 80 }} />
              )}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="设备类型分布" className="chart-card">
            <div style={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              {deviceTypePieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={deviceTypePieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {deviceTypePieData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Empty description={cmdbLoadError ? 'CMDB 加载失败' : '暂无设备类型数据'} style={{ marginTop: 80 }} />
              )}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="section-container">
        <Col xs={24} lg={12}>
          <Card title="告警按严重性" className="chart-card">
            <div style={{ height: 220 }}>
              {alertsBySeverityPieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={alertsBySeverityPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      dataKey="value"
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      {alertsBySeverityPieData.map((_, index) => (
                        <Cell key={`cell-s-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Empty description={alertsLoadError ? '告警加载失败' : '暂无告警'} style={{ marginTop: 60 }} />
              )}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="备份来源分布（7 天）" className="chart-card">
            <div style={{ height: 220 }}>
              {backupsBySource.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={backupsBySource}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      dataKey="value"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {backupsBySource.map((_, index) => (
                        <Cell key={`cell-src-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="暂无备份来源数据" style={{ marginTop: 60 }} />
              )}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="section-container">
        <Col xs={24} lg={12}>
          <Card title="最近告警" className="list-card custom-table">
            {alertsLoadError ? (
              <Empty description="告警列表加载失败" />
            ) : (
              <Table
                columns={alertColumns}
                dataSource={alerts.map((a) => ({ ...a, key: a.id }))}
                pagination={false}
                size="middle"
                className="custom-table"
                locale={{ emptyText: '暂无告警' }}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="最近任务" className="list-card">
            {jobLoadError ? (
              <Empty description="任务列表加载失败" />
            ) : (
              <List
                itemLayout="horizontal"
                dataSource={jobExecutions}
                locale={{ emptyText: '暂无执行记录' }}
                renderItem={(item) => {
                  const statusStr = String(item.status);
                  const { text, status: badgeStatus } = jobStatusDisplay(statusStr);
                  const icon =
                    statusStr === 'completed' ? (
                      <CheckCircleOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
                    ) : statusStr === 'running' ? (
                      <SyncOutlined spin style={{ fontSize: '24px', color: '#1890ff' }} />
                    ) : (
                      <ClockCircleOutlined style={{ fontSize: '24px', color: '#faad14' }} />
                    );
                  return (
                    <List.Item>
                      <List.Item.Meta
                        avatar={icon}
                        title={<span>{item.job_name || `作业 #${item.job_id}`}</span>}
                        description={
                          <Space>
                            <Badge status={badgeStatus} text={text} />
                            <Text type="secondary">{item.start_time ? item.start_time.slice(0, 19).replace('T', ' ') : '-'}</Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  );
                }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
