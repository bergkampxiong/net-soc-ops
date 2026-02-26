import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Button, Select, message, Radio, Alert, Typography } from 'antd';
import { Line } from '@ant-design/charts';
import { getPoolStats, getPoolMetrics, cleanupConnections } from '../../../../services/poolConfig';
import type { PoolStats } from '../../../../services/poolConfig';

const { Option } = Select;
const { Text } = Typography;

const DEFAULT_STATS: PoolStats = {
  total_connections: 0,
  active_connections: 0,
  idle_connections: 0,
  waiting_connections: 0,
  max_wait_time: 0,
  avg_wait_time: 0,
  created_at: '',
};

const PoolMonitor: React.FC = () => {
  const [stats, setStats] = useState<PoolStats | null>(DEFAULT_STATS);
  const [metrics, setMetrics] = useState<any>({ connection_history: [], error_history: [], resource_usage: [] });
  const [timeRange, setTimeRange] = useState('1h');
  const [loading, setLoading] = useState(false);
  const [poolType, setPoolType] = useState<'redis' | 'device'>('device');
  const [loadError, setLoadError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const [statsData, metricsData] = await Promise.all([
        getPoolStats(poolType),
        getPoolMetrics(timeRange, poolType)
      ]);
      setStats(statsData ?? DEFAULT_STATS);
      setMetrics(metricsData ?? { connection_history: [], error_history: [], resource_usage: [] });
    } catch (error) {
      message.error('获取监控数据失败');
      console.error('获取监控数据失败:', error);
      setLoadError('获取监控数据失败，请检查后端服务与 Redis。');
      setStats(DEFAULT_STATS);
      setMetrics({ connection_history: [], error_history: [], resource_usage: [] });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 60000); // 每1分钟更新一次
    return () => clearInterval(timer);
  }, [timeRange, poolType]);

  const handleCleanup = async () => {
    try {
      await cleanupConnections(poolType);
      message.success('异常连接清理成功');
      fetchData();
    } catch (error) {
      message.error('清理异常连接失败');
      console.error('清理异常连接失败:', error);
    }
  };

  const config = {
    data: metrics?.connection_history || [],
    xField: 'timestamp',
    yField: 'value',
    seriesField: 'type',
    smooth: true,
    animation: false,
    point: {
      size: 3,
      shape: 'circle',
    },
    tooltip: {
      showCrosshairs: true,
    },
  };

  return (
    <div>
      <Alert
        type="info"
        showIcon
        message="与 SSH 连接配置的关系"
        description={
          <>
            <Text>本页统计的是<strong>网络设备连接池</strong>，即流程/作业执行时通过<strong>上方「SSH 连接配置」</strong>中的连接模板建立的 SSH 连接。选择「网络设备连接池」可查看当前活动连接数、总连接数等；流程发布到「作业执行控制」后执行时，任务中的设备连接会实时计入本统计；「清理异常连接」将清空池中所有 SSH 连接并重置计数。</Text>
          </>
        }
        style={{ marginBottom: 16 }}
      />
      {loadError && (
        <Alert type="warning" showIcon message={loadError} style={{ marginBottom: 16 }} />
      )}
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span>连接池状态</span>
                <Radio.Group 
                  value={poolType} 
                  onChange={(e) => setPoolType(e.target.value as 'redis' | 'device')}
                  buttonStyle="solid"
                >
                  <Radio.Button value="redis">Redis通信连接池</Radio.Button>
                  <Radio.Button value="device">网络设备连接池</Radio.Button>
                </Radio.Group>
              </div>
            }
            extra={
              <div style={{ display: 'flex', gap: '16px' }}>
                <Select
                  value={timeRange}
                  onChange={setTimeRange}
                  style={{ width: 120 }}
                >
                  <Option value="1h">最近1小时</Option>
                  <Option value="6h">最近6小时</Option>
                  <Option value="24h">最近24小时</Option>
                </Select>
                <Button type="primary" danger onClick={handleCleanup}>
                  清理异常连接
                </Button>
              </div>
            }
          >
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Statistic
                  title="总连接数"
                  value={stats?.total_connections ?? 0}
                  loading={loading}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="活动连接数"
                  value={stats?.active_connections ?? 0}
                  loading={loading}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="空闲连接数"
                  value={stats?.idle_connections ?? 0}
                  loading={loading}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="等待连接数"
                  value={stats?.waiting_connections ?? 0}
                  loading={loading}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={24}>
          <Card title="连接统计">
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Statistic
                  title="总连接数"
                  value={stats?.total_connections}
                  loading={loading}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="活动连接数"
                  value={stats?.active_connections}
                  loading={loading}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="空闲连接数"
                  value={stats?.idle_connections}
                  loading={loading}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="等待连接数"
                  value={stats?.waiting_connections}
                  loading={loading}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="最大等待时间(ms)"
                  value={stats?.max_wait_time}
                  loading={loading}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="平均等待时间(ms)"
                  value={stats?.avg_wait_time}
                  loading={loading}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={24}>
          <Card title="连接趋势">
            {(metrics?.connection_history?.length ?? 0) > 0 ? (
              <Line {...config} />
            ) : (
              <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>暂无趋势数据</div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PoolMonitor; 