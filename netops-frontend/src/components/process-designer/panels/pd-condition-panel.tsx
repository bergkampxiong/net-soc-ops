import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, message } from 'antd';
import { BranchesOutlined } from '@ant-design/icons';
import type { ConditionNode } from '../../../types/automation';

interface ConditionPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: ConditionNode;
  onSave: (data: ConditionNode) => void;
}

export const PDConditionPanel: React.FC<ConditionPanelProps> = ({
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
          <BranchesOutlined />
          <span>条件节点配置</span>
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
          label="条件名称"
          rules={[{ required: true, message: '请输入条件名称' }]}
        >
          <Input placeholder="请输入条件名称" />
        </Form.Item>

        <Form.Item
          name="description"
          label="条件描述"
        >
          <Input.TextArea rows={3} placeholder="请输入条件描述" />
        </Form.Item>

        <Form.Item
          name="condition"
          label="条件表达式"
          rules={[{ required: true, message: '请输入条件表达式' }]}
        >
          <Input.TextArea rows={4} placeholder="请输入条件表达式" />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 