import React, { useEffect, useState } from 'react';
import {
  Table,
  Card,
  Form,
  Input,
  Button,
  Space,
  Modal,
  Drawer,
  Spin,
  message,
  Popconfirm,
} from 'antd';
import { useSearchParams } from 'react-router-dom';
import request from '../../utils/request';

interface BackupItem {
  id: number;
  device_id: string;
  device_name?: string;
  device_host?: string;
  source?: string;
  remark?: string;
  version_no?: number;
  created_at?: string;
  created_by?: string;
}

const ConfigModuleManagement: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<BackupItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailContent, setDetailContent] = useState<string>('');
  const [detailRecord, setDetailRecord] = useState<BackupItem | null>(null);
  const [diffVisible, setDiffVisible] = useState(false);
  const [diffText, setDiffText] = useState('');
  const [diffIds, setDiffIds] = useState<[number, number] | null>(null);

  const deviceIdFromUrl = searchParams.get('device_id') || undefined;

  const loadList = async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
        ...filters,
      };
      if (deviceIdFromUrl) params.device_id = deviceIdFromUrl;
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      const res = await request.get(`/config-module/backups?${qs}`);
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      const tot = data?.total ?? (Array.isArray(items) ? items.length : 0);
      setList(Array.isArray(items) ? items : []);
      setTotal(typeof tot === 'number' ? tot : 0);
    } catch (e) {
      message.error('加载备份列表失败');
      console.error(e);
      setList([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList();
  }, [page, pageSize, deviceIdFromUrl, JSON.stringify(filters)]);

  useEffect(() => {
    if (deviceIdFromUrl) form.setFieldsValue({ device_id: deviceIdFromUrl });
  }, [deviceIdFromUrl]);

  const onViewDetail = async (record: BackupItem) => {
    try {
      const res = await request.get(`/config-module/backups/${record.id}`);
      const d = res.data?.data ?? res.data;
      setDetailContent(d?.content ?? '');
      setDetailRecord(record);
      setDetailVisible(true);
    } catch (e) {
      message.error('加载配置详情失败');
    }
  };

  const onDiff = async (idA: number, idB: number) => {
    try {
      const res = await request.get(`/config-module/backups/diff?id_a=${idA}&id_b=${idB}`);
      const d = res.data?.data ?? res.data;
      setDiffText(d?.diff_text ?? '');
      setDiffIds([idA, idB]);
      setDiffVisible(true);
    } catch (e) {
      message.error('加载对比结果失败');
    }
  };

  const onDelete = async (id: number) => {
    try {
      await request.delete(`/config-module/backups/${id}`);
      message.success('已删除');
      loadList();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const [form] = Form.useForm();
  const onFinish = (v: Record<string, string>) => {
    setFilters(v);
    setPage(1);
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>配置管理</h2>
      <Card>
        <Form form={form} layout="inline" onFinish={onFinish} style={{ marginBottom: 16 }}>
          <Form.Item name="device_id" label="设备标识">
            <Input placeholder="设备ID" allowClear style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="device_host" label="主机">
            <Input placeholder="IP/主机名" allowClear style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="keyword" label="关键词">
            <Input placeholder="设备名/主机/备注" allowClear style={{ width: 160 }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">查询</Button>
              <Button onClick={() => { form.resetFields(); setFilters({}); setPage(1); }}>重置</Button>
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
            { title: '设备标识', dataIndex: 'device_id', ellipsis: true, width: 120 },
            { title: '设备名', dataIndex: 'device_name', ellipsis: true, width: 120 },
            { title: '主机', dataIndex: 'device_host', ellipsis: true, width: 120 },
            { title: '来源', dataIndex: 'source', width: 80 },
            { title: '备份时间', dataIndex: 'created_at', width: 180 },
            {
              title: '操作',
              key: 'action',
              width: 220,
              render: (_, record) => (
                <Space>
                  <a onClick={() => onViewDetail(record)}>查看</a>
                  <a
                    onClick={() => {
                      const idx = list.findIndex((r) => r.id === record.id);
                      if (idx > 0) onDiff(list[idx - 1].id, record.id);
                      else message.info('请选择同设备下另一版本进行对比');
                    }}
                  >
                    与上一版对比
                  </a>
                  <Popconfirm title="确定删除该备份？" onConfirm={() => onDelete(record.id)}>
                    <a style={{ color: '#ff4d4f' }}>删除</a>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Drawer
        title={`配置详情 - ${detailRecord?.device_id ?? ''}`}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        width={720}
      >
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 12 }}>
          {detailContent}
        </pre>
      </Drawer>

      <Modal
        title={diffIds ? `版本对比 (${diffIds[0]} vs ${diffIds[1]})` : '版本对比'}
        open={diffVisible}
        onCancel={() => setDiffVisible(false)}
        footer={null}
        width={800}
      >
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 12, maxHeight: 480, overflow: 'auto' }}>
          {diffText || '无差异'}
        </pre>
      </Modal>
    </div>
  );
};

export default ConfigModuleManagement;
