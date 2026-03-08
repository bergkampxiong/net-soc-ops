import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Input,
  Select,
  DatePicker,
  message,
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Modal,
  Tooltip
} from 'antd';
import {
  SearchOutlined,
  ExportOutlined,
  EyeOutlined,
  DeleteOutlined,
  FileSearchOutlined,
  UserOutlined,
  ClockCircleOutlined,
  SafetyOutlined
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import request from '../../utils/request';
import { formatBeijingToSecond, getDisplayTimezone } from '../../utils/formatTime';

const { RangePicker } = DatePicker;
const { Title } = Typography;
const { Option } = Select;

dayjs.extend(utc);
dayjs.extend(timezone);

interface AuditLog {
  id: number;
  username: string;
  event_type: string;
  ip_address: string;
  timestamp: string;
  details: string | object;
  success: boolean;
  user_agent?: string;
}

/** 事件类型中文文案（与后端 event_type 一致） */
const EVENT_TYPE_MAP: Record<string, string> = {
  login_success: '登录成功',
  first_login: '首次登录',
  logout: '登出',
  login_failed: '登录失败',
  ldap_login: 'LDAP登录',
  ldap_login_success: 'LDAP登录成功',
  ldap_login_failed: 'LDAP登录失败',
  ldap_login_2fa_required: 'LDAP需2FA验证',
  '2fa_failed': '2FA验证失败',
  totp_setup: '设置2FA',
  totp_verify: '验证2FA',
  totp_enabled: '启用2FA',
  create_user: '创建用户',
  delete_user: '删除用户',
  update_user: '更新用户',
  update_role: '更新角色',
  update_department: '更新部门',
  toggle_user_status: '切换用户状态',
  change_password: '修改密码',
  reset_password: '重置密码',
  toggle_2fa: '切换2FA状态',
  create_ldap_config: '创建LDAP配置',
  update_ldap_config: '更新LDAP配置',
  delete_ldap_config: '删除LDAP配置',
  create_ldap_template: '创建LDAP模板',
  update_ldap_template: '更新LDAP模板',
  delete_ldap_template: '删除LDAP模板',
};

interface EventTypeOption {
  event_type: string;
  category: string;
}

const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [eventType, setEventType] = useState<string>('');
  const [eventTypeOptions, setEventTypeOptions] = useState<EventTypeOption[]>([]);
  const [searchText, setSearchText] = useState('');
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [userRole, setUserRole] = useState<string>('');
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  useEffect(() => {
    fetchLogs();
  }, []);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const res = await request.get<{ role?: string }>('/auth/me');
        if (res?.data?.role) setUserRole(res.data.role);
      } catch {
        // 忽略
      }
    };
    loadUser();
  }, []);

  useEffect(() => {
    const loadEventTypes = async () => {
      try {
        const res = await request.get<EventTypeOption[]>('/api/audit/event-types');
        if (Array.isArray(res?.data)) setEventTypeOptions(res.data);
      } catch {
        // 忽略失败，使用静态 eventTypeMap 的 key 作为备选
        setEventTypeOptions(Object.keys(EVENT_TYPE_MAP).map(et => ({ event_type: et, category: 'other' })));
      }
    };
    loadEventTypes();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params: any = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
      };
      if (eventType) params.event_type = eventType;
      if (dateRange && dateRange[0] && dateRange[1]) {
        const tz = getDisplayTimezone();
        params.start_date = dateRange[0].tz(tz).format('YYYY-MM-DDTHH:mm:ss');
        params.end_date = dateRange[1].tz(tz).format('YYYY-MM-DDTHH:mm:ss');
      }

      const response = await request.get('/api/audit/logs', { params });

      // 确保response.data存在且包含items和total
      if (response && response.data) {
        // 如果返回的是数组，直接使用
        if (Array.isArray(response.data)) {
          setLogs(response.data);
          setTotal(response.data.length);
        }
        // 如果返回的是对象，检查是否有items和total
        else if (response.data.items) {
          setLogs(response.data.items);
          setTotal(response.data.total || response.data.items.length);
        }
        // 如果格式不符合预期，设置为空数组
        else {
          setLogs([]);
          setTotal(0);
        }
      } else {
        setLogs([]);
        setTotal(0);
      }
    } catch (error) {
      console.error('获取审计日志失败:', error);
      message.error('获取审计日志失败');
      setLogs([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    fetchLogs();
  };

  const handleExport = () => {
    const params: any = {
      eventType: eventType,
      searchText: searchText
    };

    if (dateRange) {
      const tz = getDisplayTimezone();
      params.startTime = dateRange[0].tz(tz).format('YYYY-MM-DD HH:mm:ss');
      params.endTime = dateRange[1].tz(tz).format('YYYY-MM-DD HH:mm:ss');
    }

    // 构建查询字符串
    const queryString = Object.entries(params)
      .filter(([_, value]) => value !== undefined && value !== '')
      .map(([key, value]) => `${key}=${encodeURIComponent(value as string)}`)
      .join('&');

    // 创建下载链接
    const url = `/api/audit/logs/export?${queryString}`;
    window.open(url, '_blank');
  };

  const showDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setDetailsVisible(true);
  };

  const handleDeleteSingle = (record: AuditLog) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除该条审计日志吗？`,
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await request.delete(`/api/audit/logs/${record.id}`);
          message.success('已删除');
          fetchLogs();
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的日志');
      return;
    }
    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 条审计日志吗？`,
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await request.post('/api/audit/logs/batch-delete', { ids: selectedRowKeys });
          message.success('已删除');
          setSelectedRowKeys([]);
          fetchLogs();
        } catch (e: any) {
          message.error(e?.response?.data?.detail || '删除失败');
        }
      },
    });
  };

  const columns = [
    {
title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (t: string) => formatBeijingToSecond(t),
      sorter: (a: AuditLog, b: AuditLog) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '操作',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (event_type: string) => EVENT_TYPE_MAP[event_type] ?? event_type,
    },
    {
      title: '状态',
      dataIndex: 'success',
      key: 'success',
      render: (success: boolean) => {
        const color = success ? 'green' : 'red';
        const text = success ? '成功' : '失败';
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: AuditLog) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showDetails(record)}
          >
            详情
          </Button>
          {userRole === 'admin' && (
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteSingle(record)}
            >
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="audit-logs">
      <Card>
        <Title level={3}>审计日志</Title>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card>
              <Statistic
                title="总日志数"
                value={total}
                prefix={<FileSearchOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="成功操作"
                value={logs ? logs.filter(log => log.success).length : 0}
                prefix={<SafetyOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="失败操作"
                value={logs ? logs.filter(log => !log.success).length : 0}
                prefix={<SafetyOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }}>
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [Dayjs, Dayjs])}
          />
          <Select
            style={{ width: 220 }}
            placeholder="选择事件类型"
            value={eventType || undefined}
            onChange={setEventType}
            allowClear
          >
            {eventTypeOptions.map((opt) => (
              <Option key={opt.event_type} value={opt.event_type}>
                {EVENT_TYPE_MAP[opt.event_type] ?? opt.event_type}
              </Option>
            ))}
          </Select>
          <Input
            placeholder="搜索..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            prefix={<SearchOutlined />}
            style={{ width: 200 }}
          />
          <Button type="primary" onClick={handleSearch}>
            搜索
          </Button>
          <Button icon={<ExportOutlined />} onClick={handleExport}>
            导出
          </Button>
          {userRole === 'admin' && (
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleBatchDelete}
              disabled={selectedRowKeys.length === 0}
            >
              批量删除{selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length})` : ''}
            </Button>
          )}
        </Space>

        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          rowSelection={userRole === 'admin' ? { selectedRowKeys, onChange: setSelectedRowKeys } : undefined}
        />

        <Modal
          title="日志详情"
          open={detailsVisible}
          onCancel={() => setDetailsVisible(false)}
          footer={null}
          width={800}
        >
          {selectedLog && (
            <div>
              <p><strong>时间：</strong>{formatBeijingToSecond(selectedLog.timestamp)}</p>
              <p><strong>用户：</strong>{selectedLog.username}</p>
              <p><strong>操作：</strong>{EVENT_TYPE_MAP[selectedLog.event_type] ?? selectedLog.event_type}</p>
              <p><strong>状态：</strong>{selectedLog.success ? '成功' : '失败'}</p>
              <p><strong>IP地址：</strong>{selectedLog.ip_address}</p>
              <p><strong>详细信息：</strong></p>
              <pre>{typeof selectedLog.details === 'string' ? selectedLog.details : JSON.stringify(selectedLog.details, null, 2)}</pre>
            </div>
          )}
        </Modal>
      </Card>
    </div>
  );
};

export default AuditLogs; 