import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Form,
  Input,
  Select,
  message,
  Descriptions,
} from 'antd';
import { ReloadOutlined, FileTextOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import request from '@/utils/request';

const STRIX_BASE = '/config-module/strix';

interface ScanItem {
  id: number;
  target_type: string;
  target_value: string;
  instruction: string | null;
  scan_mode: string;
  status: string;
  run_name: string | null;
  job_execution_id: number | null;
  created_at: string;
  finished_at: string | null;
  summary: { high?: number; medium?: number; low?: number } | null;
  report_path: string | null;
}

const statusMap: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待中' },
  running: { color: 'processing', text: '运行中' },
  success: { color: 'success', text: '成功' },
  failed: { color: 'error', text: '失败' },
  cancelled: { color: 'warning', text: '已取消' },
};

const PenetrationReports: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const jobExecutionIdFromUrl = searchParams.get('job_execution_id') ?? undefined;
  const [list, setList] = useState<ScanItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<ScanItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filters, setFilters] = useState<{ job_execution_id?: string; status?: string }>(() =>
    jobExecutionIdFromUrl ? { job_execution_id: jobExecutionIdFromUrl } : {}
  );
  const [page, setPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    if (jobExecutionIdFromUrl) {
      setFilters((f) => ({ ...f, job_execution_id: jobExecutionIdFromUrl }));
    }
  }, [jobExecutionIdFromUrl]);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { skip: (page - 1) * pageSize, limit: pageSize };
      if (filters.job_execution_id) params.job_execution_id = Number(filters.job_execution_id);
      if (filters.status) params.status = filters.status;
      const res = await request.get<{ items: ScanItem[]; total: number }>(`${STRIX_BASE}/scans`, { params });
      const data = res.data ?? res;
      setList(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {
      message.error('获取列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, filters.job_execution_id, filters.status]);

  useEffect(() => {
    if (id) {
      setDetailLoading(true);
      request
        .get<ScanItem>(`${STRIX_BASE}/scans/${id}`)
        .then((res) => {
          setDetail(res.data ?? res);
        })
        .catch(() => message.error('获取详情失败'))
        .finally(() => setDetailLoading(false));
    } else {
      setDetail(null);
      fetchList();
    }
  }, [id, fetchList]);

  const downloadReport = (taskId: number) => {
    const base = (request.defaults.baseURL as string) || '/api';
    window.open(`${base}${STRIX_BASE}/scans/${taskId}/report`, '_blank');
  };

  if (id) {
    return (
      <div style={{ padding: 24 }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/rpa/task-job-management/penetration-reports')}>
          返回列表
        </Button>
        <Card title="扫描报告详情" loading={detailLoading} style={{ marginTop: 16 }}>
          {detail && (
            <>
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="扫描 ID">{detail.id}</Descriptions.Item>
                <Descriptions.Item label="目标类型">{detail.target_type}</Descriptions.Item>
                <Descriptions.Item label="目标值">{detail.target_value}</Descriptions.Item>
                <Descriptions.Item label="扫描模式">{detail.scan_mode}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={statusMap[detail.status]?.color}>{statusMap[detail.status]?.text ?? detail.status}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="作业执行 ID">{detail.job_execution_id ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="创建时间">{detail.created_at ? new Date(detail.created_at).toLocaleString() : '-'}</Descriptions.Item>
                <Descriptions.Item label="结束时间">{detail.finished_at ? new Date(detail.finished_at).toLocaleString() : '-'}</Descriptions.Item>
              </Descriptions>
              <div style={{ marginTop: 16 }}>
                <Button type="primary" icon={<FileTextOutlined />} onClick={() => downloadReport(detail.id)}>
                  下载报告
                </Button>
              </div>
            </>
          )}
        </Card>
      </div>
    );
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    { title: '目标', dataIndex: 'target_value', key: 'target_value', ellipsis: true },
    { title: '模式', dataIndex: 'scan_mode', key: 'scan_mode', width: 90 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => {
        const t = statusMap[s] || { color: 'default', text: s };
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    { title: '作业执行 ID', dataIndex: 'job_execution_id', key: 'job_execution_id', width: 110 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170, render: (v: string) => (v ? new Date(v).toLocaleString() : '-') },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_: unknown, record: ScanItem) => (
        <Space>
          <Button type="link" size="small" onClick={() => navigate(`/rpa/task-job-management/penetration-reports/${record.id}`)}>
            详情
          </Button>
          <Button type="link" size="small" onClick={() => downloadReport(record.id)}>
            下载报告
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4}>渗透测试报告</Typography.Title>
      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <Form layout="inline" onValuesChange={(_, v) => setFilters(v)}>
            <Form.Item name="job_execution_id" label="作业执行 ID">
              <Input type="number" placeholder="筛选" style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="status" label="状态">
              <Select placeholder="全部" allowClear style={{ width: 100 }} options={Object.entries(statusMap).map(([k, v]) => ({ value: k, label: v.text }))} />
            </Form.Item>
          </Form>
          <Button icon={<ReloadOutlined />} onClick={fetchList}>刷新</Button>
        </Space>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={list}
          pagination={{
            total,
            current: page,
            pageSize,
            showSizeChanger: false,
            onChange: setPage,
          }}
          size="small"
        />
      </Card>
    </div>
  );
};

export default PenetrationReports;
