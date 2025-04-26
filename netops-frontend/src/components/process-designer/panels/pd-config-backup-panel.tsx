import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, message } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import type { ConfigBackupNode } from '../../../types/automation';

interface ConfigBackupPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: ConfigBackupNode;
  onSave: (data: ConfigBackupNode) => void;
}

export const PDConfigBackupPanel: React.FC<ConfigBackupPanelProps> = ({
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
          <SaveOutlined />
          <span>配置备份节点配置</span>
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
          label="备份名称"
          rules={[{ required: true, message: '请输入备份名称' }]}
        >
          <Input placeholder="请输入备份名称" />
        </Form.Item>

        <Form.Item
          name="description"
          label="备份描述"
        >
          <Input.TextArea rows={3} placeholder="请输入备份描述" />
        </Form.Item>

        <Form.Item
          name="backupPath"
          label="备份路径"
          rules={[{ required: true, message: '请输入备份路径' }]}
        >
          <Input placeholder="请输入备份路径" />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 