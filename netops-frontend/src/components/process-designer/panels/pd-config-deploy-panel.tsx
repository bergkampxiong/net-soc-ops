import React, { useEffect, useState } from 'react';
import { Form, Input, Button, Space, message } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
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

  if (!visible) return null;

  return (
    <div className="pd-config-panel">
      <div className="pd-config-panel-header">
        <span>配置下发节点配置</span>
        <Button type="text" icon={<CloseOutlined />} onClick={onClose} />
      </div>
      <div className="pd-config-panel-content">
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
        </Form>
      </div>
      <div className="pd-config-panel-footer">
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSave} loading={loading}>
            保存
          </Button>
        </Space>
      </div>
    </div>
  );
}; 