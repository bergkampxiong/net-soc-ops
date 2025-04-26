import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, message } from 'antd';
import { DeploymentUnitOutlined } from '@ant-design/icons';
import type { ConfigDeployNode } from '../../../types/automation';

interface ConfigDeployPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: ConfigDeployNode;
  onSave: (data: ConfigDeployNode) => void;
}

export const PDConfigDeployPanel: React.FC<ConfigDeployPanelProps> = ({
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
          <DeploymentUnitOutlined />
          <span>配置下发节点配置</span>
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
          label="配置名称"
          rules={[{ required: true, message: '请输入配置名称' }]}
        >
          <Input placeholder="请输入配置名称" />
        </Form.Item>

        <Form.Item
          name="description"
          label="配置描述"
        >
          <Input.TextArea rows={3} placeholder="请输入配置描述" />
        </Form.Item>

        <Form.Item
          name="configContent"
          label="配置内容"
          rules={[{ required: true, message: '请输入配置内容' }]}
        >
          <Input.TextArea rows={6} placeholder="请输入配置内容" />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 