/**
 * IP 管理 - 聚合（Aggregates）列表与增删改（PRD-IP管理功能）
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Input, Modal, Form, message, Popconfirm, Card, Progress } from 'antd';
import type { TableRowSelection } from 'antd/es/table/interface';
import { PlusOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import request from '../../../utils/request';
import IpamCsvImportControls from './IpamCsvImportControls';
import { IPAM_AGGREGATE_CSV_HEADERS } from './ipamImportTemplates';

interface AggregateRow {
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

const IPManagementAggregates: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<AggregateRow[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(20);
  const [filterPrefix, setFilterPrefix] = useState('');
  const [filterRir, setFilterRir] = useState('');
  const [filterDescription, setFilterDescription] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchDeleting, setBatchDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { skip, limit };
      if (filterPrefix) params.prefix = filterPrefix;
      if (filterRir) params.rir = filterRir;
      if (filterDescription) params.description = filterDescription;
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      const res = await request.get(`/config-module/ipam/aggregates?${qs}`);
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
  }, [skip, limit, filterPrefix, filterRir, filterDescription]);

  useEffect(() => {
    load();
  }, [load]);

  const openAdd = () => {
    setEditingId(null);
    form.setFieldsValue({ prefix: '', rir: '', date_added: '', description: '' });
    setModalVisible(true);
  };

  const openEdit = (row: AggregateRow) => {
    setEditingId(row.id);
    form.setFieldsValue({
      prefix: row.prefix,
      rir: row.rir ?? '',
      date_added: row.date_added ?? '',
      description: row.description ?? '',
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editingId != null) {
        await request.put(`/config-module/ipam/aggregates/${editingId}`, {
          prefix: values.prefix?.trim(),
          rir: values.rir?.trim() || undefined,
          date_added: values.date_added || undefined,
          description: values.description?.trim() || undefined,
        });
        message.success('更新成功');
      } else {
        await request.post('/config-module/ipam/aggregates', {
          prefix: values.prefix?.trim(),
          rir: values.rir?.trim() || undefined,
          date_added: values.date_added || undefined,
          description: values.description?.trim() || undefined,
        });
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
      await request.delete(`/config-module/ipam/aggregates/${id}`);
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
    let failMsg = '';
    for (const id of ids) {
      try {
        await request.delete(`/config-module/ipam/aggregates/${id}`);
        successCount += 1;
      } catch (e: any) {
        failMsg = e?.response?.data?.detail || '删除失败';
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

  const rowSelection: TableRowSelection<AggregateRow> = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    {
      title: 'Prefix (CIDR)',
      dataIndex: 'prefix',
      ellipsis: true,
      render: (text: string, row: AggregateRow) => (
        <Link to={`/config-module/ip-management/aggregates/${row.id}`}>{text || '-'}</Link>
      ),
    },
    { title: 'RIR', dataIndex: 'rir', ellipsis: true },
    {
      title: 'Prefixes',
      dataIndex: 'prefix_count',
      width: 100,
      render: (count: number, row: AggregateRow) => (
        <Link to={`/config-module/ip-management/aggregates/${row.id}?tab=prefixes`}>{count ?? 0}</Link>
      ),
    },
    {
      title: 'Utilization',
      key: 'utilization',
      width: 160,
      render: (_: unknown, row: AggregateRow) => {
        const pct = row.utilization_pct ?? 0;
        return (
          <Space size="small">
            <Progress percent={pct} size="small" showInfo={false} style={{ marginBottom: 0, width: 60 }} />
            <span>{pct}%</span>
          </Space>
        );
      },
    },
    { title: '分配日期', dataIndex: 'date_added', width: 120 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '创建时间', dataIndex: 'created_at', width: 180 },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: unknown, row: AggregateRow) => (
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
    <Card title="聚合（Aggregates）">
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
        <IpamCsvImportControls
          importEndpoint="/config-module/ipam/aggregates/import"
          templateFileName="ipam_aggregates_import_template.csv"
          headers={IPAM_AGGREGATE_CSV_HEADERS}
          onImported={() => load()}
        />
        <Button icon={<ReloadOutlined />} onClick={() => load()}>刷新</Button>
        <Input.Search
          placeholder="Prefix 筛选"
          allowClear
          style={{ width: 200 }}
          onSearch={(v) => { setFilterPrefix(v); setSkip(0); }}
        />
        <Input.Search
          placeholder="RIR 筛选"
          allowClear
          style={{ width: 160 }}
          onSearch={(v) => { setFilterRir(v); setSkip(0); }}
        />
        <Input.Search
          placeholder="描述筛选"
          allowClear
          style={{ width: 160 }}
          onSearch={(v) => { setFilterDescription(v); setSkip(0); }}
        />
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
        title={editingId != null ? '编辑聚合' : '新增聚合'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="prefix" label="Prefix (CIDR)" rules={[{ required: true, message: '必填' }]}>
            <Input placeholder="如 10.0.0.0/8" />
          </Form.Item>
          <Form.Item name="rir" label="RIR">
            <Input placeholder="如 RFC 1918、APNIC" />
          </Form.Item>
          <Form.Item name="date_added" label="分配日期">
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default IPManagementAggregates;
