/**
 * IP 管理 - DHCP 服务管理：从 WMI 同步 + 服务器列表（PRD-IP管理功能）
 * DHCP 采集配置（WMI）在网络导入菜单下维护
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Table, Card, Input, Select, Button, Space, message } from 'antd';
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import request from '../../../utils/request';
import { useNavigate } from 'react-router-dom';

interface DhcpServerRow {
  id: number;
  name?: string;
  type?: string;
  ip_address?: string;
  failover_status?: string;
  location?: string;
  vlan_id?: number;
  num_scopes?: number;
  percent_used?: number;
  total_ips?: number;
  used_ips?: number;
  available_ips?: number;
  status?: string;
}

const IPManagementDhcpServers: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<DhcpServerRow[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(20);
  const [filterLocation, setFilterLocation] = useState('');
  const [filterType, setFilterType] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [syncFromWmiLoading, setSyncFromWmiLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { skip, limit };
      if (filterLocation) params.location = filterLocation;
      if (filterType) params.server_type = filterType;
      if (filterStatus) params.status = filterStatus;
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      const res = await request.get(`/config-module/dhcp/servers?${qs}`);
      const data = res.data?.data ?? res.data;
      setList(Array.isArray(data?.items) ? data.items : []);
      setTotal(typeof data?.total === 'number' ? data.total : 0);
    } catch {
      setList([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [skip, limit, filterLocation, filterType, filterStatus]);

  useEffect(() => {
    load();
  }, [load]);

  const syncFromWmi = async () => {
    setSyncFromWmiLoading(true);
    try {
      const res = await request.post('/config-module/dhcp/sync-from-wmi');
      const data = res.data?.data ?? res.data;
      const success = data?.success !== false;
      if (success) {
        message.success(data?.message || '同步完成');
        load();
      } else {
        const errList = data?.error_per_target as Array<{ host?: string; error?: string }> | undefined;
        const msg = errList?.length
          ? errList.map((e) => `${e.host ?? ''}: ${e.error ?? ''}`).join('；')
          : data?.message || '同步失败';
        message.error(msg);
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const errList = e?.response?.data?.error_per_target;
      const msg = Array.isArray(errList) && errList.length
        ? errList.map((x: { host?: string; error?: string }) => `${x.host ?? ''}: ${x.error ?? ''}`).join('；')
        : typeof detail === 'string' ? detail : '从 WMI 同步失败';
      message.error(msg);
    } finally {
      setSyncFromWmiLoading(false);
    }
  };

  const columns = [
    {
      title: 'DHCP 服务器名称',
      dataIndex: 'name',
      ellipsis: true,
      render: (t: string, r: DhcpServerRow) => (
        <a onClick={() => navigate(`/config-module/ip-management/dhcp/servers/${r.id}`)}>{t || '-'}</a>
      ),
    },
    { title: '类型', dataIndex: 'type', width: 90 },
    { title: 'IP 地址', dataIndex: 'ip_address', width: 130 },
    { title: '故障转移', dataIndex: 'failover_status', width: 100 },
    { title: 'Location', dataIndex: 'location', ellipsis: true },
    { title: 'VLAN ID', dataIndex: 'vlan_id', width: 90 },
    { title: '作用域数', dataIndex: 'num_scopes', width: 90 },
    { title: '% IPs used', dataIndex: 'percent_used', width: 100, render: (v: number) => (v != null ? `${v}%` : '-') },
    { title: 'Total IPs', dataIndex: 'total_ips', width: 90 },
    { title: 'Used IPs', dataIndex: 'used_ips', width: 90 },
    { title: 'Available IPs', dataIndex: 'available_ips', width: 100 },
  ];

  return (
    <Card
      title="DHCP 服务器"
      extra={
        <Space>
          <Button size="small" icon={<SyncOutlined />} onClick={syncFromWmi} loading={syncFromWmiLoading}>从 WMI 同步</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={load}>刷新</Button>
        </Space>
      }
    >
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search placeholder="Location 筛选" allowClear style={{ width: 180 }} onSearch={(v) => { setFilterLocation(v); setSkip(0); }} />
        <Select placeholder="Server Type" allowClear style={{ width: 120 }} onChange={(v) => { setFilterType(v); setSkip(0); }} options={[{ value: 'Windows', label: 'Windows' }]} />
        <Select placeholder="Status" allowClear style={{ width: 100 }} onChange={(v) => { setFilterStatus(v); setSkip(0); }} options={[{ value: 'Up', label: 'Up' }]} />
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={list}
        pagination={{
          current: Math.floor(skip / limit) + 1,
          pageSize: limit,
          total,
          showSizeChanger: false,
          onChange: (page) => setSkip((page - 1) * limit),
        }}
        size="small"
      />
    </Card>
  );
};

export default IPManagementDhcpServers;
