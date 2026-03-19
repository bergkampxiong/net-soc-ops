/**
 * IP 管理 - Aggregate 详情（图1）：信息 Tab、Prefixes Tab、Journal/Change Log 占位
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Card, Descriptions, Tabs, Button, Space, Progress, message, Popconfirm, Modal, Form, Input, Select, Table, Checkbox, Tag } from 'antd';
import { CopyOutlined, EditOutlined, DeleteOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import request from '../../../utils/request';

interface AggregateDetailData {
  id: number;
  prefix: string;
  rir?: string;
  date_added?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  prefix_count?: number;
  utilization_pct?: number;
}

interface PrefixRow {
  id?: number;
  prefix: string;
  status: string;
  description?: string;
  aggregate_id?: number;
  /** 是否为可用网段虚拟行（无 id） */
  isAvailable?: boolean;
  /** 关联 DHCP Scope 汇总的使用率（有 IP 数据时由后端返回） */
  utilization_used?: number;
  utilization_total?: number;
  utilization_pct?: number;
}

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'reserved', label: 'Reserved' },
  { value: 'deprecated', label: 'Deprecated' },
  { value: 'container', label: 'Container' },
];

const IPManagementAggregateDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tabFromUrl = searchParams.get('tab') || 'aggregate';
  const [activeTab, setActiveTab] = useState(tabFromUrl);
  const [detail, setDetail] = useState<AggregateDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editForm] = Form.useForm();
  const [prefixList, setPrefixList] = useState<PrefixRow[]>([]);
  const [prefixTotal, setPrefixTotal] = useState(0);
  const [prefixSkip, setPrefixSkip] = useState(0);
  const [prefixLoading, setPrefixLoading] = useState(false);
  const [prefixFilterStatus, setPrefixFilterStatus] = useState<string | undefined>();
  const [addPrefixModalVisible, setAddPrefixModalVisible] = useState(false);
  const [addPrefixForm] = Form.useForm();
  const [addPrefixLoading, setAddPrefixLoading] = useState(false);
  const [editIsClone, setEditIsClone] = useState(false);
  const [availableRanges, setAvailableRanges] = useState<string[]>([]);
  const [availableRangesLoading, setAvailableRangesLoading] = useState(false);
  const prefixLimit = 20;

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await request.get(`/config-module/ipam/aggregates/${id}`);
      const data = res.data?.data ?? res.data;
      setDetail(data);
    } catch {
      message.error('加载失败');
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    setActiveTab(tabFromUrl === 'prefixes' ? 'prefixes' : tabFromUrl === 'journal' ? 'journal' : tabFromUrl === 'changelog' ? 'changelog' : 'aggregate');
  }, [tabFromUrl]);

  const loadPrefixes = useCallback(async () => {
    if (!id) return;
    setPrefixLoading(true);
    try {
      const params: Record<string, string | number> = { aggregate_id: id, skip: prefixSkip, limit: prefixLimit };
      if (prefixFilterStatus) params.status = prefixFilterStatus;
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      const res = await request.get(`/config-module/ipam/prefixes?${qs}`);
      const data = res.data?.data ?? res.data;
      setPrefixList(Array.isArray(data?.items) ? data.items : []);
      setPrefixTotal(typeof data?.total === 'number' ? data.total : 0);
    } catch {
      setPrefixList([]);
      setPrefixTotal(0);
    } finally {
      setPrefixLoading(false);
    }
  }, [id, prefixSkip, prefixFilterStatus]);

  const loadAvailableRanges = useCallback(async () => {
    if (!id) return;
    setAvailableRangesLoading(true);
    try {
      const res = await request.get(`/config-module/ipam/aggregates/${id}/available-ranges`);
      const data = res.data?.data ?? res.data;
      setAvailableRanges(Array.isArray(data?.items) ? data.items : []);
    } catch {
      setAvailableRanges([]);
    } finally {
      setAvailableRangesLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (activeTab === 'prefixes') {
      loadPrefixes();
      loadAvailableRanges();
    }
  }, [activeTab, loadPrefixes, loadAvailableRanges]);

  const handleClone = () => {
    if (!detail) return;
    setEditIsClone(true);
    editForm.setFieldsValue({
      prefix: '',
      rir: detail.rir ?? '',
      date_added: detail.date_added ?? '',
      description: detail.description ?? '',
    });
    setEditModalVisible(true);
  };

  const handleEdit = () => {
    if (!detail) return;
    setEditIsClone(false);
    editForm.setFieldsValue({
      prefix: detail.prefix,
      rir: detail.rir ?? '',
      date_added: detail.date_added ?? '',
      description: detail.description ?? '',
    });
    setEditModalVisible(true);
  };

  const handleEditSubmit = async (isClone: boolean) => {
    const values = await editForm.validateFields();
    try {
      if (isClone) {
        await request.post('/config-module/ipam/aggregates', {
          prefix: values.prefix?.trim(),
          rir: values.rir?.trim() || undefined,
          date_added: values.date_added || undefined,
          description: values.description?.trim() || undefined,
        });
        message.success('已复制为新聚合');
        setEditModalVisible(false);
        navigate('/config-module/ip-management/aggregates');
      } else {
        await request.put(`/config-module/ipam/aggregates/${id}`, {
          prefix: values.prefix?.trim(),
          rir: values.rir?.trim() || undefined,
          date_added: values.date_added || undefined,
          description: values.description?.trim() || undefined,
        });
        message.success('更新成功');
        setEditModalVisible(false);
        loadDetail();
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    }
  };

  const handleDelete = async () => {
    try {
      await request.delete(`/config-module/ipam/aggregates/${id}`);
      message.success('已删除');
      navigate('/config-module/ip-management/aggregates');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败');
    }
  };

  const handleAddPrefix = (initialPrefix?: string) => {
    addPrefixForm.setFieldsValue({
      prefix: initialPrefix ?? '',
      status: 'active',
      description: '',
      is_pool: false,
      mark_utilized: false,
      aggregate_id: id ? Number(id) : undefined,
    });
    setAddPrefixModalVisible(true);
  };

  const handleAddPrefixSubmit = async () => {
    const values = await addPrefixForm.validateFields();
    setAddPrefixLoading(true);
    try {
      await request.post('/config-module/ipam/prefixes', {
        prefix: values.prefix?.trim(),
        status: values.status,
        description: values.description?.trim() || undefined,
        is_pool: values.is_pool,
        mark_utilized: values.mark_utilized,
        aggregate_id: id ? Number(id) : undefined,
      });
      message.success('新增成功');
      setAddPrefixModalVisible(false);
      loadPrefixes();
      loadDetail();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    } finally {
      setAddPrefixLoading(false);
    }
  };

  const prefixTableDataSource: PrefixRow[] = [
    ...prefixList,
    ...availableRanges.map((prefix) => ({
      prefix,
      status: 'Available',
      description: '—',
      isAvailable: true as const,
    })),
  ];

  const prefixColumns = [
    {
      title: 'Prefix',
      dataIndex: 'prefix',
      render: (text: string, row: PrefixRow) =>
        row.isAvailable ? (
          <a onClick={() => handleAddPrefix(row.prefix)}>{text || '-'}</a>
        ) : (
          <Link to={`/config-module/ip-management/prefixes/${row.id}`}>{text || '-'}</Link>
        ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 100,
      render: (status: string) =>
        status === 'Available' ? <Tag color="green">Available</Tag> : status,
    },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    {
      title: '使用率',
      key: 'utilization',
      width: 140,
      render: (_: unknown, row: PrefixRow) => {
        if (row.isAvailable || row.utilization_total == null || row.utilization_total <= 0) {
          return '—';
        }
        const pct = row.utilization_pct ?? 0;
        return (
          <Space size="small">
            <Progress percent={pct} size="small" showInfo={false} style={{ width: 80 }} />
            <span>{pct}%</span>
          </Space>
        );
      },
    },
  ];

  if (loading || !detail) {
    return <Card loading={loading}>加载中…</Card>;
  }

  const family = detail.prefix && (detail.prefix.includes(':') ? 'IPv6' : 'IPv4');

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ marginBottom: 4 }}>{detail.prefix}</h2>
            <div style={{ color: '#666', fontSize: 12 }}>
              Created {detail.created_at ?? '-'} · Updated {detail.updated_at ?? '-'}
            </div>
          </div>
          <Space>
            <Button icon={<CopyOutlined />} onClick={handleClone}>Clone</Button>
            <Button icon={<EditOutlined />} onClick={handleEdit}>Edit</Button>
            <Popconfirm title="确定删除此聚合？" onConfirm={handleDelete}>
              <Button danger icon={<DeleteOutlined />}>Delete</Button>
            </Popconfirm>
          </Space>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k)}
          style={{ marginTop: 16 }}
          items={[
            {
              key: 'aggregate',
              label: 'Aggregate',
              children: (
                <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                  <div style={{ flex: '1 1 400px' }}>
                    <Descriptions bordered column={1} size="small">
                      <Descriptions.Item label="Family">{family}</Descriptions.Item>
                      <Descriptions.Item label="RIR">
                        {detail.rir ? <Link to="#">{detail.rir}</Link> : '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Utilization">
                        <Space>
                          <Progress percent={detail.utilization_pct ?? 0} size="small" showInfo={false} style={{ width: 100 }} />
                          <span>{detail.utilization_pct ?? 0}%</span>
                        </Space>
                      </Descriptions.Item>
                      <Descriptions.Item label="Tenant">—</Descriptions.Item>
                      <Descriptions.Item label="Date Added">{detail.date_added ?? '—'}</Descriptions.Item>
                      <Descriptions.Item label="Description">{detail.description || '—'}</Descriptions.Item>
                    </Descriptions>
                  </div>
                  <div style={{ flex: '0 1 200px' }}>
                    <Card size="small" title="Tags">No tags assigned</Card>
                  </div>
                </div>
              ),
            },
            {
              key: 'prefixes',
              label: `Prefixes ${detail.prefix_count ?? 0}`,
              children: (
                <div>
                  <Space style={{ marginBottom: 16 }} wrap>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAddPrefix()}>+ Add Prefix</Button>
                    <Button icon={<ReloadOutlined />} onClick={loadPrefixes}>刷新</Button>
                    <Select
                      placeholder="Show All"
                      allowClear
                      style={{ width: 140 }}
                      onChange={(v) => { setPrefixFilterStatus(v); setPrefixSkip(0); }}
                      options={[{ value: undefined, label: 'Show All' }, ...STATUS_OPTIONS]}
                    />
                  </Space>
                  <Table
                    rowKey={(row: PrefixRow) => (row.isAvailable ? `available-${row.prefix}` : String(row.id))}
                    loading={prefixLoading || availableRangesLoading}
                    columns={prefixColumns}
                    dataSource={prefixTableDataSource}
                    size="small"
                    pagination={{
                      current: Math.floor(prefixSkip / prefixLimit) + 1,
                      pageSize: prefixLimit,
                      total: prefixTotal,
                      showSizeChanger: false,
                      onChange: (page) => setPrefixSkip((page - 1) * prefixLimit),
                    }}
                  />
                </div>
              ),
            },
            { key: 'journal', label: 'Journal', children: <div style={{ color: '#999' }}>暂无</div> },
            { key: 'changelog', label: 'Change Log', children: <div style={{ color: '#999' }}>暂无</div> },
          ]}
        />
      </Card>

      <Modal
        title={editIsClone ? '复制为新聚合' : '编辑聚合'}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setEditModalVisible(false)}>取消</Button>,
          editIsClone ? (
            <Button key="clone" type="primary" onClick={() => handleEditSubmit(true)}>另存为新聚合</Button>
          ) : (
            <Button key="save" type="primary" onClick={() => handleEditSubmit(false)}>保存</Button>
          ),
        ]}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="prefix" label="Prefix (CIDR)" rules={[{ required: true }]}>
            <Input placeholder="如 10.0.0.0/8" />
          </Form.Item>
          <Form.Item name="rir" label="RIR"><Input /></Form.Item>
          <Form.Item name="date_added" label="Date Added"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title="新增 Prefix"
        open={addPrefixModalVisible}
        onOk={handleAddPrefixSubmit}
        onCancel={() => setAddPrefixModalVisible(false)}
        confirmLoading={addPrefixLoading}
        destroyOnClose
      >
        <Form form={addPrefixForm} layout="vertical">
          <Form.Item name="prefix" label="Prefix (CIDR)" rules={[{ required: true }]}>
            <Input placeholder="需落在当前 Aggregate 范围内" />
          </Form.Item>
          <Form.Item name="status" label="Status" rules={[{ required: true }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="is_pool" valuePropName="checked"><Checkbox>Is Pool</Checkbox></Form.Item>
          <Form.Item name="mark_utilized" valuePropName="checked"><Checkbox>Mark Utilized</Checkbox></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default IPManagementAggregateDetail;
