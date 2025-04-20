import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Button, Select, message, Radio } from 'antd';
import { Line } from '@ant-design/charts';
import { getPoolStats, getPoolMetrics, cleanupConnections } from '../../../../services/poolConfig';
import type { PoolStats } from '../../../../services/poolConfig';

const { Option } = Select;

const PoolMonitor: React.FC = () => {
  const [stats, setStats] = useState<PoolStats | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [timeRange, setTimeRange] = useState('1h');
  const [loading, setLoading] = useState(false);
  const [poolType, setPoolType] = useState('redis');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsData, metricsData] = await Promise.all([
        getPoolStats(),
        getPoolMetrics(timeRange)
      ]);
      setStats(statsData);
      setMetrics(metricsData);
    } catch (error) {
      message.error('获取监控数据失败');
      console.error('获取监控数据失败:', error);
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
      await cleanupConnections();
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
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span>连接池状态</span>
                <Radio.Group 
                  value={poolType} 
                  onChange={(e) => setPoolType(e.target.value)}
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
                  value={stats?.total_connections}
                  loading={loading}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="活动连接数"
                  value={stats?.active_connections}
                  loading={loading}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="空闲连接数"
                  value={stats?.idle_connections}
                  loading={loading}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="等待连接数"
                  value={stats?.waiting_connections}
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
            <Line {...config} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PoolMonitor; 