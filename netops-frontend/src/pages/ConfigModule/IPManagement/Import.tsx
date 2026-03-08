/**
 * IP 管理 - 网络导入：NetBox 迁移 + DHCP 采集配置（WMI）（PRD-IP管理功能）
 * NetBox 可选用 API 凭证；DHCP WMI 可选用 Windows/域控凭证。
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, Form, Input, Button, Space, message, Switch, Table, Popconfirm, Row, Col, Select } from 'antd';
import { CloudDownloadOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import request from '../../../utils/request';

interface NetboxConfig {
  base_url: string;
  api_token?: string;
  api_credential_id?: number | null;
}

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
  username?: string;
  password?: string;
  use_ssl?: boolean;
  enabled?: boolean;
  windows_credential_id?: number | null;
}

const IPManagementImport: React.FC = () => {
  const [netboxLoading, setNetboxLoading] = useState(false);
  const [netboxConfig, setNetboxConfig] = useState<NetboxConfig>({ base_url: '', api_token: undefined });
  const [importing, setImporting] = useState(false);
  const [form] = Form.useForm();

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
      setNetboxConfig({ base_url: data?.base_url ?? '', api_token: data?.api_token, api_credential_id: apiCredId });
      form.setFieldsValue({ base_url: data?.base_url ?? '', api_token: '', api_credential_id: apiCredId || undefined });
    } catch {
      form.setFieldsValue({ base_url: '', api_token: '', api_credential_id: undefined });
    } finally {
      setNetboxLoading(false);
    }
  }, [form]);

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
      const data = res.data?.data ?? res.data;
      setWmiTargets(Array.isArray(data?.items) ? data.items : []);
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
    const values = await form.validateFields();
    try {
      await request.post('/config-module/import/netbox-config', {
        base_url: values.base_url?.trim(),
        api_token: values.api_token?.trim() || undefined,
        api_credential_id: values.api_credential_id ?? null,
      });
      message.success('配置已保存');
      loadNetboxConfig();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败');
    }
  };

  const runImport = async () => {
    setImporting(true);
    try {
      const res = await request.post('/config-module/import/netbox', { strategy: 'merge' });
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

  const saveWmiTarget = async () => {
    const values = await wmiForm.validateFields();
    setWmiSaveLoading(true);
    try {
      const payload = {
        name: values.name?.trim() || undefined,
        host: values.host?.trim(),
        port: values.port != null ? Number(values.port) : 5985,
        username: values.username?.trim() || undefined,
        password: values.password?.trim() || undefined,
        use_ssl: !!values.use_ssl,
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
      port: row.port ?? 5985,
      username: row.username,
      password: '',
      use_ssl: row.use_ssl ?? false,
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

  return (
    <Card title="网络导入">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Card title="NetBox 迁移" size="small" type="inner">
          <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
            <Form.Item name="base_url" label="NetBox 基础 URL" rules={[{ required: true }]} style={{ minWidth: 280 }}>
              <Input placeholder="https://netbox.example.com" />
            </Form.Item>
            <Form.Item name="api_credential_id" label="API 凭证" style={{ width: 200 }}>
              <Select allowClear placeholder="可选，选择后优先使用" options={apiCredentials.map(c => ({ value: c.id, label: c.name }))} />
            </Form.Item>
            <Form.Item name="api_token" label="API Token">
              <Input.Password placeholder="未选凭证时使用" style={{ width: 200 }} />
            </Form.Item>
            <Form.Item>
              <Button onClick={saveNetboxConfig} loading={netboxLoading}>保存配置</Button>
            </Form.Item>
          </Form>
          <Button type="primary" icon={<CloudDownloadOutlined />} onClick={runImport} loading={importing}>
            从 NetBox 导入 Aggregates 与 Prefixes
          </Button>
        </Card>
        <Card title="DHCP 采集配置（WMI）" size="small" type="inner">
          <Form form={wmiForm} layout="vertical" style={{ marginBottom: 16 }} onFinish={saveWmiTarget}>
            <Row gutter={16}>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="host" label="Windows 主机（IP 或主机名）" rules={[{ required: true, message: '必填' }]}>
                  <Input placeholder="IP 或主机名" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={4}>
                <Form.Item name="port" label="端口" initialValue={5985}>
                  <Input type="number" placeholder="5985" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="windows_credential_id" label="Windows 登录凭证">
                  <Select allowClear placeholder="可选，选择后优先使用" options={windowsCredentials.map(c => ({ value: c.id, label: c.name }))} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="username" label="用户名">
                  <Input placeholder="未选凭证时填写" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Form.Item name="password" label="密码">
                  <Input.Password placeholder={editingWmiId != null ? '留空不修改' : '未选凭证时填写'} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={4}>
                <Form.Item name="use_ssl" label="HTTPS" valuePropName="checked" initialValue={false}>
                  <Switch />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={4}>
                <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
                  <Switch />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8} lg={4}>
                <Form.Item label=" " colon={false}>
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
            scroll={{ x: 780 }}
            columns={[
              { title: '主机', dataIndex: 'host', ellipsis: true, width: 140 },
              { title: '端口', dataIndex: 'port', width: 70 },
              {
                title: 'Windows 凭证',
                dataIndex: 'windows_credential_id',
                width: 100,
                render: (id: number | null) => (id ? windowsCredentials.find(c => c.id === id)?.name ?? `#${id}` : '-'),
              },
              { title: '用户名', dataIndex: 'username', ellipsis: true, width: 100 },
              { title: '密码', dataIndex: 'password', width: 80, render: () => '***' },
              { title: 'HTTPS', dataIndex: 'use_ssl', width: 70, render: (v: boolean) => (v ? '是' : '否') },
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
      </Space>
    </Card>
  );
};

export default IPManagementImport;
