import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, Select, message } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';

export interface ScanTargetNodeOption {
  id: string;
  label?: string;
}

export interface PenetrationTestNodeData {
  targetSource?: 'targetNode' | 'inline';
  targetNodeId?: string;
  targetType?: string;
  targets?: string[];
  targetValue?: string;
  instruction?: string;
  scanMode?: string;
  presetId?: string;
  label?: string;
  configured?: boolean;
}

interface PDPenetrationTestPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: PenetrationTestNodeData;
  onSave: (data: PenetrationTestNodeData) => void;
  scanTargetNodes?: ScanTargetNodeOption[];
}

const SCAN_MODES = [
  { value: 'quick', label: 'quick（快速）' },
  { value: 'standard', label: 'standard（常规）' },
  { value: 'deep', label: 'deep（深度）' },
];

export const PDPenetrationTestPanel: React.FC<PDPenetrationTestPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
  scanTargetNodes = [],
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      form.setFieldsValue({
        targetSource: initialData?.targetSource ?? 'inline',
        targetNodeId: initialData?.targetNodeId,
        targetType: initialData?.targetType ?? 'web_url',
        targetValue: Array.isArray(initialData?.targets)
          ? initialData.targets.join('\n')
          : initialData?.targetValue || '',
        instruction: initialData?.instruction,
        scanMode: initialData?.scanMode ?? 'deep',
        presetId: initialData?.presetId,
      });
    }
  }, [visible, initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const targetSource = values.targetSource as 'targetNode' | 'inline';
      let targets: string[] = [];
      let targetNodeId: string | undefined;
      if (targetSource === 'targetNode' && values.targetNodeId) {
        targetNodeId = values.targetNodeId;
      } else {
        const targetValue = (values.targetValue || '').trim();
        targets = targetValue ? targetValue.split(/\n/).map((s: string) => s.trim()).filter(Boolean) : [];
        if (!targets.length) {
          message.error('请至少填写一个目标，或选择从目标节点获取');
          return;
        }
      }
      onSave({
        targetSource,
        targetNodeId,
        targetType: values.targetType,
        targets: targets.length ? targets : undefined,
        targetValue: targets[0],
        instruction: values.instruction || undefined,
        scanMode: values.scanMode ?? 'deep',
        presetId: values.presetId,
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
          <SafetyCertificateOutlined />
          <span>渗透测试节点配置</span>
        </Space>
      }
      width={440}
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
        <Form.Item name="targetSource" label="目标来源" rules={[{ required: true }]}>
          <Select
            options={[
              { value: 'targetNode', label: '从目标节点获取' },
              { value: 'inline', label: '本节点内填写' },
            ]}
          />
        </Form.Item>
        <Form.Item
          noStyle
          shouldUpdate={(prev, curr) => prev.targetSource !== curr.targetSource}
        >
          {({ getFieldValue }) =>
            getFieldValue('targetSource') === 'targetNode' ? (
              <Form.Item name="targetNodeId" label="选择扫描目标节点" rules={[{ required: true }]}>
                <Select
                  placeholder="选择流程中的扫描目标节点"
                  options={scanTargetNodes.map((n) => ({
                    value: n.id,
                    label: n.label || `扫描目标 (${n.id})`,
                  }))}
                />
              </Form.Item>
            ) : (
              <>
                <Form.Item name="targetType" label="目标类型">
                  <Select
                    options={[
                      { value: 'web_url', label: 'Web URL' },
                      { value: 'git_url', label: 'Git URL' },
                      { value: 'local_path', label: '本地路径' },
                      { value: 'domain_ip', label: '域名或 IP' },
                    ]}
                  />
                </Form.Item>
                <Form.Item name="targetValue" label="目标值（多行）">
                  <Input.TextArea rows={3} placeholder="每行一个目标" />
                </Form.Item>
              </>
            )
          }
        </Form.Item>
        <Form.Item name="scanMode" label="扫描模式" rules={[{ required: true }]}>
          <Select options={SCAN_MODES} />
        </Form.Item>
        <Form.Item name="instruction" label="自定义指令（可选）">
          <Input.TextArea rows={2} placeholder="如：仅测认证与越权" />
        </Form.Item>
        <Form.Item name="presetId" label="扫描预设（可选）">
          <Select allowClear placeholder="选择预设" options={[]} />
        </Form.Item>
      </Form>
    </Drawer>
  );
};
