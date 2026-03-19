/**
 * IP 管理 - 网络地址导入：NetBox / phpIPAM + DHCP 采集配置（WMI）
 * 布局与系统管理页一致：左侧 Tabs + page-header
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, Form, Input, Button, Space, message, Switch, Table, Popconfirm, Row, Col, Select, Tabs, Typography } from 'antd';
import {
  CloudDownloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  GlobalOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import request from '../../../utils/request';

const { Title } = Typography;

interface CredentialOption {
  id: number;
  name: string;
  credential_type: string;
}

interface DhcpWmiTargetRow {
  id: number;
  name?: string;
  host: string;
  port?: number;
  use_ssl?: boolean;
  enabled?: boolean;
  windows_credential_id?: number | null;
}

const IPManagementImport: React.FC = () => {
  const [netboxLoading, setNetboxLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [netboxForm] = Form.useForm();
  const [phpipamForm] = Form.useForm();
  const [phpipamImporting, setPhpipamImporting] = useState(false);

  const [wmiTargets, setWmiTargets] = useState<DhcpWmiTargetRow[]>([]);
  const [wmiTargetsLoading, setWmiTargetsLoading] = useState(false);
  const [wmiSaveLoading, setWmiSaveLoading] = useState(false);
  const [wmiForm] = Form.useForm();
  const [editingWmiId, setEditingWmiId] = useState<number | null>(null);

  const [apiCredentials, setApiCredentials] = useState<CredentialOption[]>([]);
  const [windowsCredentials, setWindowsCredentials] = useState<CredentialOption[]>([]);

  const loadNetboxConfig = useCallback(async () => {
    setNetboxLoading(true);
    try {
      const res = await request.get('/config-module/import/netbox-config');
      const data = res.data?.data ?? res.data;
      const apiCredId = data?.api_credential_id ?? null;
      netboxForm.setFieldsValue({ base_url: data?.base_url ?? '', api_credential_id: apiCredId || undefined });
    } catch {
      netboxForm.setFieldsValue({ base_url: '', api_credential_id: undefined });
    } finally {
      setNetboxLoading(false);
    }
  }, [netboxForm]);

  const loadApiCredentials = useCallback(async () => {
    try {
      const res = await request.get('/device/credential/?credential_type=api_key&limit=100');
      const list = Array.isArray(res.data) ? res.data : [];
      setApiCredentials(list.map((c: CredentialOption) => ({ id: c.id, name: c.name, credential_type: c.credential_type })));
    } catch {
      setApiCredentials([]);
    }
  }, []);
  const loadWindowsCredentials = useCallback(async () => {
    try {
      const res = await request.get('/device/credential/?credential_type=windows_domain&limit=100');
      const list = Array.isArray(res.data) ? res.data : [];
      setWindowsCredentials(list.map((c: CredentialOption) => ({ id: c.id, name: c.name, credential_type: c.credential_type })));
    } catch {
      setWindowsCredentials([]);
    }
  }, []);

  const loadWmiTargets = useCallback(async () => {
    setWmiTargetsLoading(true);
    try {
      const res = await request.get('/config-module/dhcp/wmi-targets');
      const raw = res.data?.data ?? res.data;
      const items = Array.isArray(raw) ? raw : (Array.isArray(raw?.items) ? raw.items : []);
      setWmiTargets(items);
    } catch {
      setWmiTargets([]);
    } finally {
      setWmiTargetsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNetboxConfig();
  }, [loadNetboxConfig]);
  useEffect(() => {
    loadWmiTargets();
  }, [loadWmiTargets]);
  useEffect(() => {
    loadApiCredentials();
    loadWindowsCredentials();
  }, [loadApiCredentials, loadWindowsCredentials]);

  const saveNetboxConfig = async () => {
    const values = await netboxForm.validateFields();
    try {
      await request.post('/config-module/import/netbox-config', {
        base_url: values.base_url?.trim(),
        api_credential_id: values.api_credential_id ?? null,
      });
      message.success('配置已保存');
      loadNetboxConfig();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    }
  };

  const runImport = async () => {
    const values = await netboxForm.validateFields();
    setImporting(true);
    try {
      const res = await request.post('/config-module/import/netbox', {
        strategy: 'merge',
        base_url: values.base_url?.trim(),
        api_credential_id: values.api_credential_id ?? null,
      });
      const data = res.data?.data ?? res.data;
      message.success(
        `导入完成：Aggregates 新增 ${data?.aggregates_created ?? 0}、更新 ${data?.aggregates_updated ?? 0}；` +
        `Prefixes 新增 ${data?.prefixes_created ?? 0}、更新 ${data?.prefixes_updated ?? 0}`
      );
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '导入失败');
    } finally {
      setImporting(false);
    }
  };

  const runPhpipamImport = async () => {
    const values = await phpipamForm.validateFields();
    setPhpipamImporting(true);
    try {
      const res = await request.post('/config-module/import/phpipam', {
        api_base_url: values.phpipam_api_base_url?.trim(),
        api_credential_id: values.phpipam_api_credential_id,
        strategy: 'merge',
      });
      const data = res.data?.data ?? res.data;
      message.success(
        `phpIPAM 导入完成：Aggregates 新增 ${data?.aggregates_created ?? 0}、更新 ${data?.aggregates_updated ?? 0}；` +
        `Prefixes 新增 ${data?.prefixes_created ?? 0}、更新 ${data?.prefixes_updated ?? 0}`
      );
    } catch (e: any) {
      message.error(e?.response?.data?.detail || 'phpIPAM 导入失败');
    } finally {
      setPhpipamImporting(false);
    }
  };

  const saveWmiTarget = async () => {
    const values = await wmiForm.validateFields();
    setWmiSaveLoading(true);
    try {
      const payload = {
        name: values.name?.trim() || undefined,
        host: values.host?.trim(),
        port: 5985,
        use_ssl: false,
        enabled: values.enabled !== false,
        windows_credential_id: values.windows_credential_id ?? null,
      };
      if (editingWmiId != null) {
        await request.put(`/config-module/dhcp/wmi-targets/${editingWmiId}`, payload);
        message.success('采集目标已更新');
      } else {
        await request.post('/config-module/dhcp/wmi-targets', payload);
        message.success('采集目标已添加');
      }
      setEditingWmiId(null);
      wmiForm.resetFields();
      loadWmiTargets();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || (editingWmiId != null ? '更新失败' : '添加失败'));
    } finally {
      setWmiSaveLoading(false);
    }
  };

  const editWmiTarget = (row: DhcpWmiTargetRow) => {
    setEditingWmiId(row.id);
    wmiForm.setFieldsValue({
      name: row.name,
      host: row.host,
      enabled: row.enabled !== false,
      windows_credential_id: row.windows_credential_id ?? undefined,
    });
  };

  const deleteWmiTarget = async (id: number) => {
    try {
      await request.delete(`/config-module/dhcp/wmi-targets/${id}`);
      message.success('已删除');
      loadWmiTargets();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '删除失败');
    }
  };

  const tabItems = [
    {
      key: 'netbox',
      label: (
        <span>
          <DatabaseOutlined />
          NetBox
        </span>
      ),
      children: (
        <div>
          <Title level={4}>
            <DatabaseOutlined /> NetBox 导入
          </Title>
          <Card loading={netboxLoading}>
            <Form form={netboxForm} layout="vertical" style={{ maxWidth: 560 }}>
              <Form.Item name="base_url" label="NetBox 基础 URL" rules={[{ required: true, message: '请填写 NetBox 地址' }]}>
                <Input placeholder="https://netbox.example.com" />
              </Form.Item>
              <Form.Item name="api_credential_id" label="API 凭证" rules={[{ required: true, message: '请选择 API 凭证' }]}>
                <Select allowClear placeholder="请选择" options={apiCredentials.map(c => ({ value: c.id, label: c.name }))} />
              </Form.Item>
              <Form.Item>
                <Space wrap>
                  <Button onClick={saveNetboxConfig} loading={netboxLoading}>
                    保存配置
                  </Button>
                  <Button type="primary" icon={<CloudDownloadOutlined />} onClick={runImport} loading={importing}>
                    从 NetBox 导入 Aggregates 与 Prefixes
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </div>
      ),
    },
    {
      key: 'phpipam',
      label: (
        <span>
          <GlobalOutlined />
          phpIPAM
        </span>
      ),
      children: (
        <div>
          <Title level={4}>
            <GlobalOutlined /> phpIPAM 导入
          </Title>
          <Card>
            <Form form={phpipamForm} layout="vertical" style={{ maxWidth: 560 }}>
              <Form.Item
                name="phpipam_api_base_url"
                label="API 根路径"
                rules={[{ required: true, message: '请填写含 /api/应用名 的根路径' }]}
                extra="示例：https://phpipam.example.com/api/my_app"
              >
                <Input placeholder="https://phpipam.example.com/api/my_app" />
              </Form.Item>
              <Form.Item name="phpipam_api_credential_id" label="API 凭证" rules={[{ required: true, message: '请选择 API 凭证' }]}>
                <Select allowClear placeholder="请选择" options={apiCredentials.map(c => ({ value: c.id, label: c.name }))} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" icon={<CloudDownloadOutlined />} onClick={runPhpipamImport} loading={phpipamImporting}>
                  从 phpIPAM 导入 Aggregates 与 Prefixes
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </div>
      ),
    },
    {
      key: 'dhcp-wmi',
      label: (
        <span>
          <SettingOutlined />
          DHCP 采集
        </span>
      ),
      children: (
        <div>
          <Title level={4}>
            <SettingOutlined /> DHCP 采集配置（WMI / DCOM）
          </Title>
          <Card>
            <Form form={wmiForm} layout="vertical" style={{ marginBottom: 16 }} onFinish={saveWmiTarget}>
              <Row gutter={16}>
                <Col xs={24} sm={12} md={10}>
                  <Form.Item name="host" label="Windows DHCP 主机（IP 或主机名）" rules={[{ required: true, message: '必填' }]}>
                    <Input placeholder="IP 或主机名" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={10}>
                  <Form.Item name="windows_credential_id" label="Windows 登录凭证" rules={[{ required: true, message: '请选择 Windows 登录凭证' }]}>
                    <Select allowClear placeholder="请选择" options={windowsCredentials.map(c => ({ value: c.id, label: c.name }))} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={4}>
                  <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24}>
                  <Form.Item>
                    <Space>
                      <Button type="primary" htmlType="submit" loading={wmiSaveLoading} icon={<PlusOutlined />}>
                        {editingWmiId != null ? '更新' : '添加'}
                      </Button>
                      {editingWmiId != null && (
                        <Button onClick={() => { setEditingWmiId(null); wmiForm.resetFields(); }}>取消</Button>
                      )}
                    </Space>
                  </Form.Item>
                </Col>
              </Row>
            </Form>
            <Table
              rowKey="id"
              loading={wmiTargetsLoading}
              dataSource={wmiTargets}
              size="small"
              pagination={false}
              scroll={{ x: 680 }}
              columns={[
                { title: '主机', dataIndex: 'host', ellipsis: true, width: 160 },
                {
                  title: 'Windows 凭证',
                  dataIndex: 'windows_credential_id',
                  width: 160,
                  render: (id: number | null) => (id ? windowsCredentials.find(c => c.id === id)?.name ?? `#${id}` : '-'),
                },
                { title: '启用', dataIndex: 'enabled', width: 70, render: (v: boolean) => (v ? '是' : '否') },
                {
                  title: '操作',
                  width: 120,
                  fixed: 'right' as const,
                  render: (_: unknown, row: DhcpWmiTargetRow) => (
                    <Space>
                      <Button type="link" size="small" icon={<EditOutlined />} onClick={() => editWmiTarget(row)}>编辑</Button>
                      <Popconfirm title="确定删除该采集目标？" onConfirm={() => deleteWmiTarget(row.id)}>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]}
            />
          </Card>
        </div>
      ),
    },
  ];

  return (
    <div className="ip-network-import">
      <div className="page-header">
        <h2>网络地址导入</h2>
      </div>
      <Tabs defaultActiveKey="netbox" tabPosition="left" style={{ minHeight: 'calc(100vh - 200px)' }} items={tabItems} />
    </div>
  );
};

export default IPManagementImport;
