import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Form,
  Input,
  Button,
  Space,
  Modal,
  Select,
  Spin,
  message,
  Popconfirm,
} from 'antd';
import request from '../../utils/request';

interface EosItem {
  id: number;
  device_or_model: string;
  eos_date?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

const ConfigModuleEos: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<EosItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const loadList = async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
      };
      if (statusFilter) params.status = statusFilter;
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      const res = await request.get(`/config-module/eos?${qs}`);
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      const tot = data?.total ?? (Array.isArray(items) ? items.length : 0);
      setList(Array.isArray(items) ? items : []);
      setTotal(typeof tot === 'number' ? tot : 0);
    } catch (e) {
      message.error('加载服务终止列表失败');
      setList([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList();
  }, [page, pageSize, statusFilter]);

  const openAdd = () => {
    setEditingId(null);
    form.resetFields();
    setModalVisible(true);
  };

  const openEdit = (record: EosItem) => {
    setEditingId(record.id);
    form.setFieldsValue({
      device_or_model: record.device_or_model,
      eos_date: record.eos_date,
      description: record.description,
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const v = await form.validateFields();
      if (editingId != null) {
        await request.put(`/config-module/eos/${editingId}`, v);
        message.success('更新成功');
      } else {
        await request.post('/config-module/eos', v);
        message.success('新增成功');
      }
      setModalVisible(false);
      loadList();
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error(editingId != null ? '更新失败' : '新增失败');
    }
  };

  const onDelete = async (id: number) => {
    try {
      await request.delete(`/config-module/eos/${id}`);
      message.success('已删除');
      loadList();
    } catch (e) {
      message.error('删除失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>服务终止</h2>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="筛选状态"
            style={{ width: 140 }}
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'upcoming', label: '即将 EOS' },
              { value: 'passed', label: '已 EOS' },
            ]}
          />
          <Button type="primary" onClick={openAdd}>新增 EOS 信息</Button>
        </Space>
        <Table
          loading={loading}
          dataSource={list}
          rowKey="id"
          size="small"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); if (typeof ps === 'number') setPageSize(ps); },
          }}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 70 },
            { title: '设备/型号', dataIndex: 'device_or_model', width: 160 },
            { title: 'EOS 日期', dataIndex: 'eos_date', width: 120 },
            { title: '说明', dataIndex: 'description', ellipsis: true },
            { title: '更新时间', dataIndex: 'updated_at', width: 180 },
            {
              title: '操作',
              key: 'action',
              width: 160,
              render: (_, record) => (
                <Space>
                  <a onClick={() => openEdit(record)}>编辑</a>
                  <Popconfirm title="确定删除？" onConfirm={() => onDelete(record.id)}>
                    <a style={{ color: '#ff4d4f' }}>删除</a>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editingId != null ? '编辑 EOS 信息' : '新增 EOS 信息'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={520}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="device_or_model" label="设备/型号" rules={[{ required: true }]}>
            <Input placeholder="设备标识或型号" />
          </Form.Item>
          <Form.Item name="eos_date" label="EOS 日期 (YYYY-MM-DD)">
            <Input placeholder="如 2026-12-31" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={3} placeholder="可选说明" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigModuleEos;
