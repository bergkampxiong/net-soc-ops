import React, { useEffect, useState } from 'react';
import { Form, Input, Button, Space, message } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import type { TaskNode } from '../../../types/automation';

interface TaskPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: TaskNode;
  onSave: (data: TaskNode) => void;
}

export const PDTaskPanel: React.FC<TaskPanelProps> = ({
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
        <span>任务节点配置</span>
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
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="请输入任务名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="任务描述"
          >
            <Input.TextArea rows={3} placeholder="请输入任务描述" />
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