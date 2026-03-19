/**
 * IP 管理 - DHCP 服务管理 Level 3：某 Scope 的 IP 列表（租约/保留）（PRD-IP管理功能）
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Table, Card, Button, Modal, Form, Select, message } from 'antd';
import { ArrowLeftOutlined, ReloadOutlined, LinkOutlined } from '@ant-design/icons';
import request from '../../../utils/request';
import { useNavigate, useParams } from 'react-router-dom';

interface LeaseRow {
  id: number;
  scope_id: number;
  ip_address?: string;
  mac?: string;
  client_name?: string;
  is_reservation?: boolean;
  last_response?: string;
  response_time?: number;
  status?: string;
}

const IPManagementDhcpScopeIps: React.FC = () => {
  const { scopeId } = useParams<{ scopeId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<LeaseRow[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  const [scopeInfo, setScopeInfo] = useState<{ name?: string; server_name?: string } | null>(null);
  const [linkModalVisible, setLinkModalVisible] = useState(false);
  const [prefixOptions, setPrefixOptions] = useState<{ value: number; label: string }[]>([]);
  const [form] = Form.useForm();

  const loadScope = useCallback(async () => {
    if (!scopeId) return;
    try {
      const res = await request.get(`/config-module/dhcp/scopes/${scopeId}`);
      const data = res.data?.data ?? res.data;
      setScopeInfo({ name: data?.name, server_name: data?.server_name });
    } catch {
      setScopeInfo(null);
    }
  }, [scopeId]);

  const load = useCallback(async () => {
    if (!scopeId) return;
    setLoading(true);
    try {
      const res = await request.get(`/config-module/dhcp/scopes/${scopeId}/ips?skip=${skip}&limit=${limit}`);
      const data = res.data?.data ?? res.data;
      setList(Array.isArray(data?.items) ? data.items : []);
      setTotal(typeof data?.total === 'number' ? data.total : 0);
    } catch {
      setList([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [scopeId, skip, limit]);

  const loadPrefixOptions = useCallback(async () => {
    try {
      const res = await request.get('/config-module/ipam/prefixes?limit=100');
      const data = res.data?.data ?? res.data;
      const items = Array.isArray(data?.items) ? data.items : [];
      setPrefixOptions(items.map((p: { id: number; prefix: string }) => ({ value: p.id, label: p.prefix })));
    } catch {
      setPrefixOptions([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    loadScope();
  }, [loadScope]);

  const openLinkModal = async () => {
    await loadPrefixOptions();
    let suggestedPrefixId: number | null = null;
    if (scopeId) {
      try {
        const res = await request.get(`/config-module/dhcp/scopes/${scopeId}/suggest-prefix`);
        const data = res.data?.data ?? res.data ?? res;
        if (data?.prefix_id != null) {
          suggestedPrefixId = data.prefix_id;
        }
      } catch {
        // 忽略失败，不预填
      }
    }
    form.setFieldsValue({ prefix_id: suggestedPrefixId ?? undefined });
    setLinkModalVisible(true);
  };

  const handleLinkPrefix = async () => {
    const values = await form.validateFields();
    try {
      await request.post(`/config-module/dhcp/scopes/${scopeId}/link-prefix`, { prefix_id: values.prefix_id });
      message.success('关联已更新');
      setLinkModalVisible(false);
      loadScope();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失败');
    }
  };

  const columns = [
    { title: 'Address', dataIndex: 'ip_address', width: 130 },
    { title: 'Status', dataIndex: 'status', width: 100 },
    { title: 'MAC', dataIndex: 'mac', width: 140 },
    { title: 'Scope Name', dataIndex: 'scopeName', width: 140, render: () => scopeInfo?.name ?? '-' },
    { title: 'DHCP Client Name', dataIndex: 'client_name', ellipsis: true },
    { title: 'DHCP Reservation', dataIndex: 'is_reservation', width: 120, render: (v: boolean) => (v ? 'Yes' : 'No') },
    { title: 'Last Response', dataIndex: 'last_response', width: 160 },
    { title: 'Response Time', dataIndex: 'response_time', width: 100 },
  ];

  return (
    <Card
      title={`Scope IP 列表（${scopeInfo?.name ?? scopeId}）`}
      extra={
        <span>
          <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
          <Button size="small" icon={<LinkOutlined />} onClick={openLinkModal} style={{ marginLeft: 8 }}>关联到 Prefix</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={load} style={{ marginLeft: 8 }}>刷新</Button>
        </span>
      }
    >
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={list}
        size="small"
        pagination={{
          current: Math.floor(skip / limit) + 1,
          pageSize: limit,
          total,
          showSizeChanger: false,
          onChange: (page) => setSkip((page - 1) * limit),
        }}
      />
      <Modal title="关联到 Prefix" open={linkModalVisible} onOk={handleLinkPrefix} onCancel={() => setLinkModalVisible(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="prefix_id" label="选择 Prefix">
            <Select allowClear placeholder="可选，置空则解除关联" options={prefixOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default IPManagementDhcpScopeIps;
