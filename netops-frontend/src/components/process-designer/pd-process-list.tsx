import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

interface ProcessItem {
  id: string;
  name: string;
  description: string;
  createTime: string;
  updateTime: string;
}

interface PDProcessListProps {
  onSelectProcess: (processId: string) => void;
  onCreateProcess: (processId: string) => void;
  selectedProcessId?: string | null;
}

const PDProcessList: React.FC<PDProcessListProps> = ({ 
  onSelectProcess, 
  onCreateProcess,
  selectedProcessId 
}) => {
  const [processes, setProcesses] = useState<ProcessItem[]>([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [editingProcess, setEditingProcess] = useState<ProcessItem | null>(null);

  // 加载流程列表
  const loadProcesses = async () => {
    try {
      // TODO: 替换为实际的API调用
      const mockProcesses: ProcessItem[] = [
        {
          id: '1',
          name: '设备配置流程',
          description: '用于自动化设备配置的流程',
          createTime: '2024-03-20 10:00:00',
          updateTime: '2024-03-20 10:00:00'
        },
        {
          id: '2',
          name: '网络巡检流程',
          description: '用于自动化网络巡检的流程',
          createTime: '2024-03-20 11:00:00',
          updateTime: '2024-03-20 11:00:00'
        }
      ];
      setProcesses(mockProcesses);
    } catch (error) {
      message.error('加载流程列表失败');
    }
  };

  useEffect(() => {
    loadProcesses();
  }, []);

  // 表格列定义
  const columns: ColumnsType<ProcessItem> = [
    {
      title: '流程名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
    },
    {
      title: '更新时间',
      dataIndex: 'updateTime',
      key: 'updateTime',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(record);
            }}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(record);
            }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 处理创建/编辑流程
  const handleCreate = () => {
    setEditingProcess(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleEdit = (process: ProcessItem) => {
    setEditingProcess(process);
    form.setFieldsValue(process);
    setIsModalVisible(true);
    // 编辑时直接跳转到流程设计器
    onSelectProcess(process.id);
  };

  // 处理删除流程
  const handleDelete = (process: ProcessItem) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除流程"${process.name}"吗？`,
      onOk: async () => {
        try {
          // TODO: 替换为实际的API调用
          // 如果当前正在编辑这个流程，需要清空选中的流程ID
          if (process.id === selectedProcessId) {
            onSelectProcess('');
          }
          message.success('删除成功');
          loadProcesses();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  // 处理表单提交
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingProcess) {
        // TODO: 替换为实际的API调用
        message.success('更新成功');
        onSelectProcess(editingProcess.id);
      } else {
        // TODO: 替换为实际的API调用
        const newProcessId = `process-${Date.now()}`;
        onCreateProcess(newProcessId);
        message.success('创建成功');
      }
      setIsModalVisible(false);
      loadProcesses();
    } catch (error) {
      message.error('操作失败');
    }
  };

  return (
    <div className="pd-process-list">
      <div className="pd-process-list-header">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          新建流程
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={processes}
        rowKey="id"
        onRow={(record) => ({
          onClick: () => onSelectProcess(record.id),
        })}
      />
      <Modal
        title={editingProcess ? '编辑流程' : '新建流程'}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => setIsModalVisible(false)}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="name"
            label="流程名称"
            rules={[{ required: true, message: '请输入流程名称' }]}
          >
            <Input placeholder="请输入流程名称" />
          </Form.Item>
          <Form.Item
            name="description"
            label="流程描述"
          >
            <Input.TextArea placeholder="请输入流程描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PDProcessList;