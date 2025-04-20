import React, { useState, useRef, useEffect } from 'react';
import { Card, Typography, Tabs, Form, Input, Select, Button, Table, Switch, InputNumber, Space, message, Row, Col, Badge, Tooltip, Statistic, Modal, Popconfirm } from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  SaveOutlined,
  SyncOutlined,
  ApiOutlined,
  SettingOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import type { TabsProps } from 'antd';
import { getSSHConfigs, deleteSSHConfig, SSHConfig, getDeviceTypes, createSSHConfig, updateSSHConfig } from '../../services/sshConfig';
import SSHConfigModal from './atomic-components/device-connections/SSHConfigModal';
import PoolMonitor from './atomic-components/device-connections/PoolMonitor';
import SSHCodeViewer from './atomic-components/device-connections/SSHCodeViewer';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;
const { TextArea } = Input;

// API类型选项
const apiTypes = [
  { label: 'REST API', value: 'REST' },
  { label: 'NETCONF', value: 'NETCONF' },
  { label: 'YANG', value: 'YANG' },
  { label: 'gRPC', value: 'gRPC' },
];

// 认证类型选项
const authTypes = [
  { label: 'Basic Auth', value: 'Basic' },
  { label: 'Token', value: 'Token' },
  { label: 'OAuth', value: 'OAuth' },
];

const DeviceConnections: React.FC = () => {
  // 状态管理
  const [activeTab, setActiveTab] = useState('ssh');
  const [sshConfigs, setSSHConfigs] = useState<SSHConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [sshModalVisible, setSSHModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<any>(null);
  const [codeViewerVisible, setCodeViewerVisible] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<SSHConfig | null>(null);
  
  // 使用 ref 替代 findDOMNode
  const headersRef = useRef<HTMLTextAreaElement>(null);

  // 获取数据
  const fetchData = async () => {
    setLoading(true);
    try {
      const sshData = await getSSHConfigs();
      setSSHConfigs(sshData);
    } catch (error) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // 处理函数
  const handleAddSSH = () => {
    setEditingConfig(null);
    setSSHModalVisible(true);
  };

  const handleEditSSH = (record: SSHConfig) => {
    setEditingConfig(record);
    setSSHModalVisible(true);
  };

  const handleDeleteSSH = async (id: number) => {
    try {
      await deleteSSHConfig(id);
      message.success('删除SSH配置成功');
      fetchData();
    } catch (error) {
      message.error('删除SSH配置失败');
    }
  };

  // SSH配置表格列定义
  const sshColumns = [
    {
      title: 'SSH连接名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '设备类型',
      dataIndex: 'device_type',
      key: 'device_type',
    },
    {
      title: '超时时间(秒)',
      dataIndex: 'timeout',
      key: 'timeout',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: SSHConfig) => (
        <Space>
          <Button type="link" onClick={() => handleEditSSH(record)}>
            编辑
          </Button>
          <Button type="link" danger onClick={() => handleDeleteSSH(record.id)}>
            删除
          </Button>
          <Button 
            type="link" 
            onClick={() => {
              setSelectedConfig(record);
              setCodeViewerVisible(true);
            }}
          >
            查看代码
          </Button>
        </Space>
      ),
    },
  ];

  // 标签页配置
  const items: TabsProps['items'] = [
    {
      key: 'ssh',
      label: 'SSH连接配置',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddSSH}>
              新增SSH配置
            </Button>
          </Space>
          <Table columns={sshColumns} dataSource={sshConfigs} rowKey="id" loading={loading} />
          <SSHConfigModal
            visible={sshModalVisible}
            onCancel={() => setSSHModalVisible(false)}
            onSuccess={() => {
              setSSHModalVisible(false);
              fetchData();
            }}
            initialValues={editingConfig}
          />
        </div>
      ),
    },
    {
      key: 'pool',
      label: '连接池管理',
      children: (
        <div>
          <PoolMonitor />
        </div>
      ),
    },
  ];

  return (
    <div className="device-connections">
      <Card>
        <Title level={4}>设备连接组件</Title>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={items} />
      </Card>

      {selectedConfig && (
        <SSHCodeViewer
          visible={codeViewerVisible}
          onClose={() => setCodeViewerVisible(false)}
          config={selectedConfig}
        />
      )}
    </div>
  );
};

export default DeviceConnections; 