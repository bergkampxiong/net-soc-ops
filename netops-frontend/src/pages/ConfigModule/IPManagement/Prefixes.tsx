/**
 * IP 管理 - 网段（Prefixes）列表与增删改（PRD-IP管理功能）
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Input, Modal, Form, Select, Checkbox, message, Popconfirm, Card } from 'antd';
import type { TableRowSelection } from 'antd/es/table/interface';
import { PlusOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import request from '../../../utils/request';

interface PrefixRow {
  id: number;
  prefix: string;
  status: string;
  description?: string;
  is_pool?: boolean;
  mark_utilized?: boolean;
  vlan_id?: number;
  location?: string;
  aggregate_id?: number;
  created_at?: string;
  updated_at?: string;
}

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'reserved', label: 'Reserved' },
  { value: 'deprecated', label: 'Deprecated' },
  { value: 'container', label: 'Container' },
];

const IPManagementPrefixes: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<PrefixRow[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(20);
  const [filterPrefix, setFilterPrefix] = useState('');
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterLocation, setFilterLocation] = useState('');
  const [aggregateOptions, setAggregateOptions] = useState<{ value: number; label: string }[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);

  const loadAggregates = useCallback(async () => {
    try {
      const res = await request.get('/config-module/ipam/aggregates?limit=100');
      const data = res.data?.data ?? res.data;
      const items = Array.isArray(data?.items) ? data.items : [];
      setAggregateOptions(items.map((a: { id: number; prefix: string }) => ({ value: a.id, label: a.prefix })));
    } catch {
      setAggregateOptions([]);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { skip, limit };
      if (filterPrefix) params.prefix = filterPrefix;
      if (filterStatus) params.status = filterStatus;
      if (filterLocation) params.location = filterLocation;
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      const res = await request.get(`/config-module/ipam/prefixes?${qs}`);
      const data = res.data?.data ?? res.data;
      setList(Array.isArray(data?.items) ? data.items : []);
      setTotal(typeof data?.total === 'number' ? data.total : 0);
    } catch (e) {
      message.error('加载列表失败');
      setList([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [skip, limit, filterPrefix, filterStatus, filterLocation]);

  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    loadAggregates();
  }, [loadAggregates]);

  const openAdd = () => {
    setEditingId(null);
    form.setFieldsValue({
      prefix: '',
      status: 'active',
      description: '',
      is_pool: false,
      mark_utilized: false,
      vlan_id: undefined,
      location: '',
      aggregate_id: undefined,
    });
    setModalVisible(true);
  };

  const openEdit = (row: PrefixRow) => {
    setEditingId(row.id);
    form.setFieldsValue({
      prefix: row.prefix,
      status: row.status,
      description: row.description ?? '',
      is_pool: row.is_pool ?? false,
      mark_utilized: row.mark_utilized ?? false,
      vlan_id: row.vlan_id,
      location: row.location ?? '',
      aggregate_id: row.aggregate_id,
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const payload = {
      prefix: values.prefix?.trim(),
      status: values.status,
      description: values.description?.trim() || undefined,
      is_pool: values.is_pool,
      mark_utilized: values.mark_utilized,
      vlan_id: values.vlan_id,
      location: values.location?.trim() || undefined,
      aggregate_id: values.aggregate_id,
    };
    try {
      if (editingId != null) {
        await request.put(`/config-module/ipam/prefixes/${editingId}`, payload);
        message.success('更新成功');
      } else {
        await request.post('/config-module/ipam/prefixes', payload);
        message.success('新增成功');
      }
      setModalVisible(false);
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/config-module/ipam/prefixes/${id}`);
      message.success('已删除');
      load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败');
    }
  };

  const handleBatchDelete = async () => {
    const ids = selectedRowKeys.map(Number).filter((id) => Number.isInteger(id) && id > 0);
    if (ids.length === 0) return;
    setBatchDeleting(true);
    let successCount = 0;
    for (const id of ids) {
      try {
        await request.delete(`/config-module/ipam/prefixes/${id}`);
        successCount += 1;
      } catch (e: any) {
        const failMsg = e?.response?.data?.detail || '删除失败';
        message.error(`删除 ID ${id} 失败：${failMsg}`);
      }
    }
    setBatchDeleting(false);
    setSelectedRowKeys([]);
    if (successCount > 0) {
      message.success(`已删除 ${successCount} 条`);
      load();
    }
  };

  const rowSelection: TableRowSelection<PrefixRow> = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    {
      title: 'Prefix',
      dataIndex: 'prefix',
      ellipsis: true,
      render: (text: string, row: PrefixRow) => (
        <Link to={`/config-module/ip-management/prefixes/${row.id}`}>{text || '-'}</Link>
      ),
    },
    { title: 'Status', dataIndex: 'status', width: 100 },
    { title: 'VLAN ID', dataIndex: 'vlan_id', width: 90 },
    { title: 'Location', dataIndex: 'location', ellipsis: true },
    {
      title: '所属 Aggregate',
      dataIndex: 'aggregate_id',
      width: 140,
      render: (aggId: number | undefined) =>
        aggId != null ? (
          <Link to={`/config-module/ip-management/aggregates/${aggId}`}>
            {aggregateOptions.find((o) => o.value === aggId)?.label ?? `#${aggId}`}
          </Link>
        ) : '—',
    },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: unknown, row: PrefixRow) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEdit(row)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(row.id)}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card title="网段（Prefixes）">
      <Space style={{ marginBottom: 16 }} wrap>
        <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增</Button>
        <Popconfirm
          title={`确定删除选中的 ${selectedRowKeys.length} 条？`}
          onConfirm={handleBatchDelete}
          disabled={selectedRowKeys.length === 0}
        >
          <Button
            danger
            icon={<DeleteOutlined />}
            loading={batchDeleting}
            disabled={selectedRowKeys.length === 0}
          >
            批量删除{selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length})` : ''}
          </Button>
        </Popconfirm>
        <Button icon={<ReloadOutlined />} onClick={() => load()}>刷新</Button>
        <Input.Search placeholder="Prefix 筛选" allowClear style={{ width: 200 }} onSearch={(v) => { setFilterPrefix(v); setSkip(0); }} />
        <Select
          placeholder="Status"
          allowClear
          style={{ width: 120 }}
          onChange={(v) => { setFilterStatus(v); setSkip(0); }}
          options={STATUS_OPTIONS}
        />
        <Input.Search placeholder="Location 筛选" allowClear style={{ width: 160 }} onSearch={(v) => { setFilterLocation(v); setSkip(0); }} />
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        rowSelection={rowSelection}
        columns={columns}
        dataSource={list}
        pagination={{
          current: Math.floor(skip / limit) + 1,
          pageSize: limit,
          total,
          showSizeChanger: false,
          onChange: (page) => setSkip((page - 1) * limit),
        }}
        size="small"
      />
      <Modal
        title={editingId != null ? '编辑网段' : '新增网段'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="prefix" label="Prefix (CIDR)" rules={[{ required: true }]}>
            <Input placeholder="如 192.168.1.0/24" />
          </Form.Item>
          <Form.Item name="status" label="Status" rules={[{ required: true }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="aggregate_id" label="所属 Aggregate">
            <Select allowClear placeholder="可选" options={aggregateOptions} />
          </Form.Item>
          <Form.Item name="vlan_id" label="VLAN ID">
            <Input type="number" placeholder="可选" />
          </Form.Item>
          <Form.Item name="location" label="Location">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="is_pool" valuePropName="checked">
            <Checkbox>Is Pool</Checkbox>
          </Form.Item>
          <Form.Item name="mark_utilized" valuePropName="checked">
            <Checkbox>Mark Utilized</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default IPManagementPrefixes;
