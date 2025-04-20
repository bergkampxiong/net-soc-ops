import React, { useState, useEffect, Suspense } from 'react';
import { Card, Table, Button, Space, message, Popconfirm, Tabs, Spin } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CodeOutlined } from '@ant-design/icons';
import SSHConfigModal from './SSHConfigModal';
import SSHCodeViewer from './SSHCodeViewer';
import { getSSHConfigs, deleteSSHConfig, SSHConfig } from '../../../../services/sshConfig';

const { TabPane } = Tabs;

// 懒加载PoolMonitor组件
const PoolMonitor = React.lazy(() => import('./PoolMonitor'));

const DeviceConnections: React.FC = () => {
  const [sshConfigs, setSSHConfigs] = useState<SSHConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SSHConfig | undefined>();
  const [codeViewerVisible, setCodeViewerVisible] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<SSHConfig | undefined>();

  const fetchSSHConfigs = async () => {
    setLoading(true);
    try {
      const data = await getSSHConfigs();
      setSSHConfigs(data);
    } catch (error) {
      message.error('获取SSH配置列表失败');
      console.error('获取SSH配置列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSSHConfigs();
  }, []);

  const handleAdd = () => {
    setEditingConfig(undefined);
    setModalVisible(true);
  };

  const handleEdit = (record: SSHConfig) => {
    setEditingConfig(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteSSHConfig(id);
      message.success('删除SSH配置成功');
      fetchSSHConfigs();
    } catch (error) {
      message.error('删除SSH配置失败');
      console.error('删除SSH配置失败:', error);
    }
  };

  const handleViewCode = (record: SSHConfig) => {
    setSelectedConfig(record);
    setCodeViewerVisible(true);
  };

  const columns = [
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
      render: (_: any, record: SSHConfig) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            icon={<CodeOutlined />}
            onClick={() => handleViewCode(record)}
          >
            查看代码
          </Button>
          <Popconfirm
            title="确定要删除这个SSH配置吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Tabs defaultActiveKey="1">
      <TabPane tab="SSH连接配置" key="1">
        <Card
          title="SSH连接配置"
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              新增SSH配置
            </Button>
          }
        >
          <Table
            columns={columns}
            dataSource={sshConfigs}
            rowKey="id"
            loading={loading}
          />

          <SSHConfigModal
            visible={modalVisible}
            onCancel={() => setModalVisible(false)}
            onSuccess={() => {
              setModalVisible(false);
              fetchSSHConfigs();
            }}
            initialValues={editingConfig}
          />

          {selectedConfig && (
            <SSHCodeViewer
              visible={codeViewerVisible}
              onClose={() => setCodeViewerVisible(false)}
              config={selectedConfig}
            />
          )}
        </Card>
      </TabPane>
      <TabPane tab="连接池监控" key="2">
        <Suspense fallback={<div style={{ textAlign: 'center', padding: '20px' }}><Spin /></div>}>
          <PoolMonitor />
        </Suspense>
      </TabPane>
      <TabPane tab="状态刷新" key="3">
        <Card title="状态刷新">
          <div>
            <p><strong>最大连接数:</strong> 50</p>
            <p><strong>最小空闲连接数:</strong> 1</p>
            <p><strong>空闲超时时间:</strong> 300秒</p>
            <p><strong>连接超时时间:</strong> 30秒</p>
          </div>
        </Card>
      </TabPane>
    </Tabs>
  );
};

export default DeviceConnections; 