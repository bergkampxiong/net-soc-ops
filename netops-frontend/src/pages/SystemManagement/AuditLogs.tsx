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

const { RangePicker } = DatePicker;
const { Title } = Typography;
const { Option } = Select;

// 配置 dayjs 使用 UTC 和时区插件
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('Asia/Shanghai'); // 设置默认时区为 UTC+8

interface AuditLog {
  id: number;
  username: string;
  action: string;
  resource: string;
  status: string;
  ip_address: string;
  timestamp: string;
  details: string;
  success: boolean;
}

const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [eventType, setEventType] = useState<string>('');
  const [searchText, setSearchText] = useState('');
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params: any = {
        page: currentPage,
        pageSize: pageSize,
        eventType: eventType,
        searchText: searchText
      };

      if (dateRange) {
        params.startTime = dateRange[0].tz('Asia/Shanghai').format('YYYY-MM-DD HH:mm:ss');
        params.endTime = dateRange[1].tz('Asia/Shanghai').format('YYYY-MM-DD HH:mm:ss');
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
      params.startTime = dateRange[0].tz('Asia/Shanghai').format('YYYY-MM-DD HH:mm:ss');
      params.endTime = dateRange[1].tz('Asia/Shanghai').format('YYYY-MM-DD HH:mm:ss');
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

  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
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
      render: (event_type: string) => {
        // 根据事件类型返回对应的中文描述
        const eventTypeMap: { [key: string]: string } = {
          'login': '登录',
          'logout': '登出',
          'ldap_login': 'LDAP登录',
          'login_2fa_required': '需要2FA验证',
          'login_2fa_setup_required': '需要设置2FA',
          'account_locked': '账户锁定',
          'totp_setup': '设置2FA',
          'totp_verify': '验证2FA',
          'totp_enabled': '启用2FA',
          'create_user': '创建用户',
          'delete_user': '删除用户',
          'update_user': '更新用户',
          'update_role': '更新角色',
          'update_department': '更新部门',
          'toggle_user_status': '切换用户状态',
          'change_password': '修改密码',
          'reset_password': '重置密码',
          'toggle_2fa': '切换2FA状态'
        };
        return eventTypeMap[event_type] || event_type;
      }
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
      title: '详情',
      key: 'action',
      render: (_: any, record: AuditLog) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => showDetails(record)}
        >
          详情
        </Button>
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
            style={{ width: 200 }}
            placeholder="选择事件类型"
            value={eventType}
            onChange={setEventType}
            allowClear
          >
            <Option value="login">登录</Option>
            <Option value="logout">登出</Option>
            <Option value="create">创建</Option>
            <Option value="update">更新</Option>
            <Option value="delete">删除</Option>
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
        </Space>

        <Table
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
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
              <p><strong>时间：</strong>{selectedLog.timestamp}</p>
              <p><strong>用户：</strong>{selectedLog.username}</p>
              <p><strong>操作：</strong>{selectedLog.action}</p>
              <p><strong>资源：</strong>{selectedLog.resource}</p>
              <p><strong>状态：</strong>{selectedLog.success ? '成功' : '失败'}</p>
              <p><strong>IP地址：</strong>{selectedLog.ip_address}</p>
              <p><strong>详细信息：</strong></p>
              <pre>{JSON.stringify(selectedLog.details, null, 2)}</pre>
            </div>
          )}
        </Modal>
      </Card>
    </div>
  );
};

export default AuditLogs; 