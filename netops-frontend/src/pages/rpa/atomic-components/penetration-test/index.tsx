import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Table,
  Tag,
  message,
  Space,
  Typography,
  Modal,
  Select,
} from 'antd';
import { ReloadOutlined, PlayCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import request from '@/utils/request';

const { Title } = Typography;
const STRIX_BASE = '/config-module/strix';

// 扫描任务类型
interface ScanTask {
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
  summary: { stdout?: string; stderr?: string; error?: string } | null;
  report_path: string | null;
}

const PenetrationTest: React.FC = () => {
  const [configForm] = Form.useForm();
  const [scanForm] = Form.useForm();
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [scanList, setScanList] = useState<ScanTask[]>([]);
  const [scanTotal, setScanTotal] = useState(0);
  const [scanLoading, setScanLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportContent, setReportContent] = useState('');
  const [reportLoading, setReportLoading] = useState(false);

  const fetchConfig = useCallback(async () => {
    setConfigLoading(true);
    try {
      const res = await request.get<{ config_key: string; config_value: string }[]>(
        `${STRIX_BASE}/config`
      );
      const data = res.data ?? res;
      const initial: Record<string, string> = {};
      (Array.isArray(data) ? data : []).forEach((item: { config_key: string; config_value: string }) => {
        initial[item.config_key] = item.config_value;
      });
      configForm.setFieldsValue(initial);
    } catch {
      message.error('获取配置失败');
    } finally {
      setConfigLoading(false);
    }
  }, [configForm]);

  const saveConfig = async () => {
    try {
      const values = await configForm.validateFields();
      setConfigSaving(true);
      await request.put(`${STRIX_BASE}/config`, values);
      message.success('配置已保存');
      fetchConfig();
    } catch (e) {
      if (e?.errorFields) message.error('请填写必填项');
      else message.error('保存失败');
    } finally {
      setConfigSaving(false);
    }
  };

  const fetchScans = useCallback(async (page = 1, pageSize = 20) => {
    setScanLoading(true);
    try {
      const res = await request.get<{ items: ScanTask[]; total: number }>(`${STRIX_BASE}/scans`, {
        params: { skip: (page - 1) * pageSize, limit: pageSize },
      });
      const data = res.data ?? res;
      setScanList(data.items || []);
      setScanTotal(data.total ?? 0);
    } catch {
      message.error('获取扫描列表失败');
    } finally {
      setScanLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  useEffect(() => {
    fetchScans();
  }, [fetchScans]);

  const createScan = async () => {
    try {
      const values = await scanForm.validateFields();
      setCreateLoading(true);
      await request.post(`${STRIX_BASE}/scans`, {
        target_type: values.target_type || 'web_url',
        target_value: values.target_value?.trim() || undefined,
        targets: values.target_value?.trim() ? values.target_value.trim().split(/\s+/).filter(Boolean) : undefined,
        instruction: values.instruction || undefined,
        scan_mode: values.scan_mode || 'deep',
      });
      message.success('扫描任务已创建');
      scanForm.resetFields();
      fetchScans();
    } catch (e) {
      if (e?.errorFields) message.error('请填写目标');
      else message.error('创建失败');
    } finally {
      setCreateLoading(false);
    }
  };

  const viewReport = async (taskId: number) => {
    setReportModalVisible(true);
    setReportContent('');
    setReportLoading(true);
    try {
      const res = await request.get(`${STRIX_BASE}/scans/${taskId}/report`, {
        responseType: 'text',
      });
      const raw = typeof res.data === 'string' ? res.data : (res.data as any)?.data ?? '';
      setReportContent(raw || '报告暂不可用或任务未完成。');
    } catch {
      setReportContent('报告暂不可用或任务未完成。');
    } finally {
      setReportLoading(false);
    }
  };

  const statusMap: Record<string, { color: string; text: string }> = {
    pending: { color: 'default', text: '等待中' },
    running: { color: 'processing', text: '运行中' },
    success: { color: 'success', text: '成功' },
    failed: { color: 'error', text: '失败' },
    cancelled: { color: 'warning', text: '已取消' },
  };

  const scanColumns = [
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
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180, render: (v: string) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: ScanTask) => (
        <Button type="link" size="small" icon={<FileTextOutlined />} onClick={() => viewReport(record.id)}>
          查看报告
        </Button>
      ),
    },
  ];

  return (
    <div className="penetration-test-page" style={{ padding: 24 }}>
      <Title level={4}>渗透测试（Strix）</Title>
      <Tabs
        items={[
          {
            key: 'config',
            label: 'OpenAPI 配置',
            children: (
              <Card loading={configLoading}>
                <Form form={configForm} layout="vertical" style={{ maxWidth: 560 }}>
                  <Form.Item name="STRIX_LLM" label="STRIX_LLM" rules={[{ required: true }]}>
                    <Input placeholder="如 openai/gpt-4 或 strix/gpt-5" />
                  </Form.Item>
                  <Form.Item name="LLM_API_KEY" label="LLM_API_KEY" rules={[{ required: true }]}>
                    <Input.Password placeholder="API Key（保存后脱敏展示）" />
                  </Form.Item>
                  <Form.Item name="LLM_API_BASE" label="LLM_API_BASE">
                    <Input placeholder="可选，自建/本地模型 base URL" />
                  </Form.Item>
                  <Form.Item name="STRIX_REASONING_EFFORT" label="STRIX_REASONING_EFFORT">
                    <Input placeholder="可选，如 high / medium" />
                  </Form.Item>
                  <Space>
                    <Button type="primary" loading={configSaving} onClick={saveConfig}>
                      保存配置
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={fetchConfig}>
                      刷新
                    </Button>
                  </Space>
                </Form>
              </Card>
            ),
          },
          {
            key: 'scans',
            label: '扫描任务',
            children: (
              <>
                <Card title="创建扫描" style={{ marginBottom: 16 }}>
                  <Form form={scanForm} layout="inline" onFinish={createScan}>
                    <Form.Item name="target_value" rules={[{ required: true, message: '请输入目标 URL 或路径' }]} style={{ minWidth: 280 }}>
                      <Input placeholder="目标 URL 或路径，多个用空格分隔" />
                    </Form.Item>
                    <Form.Item name="scan_mode" initialValue="deep">
                      <Select style={{ width: 120 }} options={[
                        { value: 'quick', label: 'quick' },
                        { value: 'standard', label: 'standard' },
                        { value: 'deep', label: 'deep' },
                      ]} />
                    </Form.Item>
                    <Form.Item name="instruction">
                      <Input placeholder="可选指令" style={{ width: 200 }} />
                    </Form.Item>
                    <Form.Item>
                      <Button type="primary" htmlType="submit" loading={createLoading} icon={<PlayCircleOutlined />}>
                        创建并执行
                      </Button>
                    </Form.Item>
                  </Form>
                </Card>
                <Card
                  title="任务列表"
                  extra={
                    <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchScans()}>
                      刷新
                    </Button>
                  }
                >
                  <Table
                    rowKey="id"
                    loading={scanLoading}
                    columns={scanColumns}
                    dataSource={scanList}
                    pagination={{
                      total: scanTotal,
                      pageSize: 20,
                      showSizeChanger: false,
                      onChange: (p) => fetchScans(p, 20),
                    }}
                    size="small"
                  />
                </Card>
              </>
            ),
          },
        ]}
      />
      <Modal
        title="扫描报告"
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        footer={null}
        width={800}
        destroyOnClose
      >
        {reportLoading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>加载中...</div>
        ) : reportContent.trimStart().startsWith('<') ? (
          <div
            style={{ maxHeight: 480, overflow: 'auto' }}
            dangerouslySetInnerHTML={{ __html: reportContent }}
          />
        ) : (
          <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 480, overflow: 'auto' }}>{reportContent}</pre>
        )}
      </Modal>
    </div>
  );
};

export default PenetrationTest;
