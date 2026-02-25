import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Form,
  Input,
  Button,
  Space,
  Modal,
  Spin,
  message,
  Popconfirm,
} from 'antd';
import request from '../../utils/request';

interface TemplateItem {
  id: number;
  name: string;
  device_type?: string;
  content: string;
  tags?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

const ConfigModuleChangeTemplates: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<TemplateItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [filters, setFilters] = useState<Record<string, string>>({});

  const loadList = async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
        ...filters,
      };
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      const res = await request.get(`/config-module/change-templates?${qs}`);
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      const tot = data?.total ?? (Array.isArray(items) ? items.length : 0);
      setList(Array.isArray(items) ? items : []);
      setTotal(typeof tot === 'number' ? tot : 0);
    } catch (e) {
      message.error('加载变更模板列表失败');
      setList([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList();
  }, [page, pageSize, JSON.stringify(filters)]);

  const onFinish = (v: Record<string, string>) => {
    setFilters(v);
    setPage(1);
  };

  const openAdd = () => {
    setEditingId(null);
    form.resetFields();
    setModalVisible(true);
  };

  const openEdit = (record: TemplateItem) => {
    setEditingId(record.id);
    form.setFieldsValue({
      name: record.name,
      device_type: record.device_type,
      content: record.content,
      tags: record.tags,
      description: record.description,
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const v = await form.validateFields();
      if (editingId != null) {
        await request.put(`/config-module/change-templates/${editingId}`, v);
        message.success('更新成功');
      } else {
        await request.post('/config-module/change-templates', v);
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
      await request.delete(`/config-module/change-templates/${id}`);
      message.success('已删除');
      loadList();
    } catch (e) {
      message.error('删除失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>配置变更模板</h2>
      <Card>
        <Form form={form} layout="inline" onFinish={onFinish} style={{ marginBottom: 16 }}>
          <Form.Item name="device_type" label="设备类型">
            <Input placeholder="设备类型" allowClear style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="tag" label="标签">
            <Input placeholder="用途标签" allowClear style={{ width: 140 }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">查询</Button>
              <Button onClick={() => { form.resetFields(); setFilters({}); setPage(1); }}>重置</Button>
              <Button type="primary" onClick={openAdd}>新增模板</Button>
            </Space>
          </Form.Item>
        </Form>
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
            { title: '名称', dataIndex: 'name', ellipsis: true, width: 140 },
            { title: '设备类型', dataIndex: 'device_type', width: 120 },
            { title: '标签', dataIndex: 'tags', ellipsis: true, width: 120 },
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
        title={editingId != null ? '编辑变更模板' : '新增变更模板'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="名称" />
          </Form.Item>
          <Form.Item name="device_type" label="设备类型">
            <Input placeholder="如 cisco_ios" />
          </Form.Item>
          <Form.Item name="content" label="模板内容" rules={[{ required: true }]}>
            <Input.TextArea rows={8} placeholder="配置片段内容" />
          </Form.Item>
          <Form.Item name="tags" label="用途标签（逗号分隔）">
            <Input placeholder="如 ACL, NTP, SNMP" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={2} placeholder="可选说明" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigModuleChangeTemplates;
