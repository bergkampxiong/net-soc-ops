/**
 * IP 管理 - Prefix 详情：展示单条 Prefix 及关联 DHCP Scope，回链到所属 Aggregate
 */
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, Descriptions, Table, message } from 'antd';
import request from '../../../utils/request';

interface PrefixDetailData {
  id: number;
  prefix: string;
  status: string;
  description?: string;
  is_pool?: boolean;
  mark_utilized?: boolean;
  vlan_id?: number;
  location?: string;
  aggregate_id?: number;
  created_at?: string;
  updated_at?: string;
  linked_dhcp_scopes?: Array<Record<string, unknown>>;
}

const IPManagementPrefixDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<PrefixDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [aggregatePrefix, setAggregatePrefix] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    request.get(`/config-module/ipam/prefixes/${id}`)
      .then((res) => {
        const data = res.data?.data ?? res.data;
        if (!cancelled) setDetail(data);
        const aggId = data?.aggregate_id;
        if (aggId) {
          return request.get(`/config-module/ipam/aggregates/${aggId}`).then((r) => {
            const agg = r.data?.data ?? r.data;
            if (!cancelled && agg?.prefix) setAggregatePrefix(agg.prefix);
          });
        }
      })
      .catch(() => {
        if (!cancelled) message.error('加载失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  if (loading || !detail) {
    return <Card loading={loading}>加载中…</Card>;
  }

  const scopeColumns = [
    { title: 'Scope 名称', dataIndex: 'name', key: 'name' },
    { title: '网络地址', dataIndex: 'network_address', key: 'network_address' },
    { title: '已用/总数', key: 'ips', render: (_: unknown, r: Record<string, unknown>) => `${r.used_ips ?? 0}/${r.total_ips ?? 0}` },
  ];

  return (
    <div>
      <Card>
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label="Prefix">{detail.prefix}</Descriptions.Item>
          <Descriptions.Item label="Status">{detail.status}</Descriptions.Item>
          <Descriptions.Item label="描述">{detail.description || '—'}</Descriptions.Item>
          <Descriptions.Item label="VLAN ID">{detail.vlan_id ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="Location">{detail.location || '—'}</Descriptions.Item>
          <Descriptions.Item label="所属 Aggregate">
            {detail.aggregate_id ? (
              <Link to={`/config-module/ip-management/aggregates/${detail.aggregate_id}`}>
                {aggregatePrefix ?? `Aggregate #${detail.aggregate_id}`}
              </Link>
            ) : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{detail.created_at ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{detail.updated_at ?? '—'}</Descriptions.Item>
        </Descriptions>
        {detail.linked_dhcp_scopes && detail.linked_dhcp_scopes.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h4>关联的 DHCP Scope</h4>
            <Table
              rowKey="id"
              size="small"
              columns={scopeColumns}
              dataSource={detail.linked_dhcp_scopes as Record<string, unknown>[]}
              pagination={false}
            />
          </div>
        )}
      </Card>
    </div>
  );
};

export default IPManagementPrefixDetail;
