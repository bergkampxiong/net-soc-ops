import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, Select, message } from 'antd';
import { AimOutlined } from '@ant-design/icons';

export interface ScanTargetNodeData {
  targetType?: string;
  targets?: string[];
  targetValue?: string;
  useBackupOutput?: boolean;
  label?: string;
  configured?: boolean;
}

interface PDScanTargetPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: ScanTargetNodeData;
  onSave: (data: ScanTargetNodeData) => void;
}

const TARGET_TYPES = [
  { value: 'web_url', label: 'Web 应用 URL' },
  { value: 'git_url', label: 'Git 仓库 URL' },
  { value: 'local_path', label: '本地路径' },
  { value: 'domain_ip', label: '域名或 IP' },
];

export const PDScanTargetPanel: React.FC<PDScanTargetPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      const targets = initialData?.targets ?? (initialData?.targetValue ? [initialData.targetValue] : []);
      form.setFieldsValue({
        targetType: initialData?.targetType ?? 'web_url',
        targetValue: targets.length ? targets.join('\n') : '',
        useBackupOutput: initialData?.useBackupOutput ?? false,
      });
    }
  }, [visible, initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const targetValue = (values.targetValue || '').trim();
      const targets = targetValue ? targetValue.split(/\n/).map((s: string) => s.trim()).filter(Boolean) : [];
      if (!targets.length) {
        message.error('请至少填写一个目标');
        return;
      }
      onSave({
        targetType: values.targetType,
        targets,
        targetValue: targets[0],
        useBackupOutput: values.useBackupOutput ?? false,
        configured: true,
      });
      onClose();
      message.success('配置已保存');
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error('请检查配置信息');
    }
  };

  return (
    <Drawer
      title={
        <Space>
          <AimOutlined />
          <span>扫描目标节点配置</span>
        </Space>
      }
      width={420}
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
      <Form form={form} layout="vertical">
        <Form.Item name="targetType" label="目标类型" rules={[{ required: true }]}>
          <Select options={TARGET_TYPES} placeholder="选择目标类型" />
        </Form.Item>
        <Form.Item
          name="targetValue"
          label="目标值（多个目标每行一个）"
          rules={[{ required: true, message: '请填写至少一个目标 URL 或路径' }]}
        >
          <Input.TextArea rows={4} placeholder="如 https://example.com 或 ./app" />
        </Form.Item>
        <Form.Item name="useBackupOutput" label="使用本流程配置备份输出">
          <Select
            options={[
              { value: false, label: '否' },
              { value: true, label: '是' },
            ]}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
};
