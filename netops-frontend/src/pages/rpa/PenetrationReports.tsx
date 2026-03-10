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
  Popconfirm,
  Row,
  Col,
  Statistic,
} from 'antd';
import { ReloadOutlined, FileTextOutlined, ArrowLeftOutlined, PlusOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import request, { LONG_REQUEST_TIMEOUT } from '@/utils/request';
import { formatBeijingToSecond } from '@/utils/formatTime';

const STRIX_BASE = '/config-module/strix';

interface ProgressData {
  model: string | null;
  vulnerabilities: number | null;
  agents: number | null;
  tools: number | null;
}

interface ScanItem {
  id: number;
  target_type: string;
  target_value: string;
  instruction: string | null;
  scan_mode: string;
  status: string;
  run_name: string | null;
  job_execution_id: number | null;
  created_by?: string | null;
  created_at: string;
  finished_at: string | null;
  /** 列表/详情接口按 PRD 不返回原文，均为 null；仅用 strix_stats 展示 4 项 */
  summary: { stdout?: string; stderr?: string; high?: number; medium?: number; low?: number } | null;
  report_path: string | null;
  unified_report_path?: string | null;
  unified_report_generated_at?: string | null;
  strix_stats?: { model?: string; vulnerabilities?: number; agents?: number; tools?: number };
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
  const [filters, setFilters] = useState<{ job_execution_id?: string; status?: string; created_by?: string }>(() =>
    jobExecutionIdFromUrl ? { job_execution_id: jobExecutionIdFromUrl } : {}
  );
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [progressLoading, setProgressLoading] = useState(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

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
      if (filters.created_by?.trim()) params.created_by = filters.created_by.trim();
      const res = await request.get<{ items: ScanItem[]; total: number }>(`${STRIX_BASE}/scans`, { params });
      const data = res.data ?? res;
      setList(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {
      message.error('获取列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, filters.job_execution_id, filters.status, filters.created_by]);

  useEffect(() => {
    if (id) {
      setDetailLoading(true);
      setProgress(null);
      request
        .get<ScanItem>(`${STRIX_BASE}/scans/${id}`)
        .then((res) => {
          setDetail(res.data ?? res);
        })
        .catch(() => message.error('获取详情失败'))
        .finally(() => setDetailLoading(false));
    } else {
      setDetail(null);
      setProgress(null);
      fetchList();
    }
  }, [id, fetchList]);

  // 进入详情且任务运行中时拉取一次进度（不轮询，减少资源占用）
  const fetchProgress = useCallback(async () => {
    if (!id) return;
    setProgressLoading(true);
    try {
      const res = await request.get<ProgressData>(`${STRIX_BASE}/scans/${id}/progress`);
      const data = res.data ?? res;
      setProgress({
        model: data.model ?? null,
        vulnerabilities: data.vulnerabilities ?? null,
        agents: data.agents ?? null,
        tools: data.tools ?? null,
      });
    } catch {
      setProgress(null);
    } finally {
      setProgressLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id && detail && (detail.status === 'running' || detail.status === 'pending')) {
      fetchProgress();
    }
  }, [id, detail?.id, detail?.status, fetchProgress]);

  // 用带认证的 request 拉取报告后以 blob 打开/下载，避免 window.open 无 token 被重定向到登录页
  const openReportInNewTab = async (url: string, taskId: number, label: string) => {
    try {
      const res = await request.get(url, { responseType: 'blob' });
      const blob = res.data instanceof Blob ? res.data : new Blob([res.data]);
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
    } catch {
      message.error(`${label}打开失败`);
    }
  };

  const downloadReportAsFile = async (url: string, filename: string, label: string) => {
    try {
      const res = await request.get(url, { responseType: 'blob' });
      const blob = res.data instanceof Blob ? res.data : new Blob([res.data]);
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(blobUrl);
    } catch {
      message.error(`${label}下载失败`);
    }
  };

  /** 下载 Strix 报告目录打包的 zip */
  const downloadReport = (taskId: number) => {
    downloadReportAsFile(
      `${STRIX_BASE}/scans/${taskId}/report`,
      `strix_report_${taskId}.zip`,
      '报告'
    );
  };

  const generateUnifiedReport = async (taskId: number) => {
    setGeneratingId(taskId);
    try {
      await request.post(`${STRIX_BASE}/scans/${taskId}/unified-report`, {}, { timeout: LONG_REQUEST_TIMEOUT });
      message.success('统一报告已生成');
      if (id && Number(id) === taskId) {
        request.get<ScanItem>(`${STRIX_BASE}/scans/${taskId}`).then((res) => setDetail(res.data ?? res));
      } else {
        fetchList();
      }
    } catch (e: unknown) {
      const err = e && typeof e === 'object' && 'response' in e ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail : null;
      const msg = typeof err === 'string' ? err : '生成失败';
      if (msg.includes('not ready') || msg.includes('missing')) {
        message.warning('报告目录未就绪，请等待扫描完成后再生成统一报告');
      } else {
        message.error(msg || '生成统一报告失败');
      }
    } finally {
      setGeneratingId(null);
    }
  };

  const downloadUnifiedReport = (taskId: number) => {
    downloadReportAsFile(
      `${STRIX_BASE}/scans/${taskId}/unified-report`,
      `unified-report-${taskId}.md`,
      '统一报告'
    );
  };

  const previewUnifiedReport = (taskId: number) => {
    openReportInNewTab(
      `${STRIX_BASE}/scans/${taskId}/unified-report?format=html`,
      taskId,
      '预览统一报告'
    );
  };

  const handleCancelScan = async (taskId: number) => {
    setCancellingId(taskId);
    try {
      await request.post(`${STRIX_BASE}/scans/${taskId}/cancel`);
      message.success('已取消任务');
      const res = await request.get<ScanItem>(`${STRIX_BASE}/scans/${taskId}`);
      setDetail(res.data ?? res);
    } catch {
      message.error('取消失败');
    } finally {
      setCancellingId(null);
    }
  };

  const handleDelete = async (taskId: number) => {
    setDeletingId(taskId);
    try {
      await request.delete(`${STRIX_BASE}/scans/${taskId}`);
      message.success('已删除');
      if (id && Number(id) === taskId) {
        navigate('/rpa/task-job-management/penetration-reports');
      }
      fetchList();
    } catch {
      message.error('删除失败');
    } finally {
      setDeletingId(null);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先勾选要删除的报告');
      return;
    }
    setBatchDeleting(true);
    try {
      const ids = selectedRowKeys as number[];
      for (const taskId of ids) {
        await request.delete(`${STRIX_BASE}/scans/${taskId}`);
      }
      message.success(`已删除 ${ids.length} 条报告`);
      setSelectedRowKeys([]);
      if (id && ids.includes(Number(id))) {
        navigate('/rpa/task-job-management/penetration-reports');
      }
      fetchList();
    } catch {
      message.error('批量删除失败');
    } finally {
      setBatchDeleting(false);
    }
  };

  if (id) {
    const refreshDetail = async () => {
      if (!id) return;
      setDetailLoading(true);
      try {
        const res = await request.get<ScanItem>(`${STRIX_BASE}/scans/${id}`);
        const data = res.data ?? res;
        setDetail(data);
        if (data.status === 'running' || data.status === 'pending') {
          await fetchProgress();
        }
      } catch {
        message.error('获取详情失败');
      } finally {
        setDetailLoading(false);
      }
    };

    return (
      <div style={{ padding: 24 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/rpa/task-job-management/penetration-reports')}>
            返回列表
          </Button>
          <Button icon={<ReloadOutlined />} onClick={refreshDetail} loading={detailLoading}>
            刷新
          </Button>
        </Space>
        <Card title="扫描报告详情" loading={detailLoading}>
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
                <Descriptions.Item label="来源">{detail.created_by === 'job' ? '作业执行' : detail.created_by ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="作业执行 ID">{detail.job_execution_id ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="创建时间">{formatBeijingToSecond(detail.created_at)}</Descriptions.Item>
                <Descriptions.Item label="结束时间">{formatBeijingToSecond(detail.finished_at)}</Descriptions.Item>
              </Descriptions>
              {(detail.status === 'running' || detail.status === 'pending') && (
                <Card size="small" title="运行状态" style={{ marginTop: 16 }} extra={
                  <Space>
                    <Button size="small" icon={<ReloadOutlined />} loading={progressLoading} onClick={fetchProgress}>刷新</Button>
                    <Popconfirm title="确定取消该扫描任务？" onConfirm={() => handleCancelScan(detail.id)} okText="确定" cancelText="取消">
                      <Button size="small" danger loading={cancellingId === detail.id}>取消任务</Button>
                    </Popconfirm>
                  </Space>
                }>
                  <Row gutter={24}>
                    <Col span={8}><Statistic title="模型" value={(progress?.model ?? detail.strix_stats?.model) || '-'} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={8}><Statistic title="Agents" value={(progress?.agents ?? detail.strix_stats?.agents) ?? 0} /></Col>
                    <Col span={8}><Statistic title="Tools" value={(progress?.tools ?? detail.strix_stats?.tools) ?? 0} /></Col>
                  </Row>
                </Card>
              )}
              {(detail.status === 'success' || detail.status === 'failed') && detail.strix_stats && (
                <Card size="small" title="运行状态" style={{ marginTop: 16 }}>
                  <Row gutter={24}>
                    <Col span={8}><Statistic title="模型" value={detail.strix_stats.model || '-'} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={8}><Statistic title="Agents" value={detail.strix_stats.agents ?? 0} /></Col>
                    <Col span={8}><Statistic title="Tools" value={detail.strix_stats.tools ?? 0} /></Col>
                  </Row>
                </Card>
              )}
              <div style={{ marginTop: 16 }}>
                <Space wrap>
                  <Button type="primary" icon={<FileTextOutlined />} onClick={() => downloadReport(detail.id)}>下载报告</Button>
                  {detail.unified_report_path ? (
                    <>
                      <Button icon={<FileTextOutlined />} onClick={() => downloadUnifiedReport(detail.id)}>下载统一报告</Button>
                      <Button icon={<EyeOutlined />} onClick={() => previewUnifiedReport(detail.id)}>预览统一报告</Button>
                      <Button icon={<ReloadOutlined />} loading={generatingId === detail.id} onClick={() => generateUnifiedReport(detail.id)}>重新生成统一报告</Button>
                    </>
                  ) : (
                    <Button icon={<PlusOutlined />} loading={generatingId === detail.id} onClick={() => generateUnifiedReport(detail.id)}>生成统一报告</Button>
                  )}
                  <Popconfirm title="确定删除该渗透测试报告记录？" onConfirm={() => handleDelete(detail.id)} okText="确定" cancelText="取消">
                    <Button danger icon={<DeleteOutlined />} loading={deletingId === detail.id}>删除</Button>
                  </Popconfirm>
                </Space>
                {!detail.unified_report_path && (
                  <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                    生成后可下载/预览合并中文化的单一报告。若需中文化请先在系统管理中配置 OpenAI API Key。
                  </Typography.Text>
                )}
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
    {
      title: '来源',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 90,
      render: (v: string | null | undefined) => (v === 'job' ? '作业执行' : v ?? '-'),
    },
    { title: '作业执行 ID', dataIndex: 'job_execution_id', key: 'job_execution_id', width: 110 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170, render: (v: string) => formatBeijingToSecond(v) },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_: unknown, record: ScanItem) => (
        <Space wrap size="small">
          <Button type="link" size="small" onClick={() => navigate(`/rpa/task-job-management/penetration-reports/${record.id}`)}>
            详情
          </Button>
          <Button type="link" size="small" onClick={() => downloadReport(record.id)}>
            下载报告
          </Button>
          {record.unified_report_path ? (
            <>
              <Button type="link" size="small" onClick={() => downloadUnifiedReport(record.id)}>
                统一报告
              </Button>
              <Button type="link" size="small" onClick={() => previewUnifiedReport(record.id)}>
                预览
              </Button>
            </>
          ) : (
            <Button
              type="link"
              size="small"
              loading={generatingId === record.id}
              onClick={() => generateUnifiedReport(record.id)}
            >
              生成统一报告
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <Form layout="inline" onValuesChange={(_, v) => setFilters(v)} style={{ marginBottom: 16 }}>
        <Form.Item name="job_execution_id" label="作业执行 ID">
          <Input type="number" placeholder="筛选" style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 100 }} options={Object.entries(statusMap).map(([k, v]) => ({ value: k, label: v.text }))} />
        </Form.Item>
        <Form.Item name="created_by" label="来源">
          <Select placeholder="全部" allowClear style={{ width: 110 }} options={[{ value: 'job', label: '作业执行' }]} />
        </Form.Item>
      </Form>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchList}>刷新</Button>
          <Popconfirm title={`确定删除已勾选的 ${selectedRowKeys.length} 条报告？`} onConfirm={handleBatchDelete} okText="确定" cancelText="取消" disabled={selectedRowKeys.length === 0}>
            <Button danger icon={<DeleteOutlined />} loading={batchDeleting} disabled={selectedRowKeys.length === 0}>批量删除</Button>
          </Popconfirm>
        </Space>
      </div>
      <Table
        rowKey="id"
        loading={loading}
        rowSelection={{ selectedRowKeys, onChange: (keys) => setSelectedRowKeys(keys) }}
        columns={columns}
        dataSource={list}
        pagination={{ total, current: page, pageSize, showSizeChanger: false, onChange: setPage }}
        size="small"
      />
    </Card>
  );
};

export default PenetrationReports;
