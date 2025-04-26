import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, message } from 'antd';
import { CodeOutlined } from '@ant-design/icons';
import type { CommandExecuteNode } from '../../../types/automation';

interface CommandExecutePanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: CommandExecuteNode;
  onSave: (data: CommandExecuteNode) => void;
}

export const PDCommandExecutePanel: React.FC<CommandExecutePanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      form.setFieldsValue(initialData);
    }
  }, [visible, initialData]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      onSave({
        ...values,
        isConfigured: true
      });
      onClose();
      message.success('配置已保存');
    } catch (error) {
      message.error('请检查配置信息');
    }
  };

  return (
    <Drawer
      title={
        <Space>
          <CodeOutlined />
          <span>命令执行节点配置</span>
        </Space>
      }
      width={400}
      open={visible}
      onClose={onClose}
      extra={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSave} loading={loading}>
            保存
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        disabled={loading}
      >
        <Form.Item
          name="name"
          label="命令名称"
          rules={[{ required: true, message: '请输入命令名称' }]}
        >
          <Input placeholder="请输入命令名称" />
        </Form.Item>

        <Form.Item
          name="description"
          label="命令描述"
        >
          <Input.TextArea rows={3} placeholder="请输入命令描述" />
        </Form.Item>

        <Form.Item
          name="command"
          label="执行命令"
          rules={[{ required: true, message: '请输入执行命令' }]}
        >
          <Input.TextArea rows={4} placeholder="请输入执行命令" />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 