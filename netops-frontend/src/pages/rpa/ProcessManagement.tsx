import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Modal, Form, Input, message, Tag, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, HistoryOutlined } from '@ant-design/icons';
import { 
  ProcessDefinition, 
  getProcessDefinitions, 
  createProcessDefinition, 
  updateProcessDefinition, 
  deleteProcessDefinition,
  publishProcessDefinition,
  disableProcessDefinition,
  getProcessVersions,
  rollbackProcessVersion
} from '../../api/process-management';
import { useNavigate } from 'react-router-dom';

const { TextArea } = Input;

const ProcessManagement: React.FC = () => {
  const [processes, setProcesses] = useState<ProcessDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [versionsVisible, setVersionsVisible] = useState(false);
  const [currentProcessId, setCurrentProcessId] = useState<string | null>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const navigate = useNavigate();

  // 获取流程列表
  const fetchProcesses = async () => {
    setLoading(true);
    try {
      const response = await getProcessDefinitions();
      setProcesses(response.data);
    } catch (error) {
      message.error('获取流程列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProcesses();
  }, []);

  // 处理表单提交
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingId) {
        await updateProcessDefinition(editingId, values);
        message.success('更新成功');
      } else {
        await createProcessDefinition(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      form.resetFields();
      fetchProcesses();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 处理删除
  const handleDelete = async (id: string) => {
    try {
      await deleteProcessDefinition(id);
      message.success('删除成功');
      fetchProcesses();
    } catch (error) {
      message.error('删除失败');
    }
  };

  // 处理发布
  const handlePublish = async (id: string) => {
    try {
      await publishProcessDefinition(id);
      message.success('发布成功');
      fetchProcesses();
    } catch (error) {
      message.error('发布失败');
    }
  };

  // 处理禁用
  const handleDisable = async (id: string) => {
    try {
      await disableProcessDefinition(id);
      message.success('禁用成功');
      fetchProcesses();
    } catch (error) {
      message.error('禁用失败');
    }
  };

  // 处理版本查看
  const handleViewVersions = async (id: string) => {
    setCurrentProcessId(id);
    try {
      const response = await getProcessVersions(id);
      setVersions(response.data);
      setVersionsVisible(true);
    } catch (error) {
      message.error('获取版本历史失败');
    }
  };

  // 处理版本回滚
  const handleRollback = async (version: number) => {
    if (!currentProcessId) return;
    try {
      await rollbackProcessVersion(currentProcessId, version);
      message.success('回滚成功');
      setVersionsVisible(false);
      fetchProcesses();
    } catch (error) {
      message.error('回滚失败');
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const color = status === 'published' ? 'success' : status === 'disabled' ? 'error' : 'default';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ProcessDefinition) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingId(record.id);
              form.setFieldsValue(record);
              setModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Button
            type="link"
            icon={<HistoryOutlined />}
            onClick={() => handleViewVersions(record.id)}
          >
            版本
          </Button>
          {record.status === 'draft' && (
            <Button
              type="link"
              onClick={() => handlePublish(record.id)}
            >
              发布
            </Button>
          )}
          {record.status === 'published' && (
            <Button
              type="link"
              onClick={() => handleDisable(record.id)}
            >
              禁用
            </Button>
          )}
          <Popconfirm
            title="确定要删除吗？"
            onConfirm={() => handleDelete(record.id)}
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
    <div className="process-management">
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingId(null);
              form.resetFields();
              setModalVisible(true);
            }}
          >
            新建流程
          </Button>
        </div>
        <Table
          columns={columns}
          dataSource={processes}
          rowKey="id"
          loading={loading}
        />
      </Card>

      {/* 编辑/创建模态框 */}
      <Modal
        title={editingId ? '编辑流程' : '新建流程'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 版本历史模态框 */}
      <Modal
        title="版本历史"
        open={versionsVisible}
        onCancel={() => setVersionsVisible(false)}
        footer={null}
      >
        <Table
          columns={[
            { title: '版本', dataIndex: 'version', key: 'version' },
            { title: '创建人', dataIndex: 'created_by', key: 'created_by' },
            { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
            {
              title: '操作',
              key: 'action',
              render: (_: any, record: any) => (
                <Button
                  type="link"
                  onClick={() => handleRollback(record.version)}
                >
                  回滚
                </Button>
              ),
            },
          ]}
          dataSource={versions}
          rowKey="id"
        />
      </Modal>
    </div>
  );
};

export default ProcessManagement; 