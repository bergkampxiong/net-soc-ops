import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Form,
  Input,
  Space,
  message,
  Popconfirm,
  Select,
  Typography,
  Row,
  Col,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import request from '../../utils/request';

const { Title } = Typography;

/** 清单项：设备或服务（item_type 提交时由 target 推断）；设备类型/厂商/位置仅展示用 */
interface ChecklistItemRow {
  item_type: 'device' | 'service';
  name: string;
  target: string;
  device_type?: string;
  vendor?: string;
  location?: string;
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

interface DeviceTypeOption {
  id: number;
  name: string;
}

interface VendorOption {
  id: number;
  name: string;
}

interface LocationOption {
  id: number;
  name: string;
}

/** 根据 target 推断为 URL 则 service，否则 device */
function inferItemType(target: string): 'device' | 'service' {
  const t = (target || '').trim();
  if (t.startsWith('http://') || t.startsWith('https://') || t.includes('://')) return 'service';
  return 'device';
}

/** 列表页 */
const ListView: React.FC = () => {
  const navigate = useNavigate();
  const [list, setList] = useState<ChecklistRecord[]>([]);
  const [loading, setLoading] = useState(false);

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
    { title: '巡检项数', dataIndex: 'item_count', key: 'item_count', width: 100 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_: unknown, record: ChecklistRecord) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => navigate(`${record.id}/edit`)}>
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
    <Card>
      <Space style={{ marginBottom: 16 }} align="center">
        <Title level={4} style={{ margin: 0 }}>
          日常巡检组件
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('create')}>
          新建清单
        </Button>
      </Space>
      <Table rowKey="id" loading={loading} columns={columns} dataSource={list} pagination={{ pageSize: 20 }} />
    </Card>
  );
};

/** 新建/编辑清单全页表单（底部 取消/确定，与 /cmdb/query 一致） */
const ChecklistFormPage: React.FC<{ mode: 'create' | 'edit'; id?: string }> = ({ mode, id }) => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [items, setItems] = useState<ChecklistItemRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [deviceTypeOptions, setDeviceTypeOptions] = useState<DeviceTypeOption[]>([]);
  const [vendorOptions, setVendorOptions] = useState<VendorOption[]>([]);
  const [locationOptions, setLocationOptions] = useState<LocationOption[]>([]);
  const [cmdbLoading, setCmdbLoading] = useState(false);
  const [deviceTypeId, setDeviceTypeId] = useState<number | undefined>();
  const [vendorId, setVendorId] = useState<number | undefined>();
  const [locationId, setLocationId] = useState<number | undefined>();

  useEffect(() => {
    const loadRef = async () => {
      try {
        const [typesRes, vendorsRes, locationsRes] = await Promise.all([
          request.get('/cmdb/device-types'),
          request.get('/cmdb/vendors'),
          request.get('/cmdb/locations'),
        ]);
        setDeviceTypeOptions(typesRes?.data ?? typesRes ?? []);
        setVendorOptions(vendorsRes?.data ?? vendorsRes ?? []);
        setLocationOptions(locationsRes?.data ?? locationsRes ?? []);
      } catch (e) {
        message.error('加载设备类型/厂商/位置失败');
      }
    };
    loadRef();
  }, []);

  useEffect(() => {
    if (mode === 'edit' && id) {
      setLoading(true);
      request
        .get<ChecklistRecord & { items?: ChecklistItemRow[] }>(`inspection/checklists/${id}`)
        .then((res) => {
          const data = res?.data ?? res;
          form.setFieldsValue({ name: data.name });
          setItems((data as any).items ?? []);
        })
        .catch(() => message.error('加载清单详情失败'))
        .finally(() => setLoading(false));
    } else {
      form.setFieldsValue({ name: '', description: '' });
      setItems([]);
    }
  }, [mode, id, form]);

  /** 按设备类型、厂商、位置查询 CMDB 并直接导入到下方巡检项列表 */
  const importDevicesFromCmdb = async () => {
    setCmdbLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (deviceTypeId != null) params.device_type_id = deviceTypeId;
      if (vendorId != null) params.vendor_id = vendorId;
      if (locationId != null) params.location_id = locationId;
      const res = await request.post<any[]>('/cmdb/assets/query', params);
      const raw = res?.data ?? res;
      const arr = Array.isArray(raw) ? raw : [];
      const existingTargets = new Set(items.map((i) => (i.target || '').trim()));
      const toAdd = arr
        .filter((a: any) => a.ip_address && !existingTargets.has((a.ip_address || '').trim()))
        .map((a: any) => ({
          item_type: 'device' as const,
          name: (a.name || a.ip_address || '').trim(),
          target: (a.ip_address || '').trim(),
          device_type: a.device_type?.name ?? '',
          vendor: a.vendor?.name ?? '',
          location: a.location?.name ?? '',
        }));
      setItems((prev) => [...prev, ...toAdd]);
      message.success(`已导入 ${toAdd.length} 台设备，不需要的可自行删除`);
    } catch (e) {
      message.error('导入 CMDB 设备失败');
    } finally {
      setCmdbLoading(false);
    }
  };

  const updateItemField = (index: number, field: 'name' | 'target', value: string) => {
    setItems((prev) => {
      const next = [...prev];
      if (next[index]) next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const addOneRow = () => {
    setItems((prev) => [...prev, { item_type: 'device', name: '', target: '' }]);
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const validItems = items.filter((i) => (i.name || '').trim() && (i.target || '').trim());
      if (validItems.length === 0) {
        message.warning('请至少添加一项巡检内容（名称与 IP/URL 均需填写）');
        return;
      }
      const body = {
        name: values.name,
        description: '',
        items: validItems.map((i) => ({
          item_type: inferItemType(i.target),
          name: (i.name || '').trim(),
          target: (i.target || '').trim(),
        })),
      };
      setSubmitLoading(true);
      if (mode === 'edit' && id) {
        await request.put(`inspection/checklists/${id}`, body);
        message.success('更新成功');
      } else {
        await request.post('inspection/checklists', body);
        message.success('创建成功');
      }
      navigate('..', { replace: true });
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error(mode === 'edit' ? '更新失败' : '创建失败');
    } finally {
      setSubmitLoading(false);
    }
  };

  return (
    <Card loading={loading}>
      <Space style={{ marginBottom: 16 }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('..')}>
          返回
        </Button>
        <Title level={4} style={{ margin: 0 }}>
          {mode === 'edit' ? '编辑巡检清单' : '新建巡检清单'}
        </Title>
      </Space>

      <Form form={form} layout="vertical">
        <Form.Item name="name" label="清单名称" rules={[{ required: true, message: '请输入清单名称' }]}>
          <Input placeholder="如：核心网络每日巡检" />
        </Form.Item>
      </Form>

      <Typography.Title level={5} style={{ marginTop: 24, marginBottom: 12 }}>
        从 CMDB 加入设备
      </Typography.Title>
      <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        按设备类型、厂商、位置筛选后点击「导入设备」，将直接加入下方列表；不需要的项可自行删除。
      </Typography.Text>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col flex="none">
          <Typography.Text type="secondary">设备类型：</Typography.Text>
          <Select
            placeholder="全部"
            allowClear
            style={{ width: 140, marginLeft: 8 }}
            options={deviceTypeOptions.map((t) => ({ value: t.id, label: t.name }))}
            value={deviceTypeId}
            onChange={setDeviceTypeId}
          />
        </Col>
        <Col flex="none">
          <Typography.Text type="secondary">厂商：</Typography.Text>
          <Select
            placeholder="全部"
            allowClear
            style={{ width: 140, marginLeft: 8 }}
            options={vendorOptions.map((v) => ({ value: v.id, label: v.name }))}
            value={vendorId}
            onChange={setVendorId}
          />
        </Col>
        <Col flex="none">
          <Typography.Text type="secondary">位置：</Typography.Text>
          <Select
            placeholder="全部"
            allowClear
            style={{ width: 140, marginLeft: 8 }}
            options={locationOptions.map((l) => ({ value: l.id, label: l.name }))}
            value={locationId}
            onChange={setLocationId}
          />
        </Col>
        <Col>
          <Button type="primary" onClick={importDevicesFromCmdb} loading={cmdbLoading}>
            导入设备
          </Button>
        </Col>
      </Row>

      <Typography.Title level={5} style={{ marginTop: 24, marginBottom: 12 }}>
        巡检项列表
      </Typography.Title>
      <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
        名称与 IP地址/URL 在同一表格填写，类型由系统根据 IP/URL 自动识别。
      </Typography.Text>
      <Space direction="vertical" style={{ width: '100%', marginBottom: 32 }}>
        <Button type="dashed" onClick={addOneRow} icon={<PlusOutlined />}>
          添加一行
        </Button>
        <Table
          size="small"
          rowKey={(_, i) => String(i)}
          dataSource={items.map((it, i) => ({ ...it, _index: i }))}
          pagination={false}
          columns={[
            {
              title: '名称',
              dataIndex: 'name',
              key: 'name',
              width: '22%',
              render: (val: string, row: ChecklistItemRow & { _index: number }) => (
                <Input
                  value={val}
                  onChange={(e) => updateItemField(row._index, 'name', e.target.value)}
                  placeholder="设备名称或服务名称"
                />
              ),
            },
            { title: '设备类型', dataIndex: 'device_type', key: 'device_type', width: '12%', render: (v: string) => v || '-' },
            { title: '厂商', dataIndex: 'vendor', key: 'vendor', width: '12%', render: (v: string) => v || '-' },
            {
              title: 'IP地址/URL',
              dataIndex: 'target',
              key: 'target',
              width: '22%',
              render: (val: string, row: ChecklistItemRow & { _index: number }) => (
                <Input
                  value={val}
                  onChange={(e) => updateItemField(row._index, 'target', e.target.value)}
                  placeholder="IP 或 URL"
                />
              ),
            },
            { title: '位置', dataIndex: 'location', key: 'location', width: '12%', render: (v: string) => v || '-' },
            {
              title: '操作',
              key: 'action',
              width: 80,
              render: (_: unknown, row: ChecklistItemRow & { _index: number }) => (
                <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => removeItem(row._index)}>
                  删除
                </Button>
              ),
            },
          ]}
        />
      </Space>

      <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16, textAlign: 'right' }}>
        <Space>
          <Button onClick={() => navigate('..')}>取消</Button>
          <Button type="primary" onClick={handleSubmit} loading={submitLoading}>
            确定
          </Button>
        </Space>
      </div>
    </Card>
  );
};

const DataCollection: React.FC = () => {
  const params = useParams<{ '*': string }>();
  const splat = params['*'] ?? '';

  if (splat === 'create') {
    return <ChecklistFormPage mode="create" />;
  }
  const editMatch = splat.match(/^(\d+)\/edit$/);
  if (editMatch) {
    return <ChecklistFormPage mode="edit" id={editMatch[1]} />;
  }
  return (
    <div className="data-collection">
      <ListView />
    </div>
  );
};

export default DataCollection;
