import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Space,
  message,
  Popconfirm,
  Select,
  Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import request from '../../utils/request';

const { Title } = Typography;

/** 清单项：设备或服务 */
interface ChecklistItemRow {
  item_type: 'device' | 'service';
  name: string;
  target: string;
}

/** 清单列表项 */
interface ChecklistRecord {
  id: number;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
  item_count: number;
}

/** CMDB 设备（供选择） */
interface CmdbDevice {
  id: number;
  name?: string;
  ip_address?: string;
}

const DataCollection: React.FC = () => {
  const [list, setList] = useState<ChecklistRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [items, setItems] = useState<ChecklistItemRow[]>([]);
  const [cmdbDevices, setCmdbDevices] = useState<CmdbDevice[]>([]);
  const [cmdbLoading, setCmdbLoading] = useState(false);
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<number[]>([]);

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await request.get<{ data?: ChecklistRecord[] }>('inspection/checklists', {
        params: { skip: 0, limit: 500 },
      });
      const data = res?.data ?? res;
      setList(Array.isArray(data) ? data : []);
    } catch (e) {
      message.error('加载巡检清单失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
  }, []);

  const loadCmdbDevices = async () => {
    setCmdbLoading(true);
    try {
      const res = await request.get<CmdbDevice[]>('device/category/cmdb-devices');
      const data = res?.data ?? res;
      setCmdbDevices(Array.isArray(data) ? data : []);
    } catch (e) {
      message.error('加载 CMDB 设备失败');
    } finally {
      setCmdbLoading(false);
    }
  };

  const openCreate = () => {
    setEditingId(null);
    form.setFieldsValue({ name: '', description: '' });
    setItems([]);
    setModalOpen(true);
  };

  const openEdit = async (id: number) => {
    setEditingId(id);
    try {
      const res = await request.get<ChecklistRecord & { items?: ChecklistItemRow[] }>(`inspection/checklists/${id}`);
      const data = res?.data ?? res;
      form.setFieldsValue({ name: data.name, description: data.description ?? '' });
      setItems((data as any).items ?? []);
      setModalOpen(true);
    } catch (e) {
      message.error('加载清单详情失败');
    }
  };

  const addDevicesFromCmdb = () => {
    const toAdd = cmdbDevices
      .filter((d) => selectedDeviceIds.includes(d.id) && d.ip_address)
      .map((d) => ({ item_type: 'device' as const, name: d.name || d.ip_address || '', target: d.ip_address || '' }));
    const existingTargets = new Set(items.map((i) => i.target));
    const newOnes = toAdd.filter((t) => !existingTargets.has(t.target));
    setItems((prev) => [...prev, ...newOnes]);
    setSelectedDeviceIds([]);
  };

  const addService = (name: string, url: string) => {
    if (!name.trim() || !url.trim()) {
      message.warning('请填写服务名称和 URL');
      return;
    }
    setItems((prev) => [...prev, { item_type: 'service', name: name.trim(), target: url.trim() }]);
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (items.length === 0) {
        message.warning('请至少添加一项巡检内容');
        return;
      }
      const body = {
        name: values.name,
        description: values.description || '',
        items: items.map((i) => ({ item_type: i.item_type, name: i.name, target: i.target })),
      };
      if (editingId != null) {
        await request.put(`inspection/checklists/${editingId}`, body);
        message.success('更新成功');
      } else {
        await request.post('inspection/checklists', body);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchList();
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error(editingId != null ? '更新失败' : '创建失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await request.delete(`inspection/checklists/${id}`);
      message.success('已删除');
      fetchList();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '巡检项数', dataIndex: 'item_count', key: 'item_count', width: 100 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_: unknown, record: ChecklistRecord) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record.id)}>
            编辑
          </Button>
          <Popconfirm title="确定删除该清单？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="data-collection">
      <Card>
        <Space style={{ marginBottom: 16 }} align="center">
          <Title level={4} style={{ margin: 0 }}>
            日常巡检组件
          </Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建清单
          </Button>
        </Space>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={list}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingId != null ? '编辑巡检清单' : '新建巡检清单'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        width={720}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="清单名称" rules={[{ required: true, message: '请输入清单名称' }]}>
            <Input placeholder="如：核心网络每日巡检" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>

        <div style={{ marginTop: 16 }}>
          <Typography.Text strong>巡检项</Typography.Text>
          <div style={{ marginTop: 8, marginBottom: 8 }}>
            <Space wrap>
              <Select
                mode="multiple"
                placeholder="从 CMDB 选择设备"
                style={{ minWidth: 280 }}
                loading={cmdbLoading}
                onDropdownVisibleChange={(open) => open && loadCmdbDevices()}
                optionFilterProp="label"
                options={cmdbDevices.map((d) => ({
                  value: d.id,
                  label: `${d.name || '-'} (${d.ip_address || '-'})`,
                }))}
                value={selectedDeviceIds}
                onChange={(v: number[]) => setSelectedDeviceIds(v || [])}
                allowClear
              />
              <Button type="default" onClick={addDevicesFromCmdb} disabled={selectedDeviceIds.length === 0}>
                加入清单
              </Button>
              <AddServiceForm onAdd={addService} />
            </Space>
          </div>
          <Table
            size="small"
            rowKey={(_, i) => String(i)}
            dataSource={items.map((it, i) => ({ ...it, _index: i }))}
            columns={[
              { title: '类型', dataIndex: 'item_type', key: 'item_type', width: 80, render: (t: string) => (t === 'device' ? '设备' : '服务') },
              { title: '名称', dataIndex: 'name', key: 'name' },
              { title: 'IP / URL', dataIndex: 'target', key: 'target', ellipsis: true },
              {
                title: '操作',
                key: 'action',
                width: 80,
                render: (_: unknown, row: ChecklistItemRow & { _index: number }) => (
                  <Button type="link" size="small" danger onClick={() => removeItem(row._index)}>
                    删除
                  </Button>
                ),
              },
            ]}
            pagination={false}
          />
        </div>
      </Modal>
    </div>
  );
};

/** 手动添加服务名称 + URL */
const AddServiceForm: React.FC<{ onAdd: (name: string, url: string) => void }> = ({ onAdd }) => {
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const handleAdd = () => {
    onAdd(name, url);
    setName('');
    setUrl('');
  };
  return (
    <Space.Compact>
      <Input placeholder="服务名称" value={name} onChange={(e) => setName(e.target.value)} style={{ width: 120 }} />
      <Input placeholder="URL（如 https://api.example.com/health）" value={url} onChange={(e) => setUrl(e.target.value)} style={{ width: 240 }} />
      <Button type="default" onClick={handleAdd}>
        添加服务
      </Button>
    </Space.Compact>
  );
};

export default DataCollection;
