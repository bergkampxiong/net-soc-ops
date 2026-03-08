/**
 * IP 管理 - DHCP 服务管理 Level 2：某服务器的 Scopes 列表（PRD-IP管理功能）
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Table, Card, Button, Space, Progress } from 'antd';
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons';
import request from '../../../utils/request';
import { useNavigate, useParams } from 'react-router-dom';

interface ScopeRow {
  id: number;
  dhcp_server_id: number;
  name?: string;
  server_name?: string;
  network_address?: string;
  mask_cidr?: string;
  failover_mode?: string;
  enabled?: boolean;
  location?: string;
  vlan_id?: number;
  percent_used?: number;
  total_ips?: number;
  used_ips?: number;
  available_ips?: number;
}

const IPManagementDhcpScopes: React.FC = () => {
  const { serverId } = useParams<{ serverId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<ScopeRow[]>([]);

  const load = useCallback(async () => {
    if (!serverId) return;
    setLoading(true);
    try {
      const res = await request.get(`/config-module/dhcp/servers/${serverId}/scopes`);
      const data = res.data?.data ?? res.data;
      setList(Array.isArray(data?.items) ? data.items : []);
    } catch {
      setList([]);
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    load();
  }, [load]);

  const columns = [
    {
      title: 'Scope 名称',
      dataIndex: 'name',
      ellipsis: true,
      render: (t: string, r: ScopeRow) => (
        <a onClick={() => navigate(`/config-module/ip-management/dhcp/scopes/${r.id}`)}>{t || '-'}</a>
      ),
    },
    { title: '服务器名称', dataIndex: 'server_name', ellipsis: true },
    { title: '故障转移', dataIndex: 'failover_mode', width: 100 },
    {
      title: 'Addresses served',
      key: 'percent',
      width: 120,
      render: (_: unknown, r: ScopeRow) => (
        <Progress percent={r.percent_used ?? 0} size="small" />
      ),
    },
    { title: 'Address', dataIndex: 'network_address', width: 130 },
    { title: 'Mask/CIDR', dataIndex: 'mask_cidr', width: 120 },
    { title: 'Enabled', dataIndex: 'enabled', width: 80, render: (v: boolean) => (v ? 'Yes' : 'No') },
    { title: 'Location', dataIndex: 'location', ellipsis: true },
    { title: 'VLAN ID', dataIndex: 'vlan_id', width: 90 },
    { title: '% IPs used', dataIndex: 'percent_used', width: 100, render: (v: number) => (v != null ? `${v}%` : '-') },
    { title: 'Total IPs', dataIndex: 'total_ips', width: 90 },
    { title: 'Used IPs', dataIndex: 'used_ips', width: 90 },
    { title: 'Available IPs', dataIndex: 'available_ips', width: 100 },
  ];

  return (
    <Card
      title={`DHCP 作用域（服务器 ID: ${serverId}）`}
      extra={
        <Space>
          <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => navigate('/config-module/ip-management/dhcp')}>返回服务器列表</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={load}>刷新</Button>
        </Space>
      }
    >
      <Table rowKey="id" loading={loading} columns={columns} dataSource={list} size="small" pagination={false} />
    </Card>
  );
};

export default IPManagementDhcpScopes;
