import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Form,
  Select,
  DatePicker,
  Modal,
  message,
  Typography,
} from 'antd';
import {
  ReloadOutlined,
  FileTextOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import request from '@/utils/request';
import type {
  JobExecutionListItem,
  JobExecutionListResponse,
  JobExecutionStatsResponse,
} from './job-execution/types';

const { RangePicker } = DatePicker;
const { Title } = Typography;

const statusMap: Record<string, { color: string; text: string }> = {
  running: { color: 'processing', text: '执行中' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
};

function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const JobMonitoring: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<JobExecutionStatsResponse | null>(null);
  const [listData, setListData] = useState<JobExecutionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [statsLoading, setStatsLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [logModalOpen, setLogModalOpen] = useState(false);
  const [logContent, setLogContent] = useState('');
  const [logTitle, setLogTitle] = useState('执行日志');

  const [statsRange, setStatsRange] = useState<'today' | '7d' | '30d'>('today');
  const [listFilters, setListFilters] = useState<{
    start_time_from?: string;
    start_time_to?: string;
  }>({});
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });
  const [searchForm] = Form.useForm();

  const getStatsDates = useCallback((): { date_from: string; date_to: string } => {
    const now = new Date();
    const today = formatDate(now);
    if (statsRange === 'today') {
      return { date_from: today, date_to: today };
    }
    if (statsRange === '7d') {
      const from = new Date(now);
      from.setDate(from.getDate() - 6);
      return { date_from: formatDate(from), date_to: today };
    }
    const from = new Date(now);
    from.setDate(from.getDate() - 29);
    return { date_from: formatDate(from), date_to: today };
  }, [statsRange]);

  const fetchStats = useCallback(async () => {
    const { date_from, date_to } = getStatsDates();
    setStatsLoading(true);
    try {
      const res = await request.get<JobExecutionStatsResponse>('/job-executions/stats', {
        params: { date_from, date_to },
      });
      const data = res.data ?? res;
      setStats(data);
    } catch {
      message.error('获取统计失败');
      setStats(null);
    } finally {
      setStatsLoading(false);
    }
  }, [getStatsDates]);

  const fetchList = useCallback(async () => {
    setListLoading(true);
    const { current, pageSize } = pagination;
    const skip = (current - 1) * pageSize;
    const params: Record<string, any> = { skip, limit: pageSize };
    if (listFilters.start_time_from) params.start_time_from = listFilters.start_time_from;
    if (listFilters.start_time_to) params.start_time_to = listFilters.start_time_to;
    try {
      const res = await request.get<JobExecutionListResponse>('/job-executions', {
        params,
      });
      const data = res.data ?? res;
      setListData(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {
      message.error('获取执行列表失败');
      setListData([]);
      setTotal(0);
    } finally {
      setListLoading(false);
    }
  }, [pagination, listFilters]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const onSearch = (values: any) => {
    const filters: typeof listFilters = {};
    if (values.timeRange?.length === 2) {
      const from = values.timeRange[0];
      const to = values.timeRange[1];
      filters.start_time_from = typeof from?.toISOString === 'function' ? from.toISOString() : from?.format?.('YYYY-MM-DDTHH:mm:ss') ?? String(from);
      filters.start_time_to = typeof to?.toISOString === 'function' ? to.toISOString() : to?.format?.('YYYY-MM-DDTHH:mm:ss') ?? String(to);
    }
    setListFilters(filters);
    setPagination((p) => ({ ...p, current: 1 }));
  };

  const onTableChange = (p: any) => {
    setPagination({
      current: p.current ?? 1,
      pageSize: p.pageSize ?? 20,
    });
  };

  const handleViewLogs = (record: JobExecutionListItem) => {
    setLogTitle(`执行日志 #${record.id} ${record.job_name ?? ''}`);
    setLogContent(record.logs ?? '（无日志）');
    setLogModalOpen(true);
  };

  const handleGoDetail = (record: JobExecutionListItem) => {
    navigate(`/rpa/job-execution/jobs/${record.job_id}?tab=executions`);
  };

  const columns = [
    {
      title: '执行ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '作业名称',
      dataIndex: 'job_name',
      key: 'job_name',
      width: 120,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const { color, text } = statusMap[status] ?? { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 170,
      render: (t: string) => (t ? new Date(t).toLocaleString() : '-'),
    },
    {
      title: '结束时间',
      dataIndex: 'end_time',
      key: 'end_time',
      width: 170,
      render: (t: string) => (t ? new Date(t).toLocaleString() : '-'),
    },
    {
      title: '执行结果',
      dataIndex: 'result',
      key: 'result',
      width: 120,
      ellipsis: true,
      render: (r: any) => (r ? JSON.stringify(r) : '-'),
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      width: 120,
      ellipsis: true,
      render: (e: string) => e || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: JobExecutionListItem) => (
        <Space size="small" wrap style={{ marginRight: 0 }}>
          <Button
            type="link"
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => handleViewLogs(record)}
            disabled={!record.logs}
            style={{ padding: '0 4px' }}
          >
            查看日志
          </Button>
          <Button
            type="link"
            size="small"
            icon={<LinkOutlined />}
            onClick={() => handleGoDetail(record)}
            style={{ padding: '0 4px' }}
          >
            作业详情
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="job-monitoring">
      <Card>
        <Title level={4}>作业监控与报告</Title>

        {/* 统计卡片 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space style={{ marginBottom: 12 }}>
            <span>统计范围：</span>
            <Select
              value={statsRange}
              onChange={setStatsRange}
              style={{ width: 120 }}
              options={[
                { label: '今日', value: 'today' },
                { label: '近7日', value: '7d' },
                { label: '近30日', value: '30d' },
              ]}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchStats} loading={statsLoading}>
              刷新统计
            </Button>
          </Space>
          <Row gutter={24}>
            <Col span={4}>
              <Statistic title="执行总数" value={stats?.total ?? 0} loading={statsLoading} />
            </Col>
            <Col span={4}>
              <Statistic title="成功" value={stats?.success ?? 0} loading={statsLoading} />
            </Col>
            <Col span={4}>
              <Statistic title="失败" value={stats?.failed ?? 0} loading={statsLoading} />
            </Col>
            <Col span={4}>
              <Statistic title="执行中" value={stats?.running ?? 0} loading={statsLoading} />
            </Col>
            <Col span={4}>
              <Statistic
                title="成功率(%)"
                value={stats?.success_rate ?? 0}
                loading={statsLoading}
              />
            </Col>
          </Row>
        </Card>

        {/* 筛选与列表 */}
        <Form
          form={searchForm}
          layout="inline"
          onFinish={onSearch}
          style={{ marginBottom: 16 }}
        >
          <Form.Item name="timeRange" label="开始时间">
            <RangePicker showTime />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                查询
              </Button>
              <Button onClick={() => { searchForm.resetFields(); onSearch({}); }}>
                重置
              </Button>
              <Button icon={<ReloadOutlined />} onClick={fetchList} loading={listLoading}>
                刷新列表
              </Button>
            </Space>
          </Form.Item>
        </Form>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={listData}
          loading={listLoading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
          onChange={onTableChange}
          scroll={{ x: 1000 }}
          tableLayout="fixed"
        />
      </Card>

      <Modal
        title={logTitle}
        open={logModalOpen}
        onCancel={() => setLogModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setLogModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        <pre style={{ maxHeight: 500, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
          {logContent}
        </pre>
      </Modal>
    </div>
  );
};

export default JobMonitoring;
