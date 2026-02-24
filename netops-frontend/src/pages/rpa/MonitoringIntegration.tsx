import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Table,
  Space,
  message,
  Typography,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Tag,
  Drawer,
  Collapse,
  Select,
  Popconfirm,
  Tabs,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  CopyOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ApiOutlined,
  BellOutlined,
  InboxOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import request from '../../utils/request';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('Asia/Shanghai');

const { Title, Paragraph, Text } = Typography;

/** 将 ISO 时间格式化为北京时间 24 小时制，精确到秒 */
function formatAlertTime(iso: string | undefined): string {
  if (!iso) return '-';
  const d = dayjs(iso).tz('Asia/Shanghai');
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : '-';
}

/** 列表展示用：精简告警标题（去首尾星号、末尾括号及内容），兼容老数据 */
function displayAlertTitle(title: string | undefined): string {
  if (!title) return '-';
  let s = title.replace(/^\s*\*+\s*|\s*\*+\s*$/g, '').trim();
  s = s.replace(/\s*\([^)]*\)\s*$/g, '').trim();
  return s || '-';
}

/** 将原始 Body 转为可读文字：JSON 则格式化展示，否则原样 */
function rawPayloadToReadable(raw: string | undefined): string {
  if (!raw) return '';
  try {
    const o = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return JSON.stringify(o, null, 2);
  } catch {
    return raw;
  }
}

interface WebhookItem {
  id: number;
  name: string;
  path_slug: string;
  enabled: boolean;
  remark?: string;
  created_at: string;
  webhook_url: string;
}

interface AlertItem {
  id: number;
  webhook_id: string;
  source: string;
  alert_title?: string;
  message?: string;
  color?: string;
  entity_interface?: string;
  node_ip?: string;
  interface_name?: string;
  severity: string;
  status: string;
  alert_time?: string;
  triggered_at?: string;
  created_at?: string;
}

interface AlertDetail extends AlertItem {
  raw_payload?: string;
  metadata?: string;
}

const severityColors: Record<string, string> = {
  critical: 'red',
  warning: 'orange',
  info: 'blue',
};

const MonitoringIntegration: React.FC = () => {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [webhookLoading, setWebhookLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<WebhookItem | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertsTotal, setAlertsTotal] = useState(0);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertPage, setAlertPage] = useState(1);
  const [alertPageSize, setAlertPageSize] = useState(20);
  const [alertFilters, setAlertFilters] = useState<{
    source?: string;
    severity?: string;
    keyword?: string;
  }>({});
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [detailAlert, setDetailAlert] = useState<AlertDetail | null>(null);

  const [archiveDays, setArchiveDays] = useState(90);
  const [archiveCount, setArchiveCount] = useState<number | null>(null);
  const [archiveCountLoading, setArchiveCountLoading] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [clearAlertsLoading, setClearAlertsLoading] = useState(false);

  const fetchWebhooks = async () => {
    setWebhookLoading(true);
    try {
      const res = await request.get('monitoring-integration/webhooks');
      setWebhooks(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      message.error('获取 Webhook 列表失败');
    } finally {
      setWebhookLoading(false);
    }
  };

  const fetchAlerts = async () => {
    setAlertsLoading(true);
    try {
      const params: Record<string, string | number> = {
        skip: (alertPage - 1) * alertPageSize,
        limit: alertPageSize,
      };
      if (alertFilters.source) params.source = alertFilters.source;
      if (alertFilters.severity) params.severity = alertFilters.severity;
      if (alertFilters.keyword) params.keyword = alertFilters.keyword;
      const res = await request.get('monitoring-integration/alerts', { params });
      setAlerts(res.data?.items ?? []);
      setAlertsTotal(res.data?.total ?? 0);
    } catch (e) {
      message.error('获取告警列表失败');
    } finally {
      setAlertsLoading(false);
    }
  };

  useEffect(() => {
    fetchWebhooks();
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [alertPage, alertPageSize, alertFilters]);

  const fetchArchiveCount = async () => {
    setArchiveCountLoading(true);
    try {
      const res = await request.get('monitoring-integration/alerts/archive/count', { params: { days: archiveDays } });
      setArchiveCount(res.data?.count ?? 0);
    } catch {
      setArchiveCount(null);
    } finally {
      setArchiveCountLoading(false);
    }
  };

  useEffect(() => {
    fetchArchiveCount();
  }, [archiveDays]);

  const handleArchiveDownloadThenDelete = async () => {
    setArchiveLoading(true);
    try {
      const res = await request.get('monitoring-integration/alerts/archive/export', {
        params: { days: archiveDays },
        responseType: 'blob',
      }) as { data: Blob; headers?: Record<string, string> };
      const blob = res.data;
      const disposition = res.headers?.['content-disposition'];
      let filename = `alerts_archive_${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')}.json`;
      if (disposition) {
        const m = disposition.match(/filename="?([^";]+)"?/);
        if (m) filename = m[1].trim();
      }
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
      await request.post(`monitoring-integration/alerts/archive/delete-by-days?days=${archiveDays}`);
      message.success('归档完成：已下载并删除对应记录');
      setArchiveCount(null);
      fetchArchiveCount();
      fetchAlerts();
    } catch (e) {
      message.error('归档失败');
    } finally {
      setArchiveLoading(false);
    }
  };

  const handleArchiveDeleteOnly = async () => {
    setArchiveLoading(true);
    try {
      const res = await request.post(`monitoring-integration/alerts/archive/delete-by-days?days=${archiveDays}`);
      const deleted = res.data?.deleted ?? 0;
      message.success(`已删除 ${deleted} 条记录`);
      setArchiveCount(null);
      fetchArchiveCount();
      fetchAlerts();
    } catch {
      message.error('删除失败');
    } finally {
      setArchiveLoading(false);
    }
  };

  const handleClearAlerts = async () => {
    setClearAlertsLoading(true);
    try {
      const res = await request.post('monitoring-integration/alerts/clear');
      const deleted = res.data?.deleted ?? 0;
      message.success(`已清空告警，共删除 ${deleted} 条`);
      setArchiveCount(null);
      fetchArchiveCount();
      fetchAlerts();
    } catch {
      message.error('清空失败');
    } finally {
      setClearAlertsLoading(false);
    }
  };

  const copyUrl = (url: string) => {
    const text = typeof url === 'string' ? url : '';
    if (!text) {
      message.warning('无内容可复制');
      return;
    }
    if (typeof navigator !== 'undefined' && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      navigator.clipboard.writeText(text).then(() => message.success('已复制到剪贴板')).catch(() => copyUrlFallback(text));
    } else {
      copyUrlFallback(text);
    }
  };

  const copyUrlFallback = (text: string) => {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      message.success('已复制到剪贴板');
    } catch (e) {
      message.warning('复制失败，请手动复制');
    }
  };

  const handleCreateWebhook = async (values: { name: string; remark?: string }) => {
    try {
      const res = await request.post('monitoring-integration/webhooks', values);
      message.success('创建成功');
      setCreateModalVisible(false);
      createForm.resetFields();
      fetchWebhooks();
      if (res.data?.webhook_url) {
        copyUrl(res.data.webhook_url);
        message.info('Webhook URL 已复制到剪贴板，请到 SolarWinds 中配置');
      }
    } catch (e) {
      message.error('创建失败');
    }
  };

  const handleUpdateWebhook = async (values: { name?: string; remark?: string; enabled?: boolean }) => {
    if (!editingWebhook) return;
    try {
      await request.patch(`monitoring-integration/webhooks/${editingWebhook.id}`, values);
      message.success('更新成功');
      setEditModalVisible(false);
      setEditingWebhook(null);
      editForm.resetFields();
      fetchWebhooks();
    } catch (e) {
      message.error('更新失败');
    }
  };

  const handleDeleteWebhook = async (id: number) => {
    try {
      await request.delete(`monitoring-integration/webhooks/${id}`);
      message.success('已删除');
      fetchWebhooks();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const openEdit = (record: WebhookItem) => {
    setEditingWebhook(record);
    editForm.setFieldsValue({ name: record.name, remark: record.remark, enabled: record.enabled });
    setEditModalVisible(true);
  };

  const loadAlertDetail = async (id: number) => {
    try {
      const res = await request.get(`monitoring-integration/alerts/${id}`);
      setDetailAlert(res.data);
      setDetailDrawerVisible(true);
    } catch (e) {
      message.error('获取详情失败');
    }
  };

  const tabItems = [
    {
      key: 'webhook',
      label: <span><ApiOutlined />Webhook 管理</span>,
      children: (
        <Card
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
              创建 Webhook
            </Button>
          }
        >
          <Table<WebhookItem>
            loading={webhookLoading}
            rowKey="id"
            dataSource={webhooks}
            columns={[
              { title: '名称', dataIndex: 'name', key: 'name', width: 160 },
              {
                title: 'Webhook URL',
                dataIndex: 'webhook_url',
                key: 'webhook_url',
                ellipsis: true,
                render: (url: string) => (
                  <Space>
                    <Text style={{ maxWidth: 360 }} ellipsis>{url || '-'}</Text>
                    <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => copyUrl(url)}>复制</Button>
                  </Space>
                ),
              },
              {
                title: '状态',
                dataIndex: 'enabled',
                key: 'enabled',
                width: 80,
                render: (v: boolean) => (v ? <Tag color="green">启用</Tag> : <Tag color="default">禁用</Tag>),
              },
              { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
              {
                title: '操作',
                key: 'action',
                width: 200,
                render: (_, record) => (
                  <Space>
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
                    <Popconfirm title="确定删除？该 URL 将不再接收告警。" onConfirm={() => handleDeleteWebhook(record.id)}>
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: 'alerts',
      label: <span><BellOutlined />告警事件</span>,
      children: (
        <Card>
          <Space style={{ marginBottom: 16 }} wrap>
            <Select
              placeholder="来源"
              allowClear
              style={{ width: 120 }}
              value={alertFilters.source}
              onChange={(v) => setAlertFilters((f) => ({ ...f, source: v }))}
            >
              <Select.Option value="solarwinds">solarwinds</Select.Option>
            </Select>
            <Select
              placeholder="严重程度"
              allowClear
              style={{ width: 120 }}
              value={alertFilters.severity}
              onChange={(v) => setAlertFilters((f) => ({ ...f, severity: v }))}
            >
              <Select.Option value="critical">critical</Select.Option>
              <Select.Option value="warning">warning</Select.Option>
              <Select.Option value="info">info</Select.Option>
            </Select>
            <Input.Search
              placeholder="关键词（标题/摘要/节点）"
              allowClear
              style={{ width: 200 }}
              onSearch={(v) => setAlertFilters((f) => ({ ...f, keyword: v || undefined }))}
            />
          </Space>
          <Table<AlertItem>
            loading={alertsLoading}
            rowKey="id"
            dataSource={alerts}
            columns={[
              {
                title: '告警标题',
                dataIndex: 'alert_title',
                key: 'alert_title',
                width: 200,
                ellipsis: true,
                render: (v: string) => displayAlertTitle(v),
              },
              {
                title: '级别',
                dataIndex: 'severity',
                key: 'severity',
                width: 80,
                render: (s: string) => <Tag color={severityColors[s] || 'default'}>{s}</Tag>,
              },
              {
                title: '节点/实体',
                key: 'node_ip',
                width: 140,
                ellipsis: true,
                render: (_: unknown, record: AlertItem) => record.node_ip || record.entity_interface || '-',
              },
              {
                title: '接口',
                dataIndex: 'interface_name',
                key: 'interface_name',
                width: 140,
                ellipsis: true,
                render: (v: string) => v || '-',
              },
              {
                title: '告警时间',
                dataIndex: 'alert_time',
                key: 'alert_time',
                width: 180,
                render: (v: string) => formatAlertTime(v),
              },
              {
                title: '操作',
                key: 'action',
                width: 80,
                render: (_, record) => (
                  <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => loadAlertDetail(record.id)}>
                    详情
                  </Button>
                ),
              },
            ]}
            pagination={{
              current: alertPage,
              pageSize: alertPageSize,
              total: alertsTotal,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 条`,
              onChange: (p, ps) => {
                setAlertPage(p);
                if (ps) setAlertPageSize(ps);
              },
            }}
          />
        </Card>
      ),
    },
    {
      key: 'archive',
      label: <span><InboxOutlined />事件归档</span>,
      children: (
        <Card title="按告警时间归档">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Space wrap align="center">
              <Typography.Text>归档早于</Typography.Text>
              <InputNumber
                min={1}
                max={365}
                value={archiveDays}
                onChange={(v) => setArchiveDays(v ?? 90)}
                addonAfter="天"
              />
              <Typography.Text type="secondary">的告警事件</Typography.Text>
            </Space>
            {archiveCountLoading ? (
              <Spin size="small" />
            ) : archiveCount !== null ? (
              <Typography.Text>当前符合条件的记录：<strong>{archiveCount}</strong> 条</Typography.Text>
            ) : null}
            <Space wrap>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={archiveLoading}
                onClick={handleArchiveDownloadThenDelete}
              >
                归档（下载后删除）
              </Button>
              <Button
                danger
                loading={archiveLoading}
                onClick={handleArchiveDeleteOnly}
              >
                仅删除
              </Button>
              <Button onClick={fetchArchiveCount} loading={archiveCountLoading}>刷新数量</Button>
              <Popconfirm
                title="确定清空全部告警？此操作不可恢复。"
                onConfirm={handleClearAlerts}
                okText="确定清空"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger loading={clearAlertsLoading}>清空告警</Button>
              </Popconfirm>
            </Space>
            <Typography.Text type="secondary">
              归档：先下载 JSON 到本地，再删除库中对应记录。仅删除：直接删除，不下载。清空告警：删除全部告警事件（不可恢复）。按告警时间（触发时间或创建时间）早于 N 天前的记录。
            </Typography.Text>
          </Space>
        </Card>
      ),
    },
  ];

  return (
    <div className="monitoring-integration">
      <div className="page-header">
        <h2>监控系统集成</h2>
      </div>
      <Tabs
        defaultActiveKey="webhook"
        tabPosition="left"
        style={{ minHeight: 'calc(100vh - 200px)' }}
        items={tabItems}
      />

      {/* 创建 Webhook 弹窗 */}
      <Modal
        title="创建 Webhook"
        open={createModalVisible}
        onCancel={() => { setCreateModalVisible(false); createForm.resetFields(); }}
        footer={null}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreateWebhook}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：SolarWinds NTA 流量告警" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">创建并复制 URL</Button>
              <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑 Webhook 弹窗 */}
      <Modal
        title="编辑 Webhook"
        open={editModalVisible}
        onCancel={() => { setEditModalVisible(false); setEditingWebhook(null); }}
        footer={null}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdateWebhook}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">保存</Button>
              <Button onClick={() => setEditModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 告警详情抽屉 */}
      <Drawer
        title="告警详情"
        width={560}
        open={detailDrawerVisible}
        onClose={() => { setDetailDrawerVisible(false); setDetailAlert(null); }}
      >
        {detailAlert && (
          <>
            <Paragraph><Text strong>告警标题：</Text>{displayAlertTitle(detailAlert.alert_title)}</Paragraph>
            <Paragraph>
              <Text strong>级别：</Text>
              <Tag color={severityColors[detailAlert.severity] || 'default'}>{detailAlert.severity}</Tag>
              {detailAlert.color && <Text type="secondary"> ({detailAlert.color})</Text>}
            </Paragraph>
            <Paragraph><Text strong>节点/实体：</Text>{detailAlert.node_ip ?? detailAlert.entity_interface ?? '-'}</Paragraph>
            <Paragraph><Text strong>接口：</Text>{detailAlert.interface_name ?? '-'}</Paragraph>
            <Paragraph><Text strong>告警时间：</Text>{formatAlertTime(detailAlert.alert_time)}</Paragraph>
            <Paragraph><Text strong>告警摘要：</Text>{detailAlert.message ?? '-'}</Paragraph>
            {detailAlert.raw_payload && (
              <Collapse defaultActiveKey={['raw']}>
                <Collapse.Panel header="原始 Body" key="raw">
                  <pre style={{
                    fontSize: 12,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    marginBottom: 0,
                    overflow: 'visible',
                    maxHeight: 'none',
                  }}>
                    {rawPayloadToReadable(detailAlert.raw_payload)}
                  </pre>
                </Collapse.Panel>
              </Collapse>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default MonitoringIntegration;
