import React, { useState, useEffect } from 'react';
import { 
  Card, Tabs, Table, Button, Space, Modal, Form, Input, 
  message, Popconfirm, Typography, Row, Col 
} from 'antd';
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, 
  ReloadOutlined, DatabaseOutlined 
} from '@ant-design/icons';
import request from '../../utils/request';
import './ModelManage.css';

const { TabPane } = Tabs;
const { Title, Text } = Typography;

// 模型类型定义
interface ModelItem {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

// 模型类型映射
const modelTypes = [
  { key: 'device-types', name: '设备类型', icon: <DatabaseOutlined /> },
  { key: 'vendors', name: '厂商', icon: <DatabaseOutlined /> },
  { key: 'locations', name: '位置', icon: <DatabaseOutlined /> },
  { key: 'departments', name: '部门', icon: <DatabaseOutlined /> },
  { key: 'asset-statuses', name: '资产状态', icon: <DatabaseOutlined /> },
  { key: 'system-types', name: '系统类型', icon: <DatabaseOutlined /> },
];

/**
 * CMDB模型管理组件
 */
const CMDBModelManage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('device-types');
  const [modelData, setModelData] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [modalTitle, setModalTitle] = useState<string>('');
  const [editingItem, setEditingItem] = useState<ModelItem | null>(null);
  const [form] = Form.useForm();

  // 获取模型数据
  const fetchModelData = async (modelType: string) => {
    setLoading(true);
    try {
      const response = await request.get(`/cmdb/${modelType}`);
      setModelData(response.data);
    } catch (error) {
      console.error(`获取${getModelTypeName(modelType)}数据失败:`, error);
      message.error(`获取${getModelTypeName(modelType)}数据失败`);
    } finally {
      setLoading(false);
    }
  };

  // 获取模型类型名称
  const getModelTypeName = (modelType: string): string => {
    const model = modelTypes.find(m => m.key === modelType);
    return model ? model.name : '未知模型';
  };

  // 切换标签页
  const handleTabChange = (key: string) => {
    setActiveTab(key);
    fetchModelData(key);
  };

  // 组件挂载时获取数据
  useEffect(() => {
    fetchModelData(activeTab);
  }, [activeTab]);

  // 打开添加模态框
  const showAddModal = () => {
    setModalTitle(`添加${getModelTypeName(activeTab)}`);
    setEditingItem(null);
    form.resetFields();
    setModalVisible(true);
  };

  // 打开编辑模态框
  const showEditModal = (item: ModelItem) => {
    setModalTitle(`编辑${getModelTypeName(activeTab)}`);
    setEditingItem(item);
    form.setFieldsValue({
      name: item.name,
      description: item.description || '',
    });
    setModalVisible(true);
  };

  // 处理表单提交
  const handleFormSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingItem) {
        // 更新现有项
        await handleEdit(values);
      } else {
        // 创建新项
        await handleAdd(values);
      }
    } catch (error) {
      console.error('表单提交失败:', error);
      message.error('操作失败，请检查输入');
    }
  };

  // 处理编辑
  const handleEdit = async (values: any) => {
    if (!editingItem) {
      message.error('编辑项不存在');
      return;
    }
    
    try {
      await request.put(`/cmdb/${activeTab}/${editingItem.id}`, values);
      message.success('更新成功');
      setEditingItem(null);
      fetchModelData(activeTab);
    } catch (error) {
      message.error('更新失败');
    }
  };

  // 处理添加
  const handleAdd = async (values: any) => {
    try {
      await request.post(`/cmdb/${activeTab}`, values);
      message.success('添加成功');
      setModalVisible(false);
      fetchModelData(activeTab);
    } catch (error) {
      message.error('添加失败');
    }
  };

  // 处理删除
  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/cmdb/${activeTab}/${id}`);
      message.success('删除成功');
      fetchModelData(activeTab);
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败，该项可能正在被使用');
    }
  };

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text: string | null) => text || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ModelItem) => (
        <Space size="small">
          <Button 
            type="text" 
            icon={<EditOutlined />} 
            onClick={() => showEditModal(record)}
          />
          <Popconfirm
            title={`确定要删除此${getModelTypeName(activeTab)}吗?`}
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="cmdb-model-manage-page">
      <Card title="CMDB模型管理" className="cmdb-model-card">
        <Tabs activeKey={activeTab} onChange={handleTabChange}>
          {modelTypes.map(model => (
            <TabPane 
              tab={
                <span>
                  {model.icon}
                  {model.name}
                </span>
              } 
              key={model.key}
            >
              <Row justify="space-between" style={{ marginBottom: 16 }}>
                <Col>
                  <Title level={5}>{model.name}管理</Title>
                  <Text type="secondary">管理CMDB中的{model.name}基础数据</Text>
                </Col>
                <Col>
                  <Space>
                    <Button 
                      icon={<ReloadOutlined />} 
                      onClick={() => fetchModelData(activeTab)}
                    >
                      刷新
                    </Button>
                    <Button 
                      type="primary" 
                      icon={<PlusOutlined />} 
                      onClick={showAddModal}
                    >
                      添加{model.name}
                    </Button>
                  </Space>
                </Col>
              </Row>
              
              <Table
                columns={columns}
                dataSource={modelData}
                rowKey="id"
                loading={loading}
                pagination={{
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条记录`,
                }}
              />
            </TabPane>
          ))}
        </Tabs>
      </Card>

      {/* 添加/编辑模态框 */}
      <Modal
        title={modalTitle}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleFormSubmit}
        okText={editingItem ? '更新' : '添加'}
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="请输入名称" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={4} placeholder="请输入描述信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CMDBModelManage; 