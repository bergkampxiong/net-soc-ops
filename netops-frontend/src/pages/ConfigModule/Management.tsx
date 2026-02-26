import React, { useEffect, useState, useCallback } from 'react';
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
  Alert,
  Row,
  Col,
} from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import request from '../../utils/request';

interface DeviceRow {
  device_key: string;
  device_id: string;
  device_host?: string;
  device_name?: string;
  cmdb_name?: string;
  cmdb_model?: string;
  cmdb_vendor?: string;
  backup_count: number;
  latest_created_at?: string;
}

interface BackupItem {
  id: number;
  device_id: string;
  device_name?: string;
  device_host?: string;
  job_execution_id?: string;
  source?: string;
  remark?: string;
  version_no?: number;
  created_at?: string;
  created_by?: string;
}

interface FilterValues {
  device_name?: string;
  device_host?: string;
  model?: string;
  vendor?: string;
}

const ConfigModuleManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [deviceList, setDeviceList] = useState<DeviceRow[]>([]);
  const [filters, setFilters] = useState<FilterValues>({});
  const [selectedDevice, setSelectedDevice] = useState<DeviceRow | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyList, setHistoryList] = useState<BackupItem[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailContent, setDetailContent] = useState<string>('');
  const [detailRecord, setDetailRecord] = useState<BackupItem | null>(null);
  const [diffVisible, setDiffVisible] = useState(false);
  const [diffText, setDiffText] = useState('');
  const [diffIds, setDiffIds] = useState<[number, number] | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);

  const loadDevices = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filters.device_name?.trim()) params.device_name = filters.device_name.trim();
      if (filters.device_host?.trim()) params.device_host = filters.device_host.trim();
      if (filters.model?.trim()) params.model = filters.model.trim();
      if (filters.vendor?.trim()) params.vendor = filters.vendor.trim();
      const qs = new URLSearchParams(params).toString();
      const res = await request.get(`/config-module/backups/devices${qs ? `?${qs}` : ''}`);
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      setDeviceList(Array.isArray(items) ? items : []);
    } catch (e) {
      message.error('加载设备列表失败');
      console.error(e);
      setDeviceList([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const loadDeviceHistory = useCallback(async (device: DeviceRow) => {
    setHistoryLoading(true);
    setHistoryList([]);
    try {
      const params: Record<string, string> = {};
      if (device.device_host?.trim()) {
        params.device_host = device.device_host.trim();
      } else {
        params.device_id = device.device_id;
      }
      const qs = new URLSearchParams(params).toString();
      const res = await request.get(`/config-module/backups/device-history?${qs}`);
      const data = res.data?.data ?? res.data ?? res;
      const list = Array.isArray(data) ? data : [];
      setHistoryList(list);
    } catch (e) {
      message.error('加载备份历史失败');
      console.error(e);
      setHistoryList([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const openDrawer = (device: DeviceRow) => {
    setSelectedDevice(device);
    setDrawerVisible(true);
    setSelectedRowKeys([]);
    loadDeviceHistory(device);
  };

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

  const onDownload = async (record: BackupItem) => {
    try {
      const res = await request.get(`/config-module/backups/${record.id}`);
      const d = res.data?.data ?? res.data;
      const content = d?.content ?? '';
      const name =
        (record.device_name || record.device_host || record.device_id || 'device').replace(
          /[^\w\u4e00-\u9fa5.-]/g,
          '_'
        ) + `_${record.id}.txt`;
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
      message.success('已开始下载');
    } catch (e) {
      message.error('下载失败');
    }
  };

  const onDelete = async (id: number) => {
    try {
      await request.delete(`/config-module/backups/${id}`);
      message.success('已删除');
      if (selectedDevice) loadDeviceHistory(selectedDevice);
      loadDevices();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const onCompare = async () => {
    if (selectedRowKeys.length !== 2) {
      message.info('请勾选两条备份进行对比');
      return;
    }
    const [idA, idB] = selectedRowKeys;
    try {
      const res = await request.get(
        `/config-module/backups/diff?id_a=${idA}&id_b=${idB}`
      );
      const d = res.data?.data ?? res.data;
      setDiffText(d?.diff_text ?? '');
      setDiffIds([idA, idB]);
      setDiffVisible(true);
    } catch (e) {
      message.error('加载对比结果失败');
    }
  };

  const renderDiffLines = () => {
    if (!diffText) return <div>无差异</div>;
    const lines = diffText.split('\n');
    return (
      <div style={{ maxHeight: 480, overflow: 'auto', fontSize: 12, fontFamily: 'monospace' }}>
        {lines.map((line, i) => {
          const isAdd = line.startsWith('+') && !line.startsWith('+++');
          const isRemove = line.startsWith('-') && !line.startsWith('---');
          const style: React.CSSProperties = {
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            margin: 0,
            padding: '2px 6px',
            ...(isAdd && { backgroundColor: 'rgba(0, 200, 83, 0.2)' }),
            ...(isRemove && { backgroundColor: 'rgba(255, 82, 82, 0.15)' }),
          };
          return (
            <div key={i} style={style}>
              {line || '\n'}
            </div>
          );
        })}
      </div>
    );
  };

  const displayName = (row: DeviceRow) =>
    row.cmdb_name?.trim() || row.device_name?.trim() || row.device_host?.trim() || row.device_id || '-';
  const displayHost = (row: DeviceRow) =>
    row.device_host?.trim() || '-';

  const [form] = Form.useForm();
  const onFinish = (v: FilterValues) => setFilters(v);
  const onReset = () => {
    form.resetFields();
    setFilters({});
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>配置管理</h2>
      <Card>
        <Form form={form} layout="inline" onFinish={onFinish} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 8]} wrap style={{ width: '100%' }}>
            <Col xs={24} sm={12} md={6} lg={4}>
              <Form.Item name="device_name" label="设备名称" style={{ marginBottom: 8 }}>
                <Input placeholder="设备名称" allowClear style={{ width: '100%', minWidth: 120 }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6} lg={4}>
              <Form.Item name="device_host" label="IP 地址" style={{ marginBottom: 8 }}>
                <Input placeholder="IP 地址" allowClear style={{ width: '100%', minWidth: 120 }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6} lg={4}>
              <Form.Item name="model" label="设备型号" style={{ marginBottom: 8 }}>
                <Input placeholder="型号" allowClear style={{ width: '100%', minWidth: 120 }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6} lg={4}>
              <Form.Item name="vendor" label="厂商" style={{ marginBottom: 8 }}>
                <Input placeholder="厂商" allowClear style={{ width: '100%', minWidth: 120 }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6} lg={4}>
              <Form.Item style={{ marginBottom: 8 }}>
                <Space>
                  <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
                    查询
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={onReset}>
                    重置
                  </Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Form>
        <Table<DeviceRow>
          loading={loading}
          dataSource={deviceList}
          rowKey="device_key"
          size="small"
          pagination={false}
          tableLayout="fixed"
          scroll={{ x: 720 }}
          onRow={(record) => ({
            onClick: () => openDrawer(record),
            style: { cursor: 'pointer' },
          })}
          columns={[
            {
              title: '设备名称',
              dataIndex: 'device_name',
              key: 'device_name',
              width: 120,
              ellipsis: true,
              render: (_, row) => displayName(row),
            },
            {
              title: 'IP 地址',
              dataIndex: 'device_host',
              key: 'device_host',
              width: 120,
              ellipsis: true,
              render: (_, row) => displayHost(row),
            },
            {
              title: '设备型号',
              dataIndex: 'cmdb_model',
              key: 'cmdb_model',
              width: 120,
              ellipsis: true,
              render: (v: string) => v?.trim() || '-',
            },
            {
              title: '厂商',
              dataIndex: 'cmdb_vendor',
              key: 'cmdb_vendor',
              width: 120,
              ellipsis: true,
              render: (v: string) => v?.trim() || '-',
            },
            {
              title: '备份数量',
              dataIndex: 'backup_count',
              key: 'backup_count',
              width: 120,
            },
            {
              title: '最近备份时间',
              dataIndex: 'latest_created_at',
              key: 'latest_created_at',
              width: 120,
              ellipsis: true,
              render: (t: string) => (t ? new Date(t).toLocaleString() : '-'),
            },
          ]}
        />
      </Card>

      <Drawer
        title={
          selectedDevice
            ? `备份详情 - ${displayName(selectedDevice)} (${displayHost(selectedDevice)})`
            : '备份详情'
        }
        open={drawerVisible}
        onClose={() => {
          setDrawerVisible(false);
          setSelectedDevice(null);
        }}
        width={720}
      >
        <Spin spinning={historyLoading}>
          <div style={{ marginBottom: 16 }}>
            <Space>
              <span>勾选两版后点击对比</span>
              <Button
                type="primary"
                onClick={onCompare}
                disabled={selectedRowKeys.length !== 2}
              >
                对比
              </Button>
            </Space>
          </div>
          <Table<BackupItem>
            dataSource={historyList}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
            rowSelection={{
              selectedRowKeys: selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys as number[]),
              type: 'checkbox',
              getCheckboxProps: (record) => ({
                disabled:
                  selectedRowKeys.length >= 2 && !selectedRowKeys.includes(record.id),
              }),
            }}
            columns={[
              {
                title: '作业执行 ID',
                dataIndex: 'job_execution_id',
                key: 'job_execution_id',
                width: 140,
                ellipsis: true,
                render: (v) => v || '-',
              },
              {
                title: '备份时间',
                dataIndex: 'created_at',
                key: 'created_at',
                width: 180,
                render: (t: string) => (t ? new Date(t).toLocaleString() : '-'),
              },
              {
                title: '操作',
                key: 'action',
                width: 200,
                render: (_, record) => (
                  <Space>
                    <a onClick={() => onViewDetail(record)}>查看</a>
                    <a onClick={() => onDownload(record)}>下载</a>
                    <Popconfirm
                      title="确定删除该备份？"
                      onConfirm={() => onDelete(record.id)}
                    >
                      <a style={{ color: '#ff4d4f' }}>删除</a>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Spin>
      </Drawer>

      <Drawer
        title={`配置详情 - ${detailRecord?.device_name ?? detailRecord?.device_host ?? ''}`}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        width={720}
      >
        {detailContent &&
          /Error:|Unrecognized command|invalid input|%\s*Error/i.test(detailContent) && (
            <Alert
              type="warning"
              showIcon
              message="该备份内容可能为设备报错而非完整配置"
              description="备份时设备可能未识别命令或处于错误模式，请检查流程中该设备的设备类型与备份命令是否正确，必要时重新执行备份。"
              style={{ marginBottom: 16 }}
            />
          )}
        <pre
          style={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            fontSize: 12,
          }}
        >
          {detailContent}
        </pre>
      </Drawer>

      <Modal
        title={
          diffIds
            ? `版本对比 (${diffIds[0]} vs ${diffIds[1]})`
            : '版本对比'
        }
        open={diffVisible}
        onCancel={() => setDiffVisible(false)}
        footer={null}
        width={800}
      >
        {renderDiffLines()}
      </Modal>
    </div>
  );
};

export default ConfigModuleManagement;
