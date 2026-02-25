import React, { useEffect, useState } from 'react';
import { Card, Table, Spin, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import request from '../../utils/request';

interface Stats {
  device_count: number;
  backup_24h_success: number;
  backup_24h_fail: number;
  backup_7d_success: number;
  backup_7d_fail: number;
  change_count_7d: number;
  compliance_pass_rate?: number;
}

interface RecentBackup {
  id: number;
  device_id: string;
  device_name?: string;
  device_host?: string;
  source?: string;
  created_at?: string;
}

const ConfigModuleSummary: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentBackups, setRecentBackups] = useState<RecentBackup[]>([]);

  useEffect(() => {
    const fetch = async () => {
      try {
        const [statsRes, recentRes] = await Promise.all([
          request.get('/config-module/summary/stats'),
          request.get('/config-module/summary/recent-backups?limit=10'),
        ]);
        if (statsRes.data?.data) setStats(statsRes.data.data as Stats);
        else if (typeof statsRes.data === 'object' && 'device_count' in statsRes.data) setStats(statsRes.data as Stats);
        else setStats(statsRes.data as Stats);
        const list = recentRes.data?.data ?? recentRes.data;
        setRecentBackups(Array.isArray(list) ? list : []);
      } catch (e) {
        message.error('加载配置摘要失败');
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>配置摘要</h2>
      <div style={{ marginBottom: 24, display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        <Card title="已纳入配置管理的设备数" size="small" style={{ minWidth: 200 }}>
          {stats?.device_count ?? 0}
        </Card>
        <Card title="最近 24 小时备份数" size="small" style={{ minWidth: 200 }}>
          {stats?.backup_24h_success ?? 0}
          {stats?.backup_24h_fail ? ` / 失败 ${stats.backup_24h_fail}` : ''}
        </Card>
        <Card title="最近 7 天备份数" size="small" style={{ minWidth: 200 }}>
          {stats?.backup_7d_success ?? 0}
          {stats?.backup_7d_fail ? ` / 失败 ${stats.backup_7d_fail}` : ''}
        </Card>
        <Card title="最近 7 天变更次数" size="small" style={{ minWidth: 200 }}>
          {stats?.change_count_7d ?? 0}
        </Card>
        {stats?.compliance_pass_rate != null && (
          <Card title="合规通过率" size="small" style={{ minWidth: 200 }}>
            {((stats.compliance_pass_rate ?? 0) * 100).toFixed(1)}%
          </Card>
        )}
      </div>
      <Card title="最近备份">
        <Table
          dataSource={recentBackups}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            { title: '设备标识', dataIndex: 'device_id', key: 'device_id', width: 120 },
            { title: '设备名', dataIndex: 'device_name', key: 'device_name', width: 120 },
            { title: '主机', dataIndex: 'device_host', key: 'device_host', width: 120 },
            { title: '来源', dataIndex: 'source', key: 'source', width: 80 },
            { title: '备份时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
            {
              title: '操作',
              key: 'action',
              render: (_, r) => (
                <a onClick={() => navigate(`/config-module/management?device_id=${encodeURIComponent(r.device_id)}`)}>
                  查看
                </a>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default ConfigModuleSummary;
