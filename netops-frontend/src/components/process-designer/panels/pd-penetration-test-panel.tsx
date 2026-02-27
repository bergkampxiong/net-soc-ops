import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, Select, message, Alert, Typography } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';

export interface ScanTargetNodeOption {
  id: string;
  label?: string;
  targetType?: string;
  /** 仅静态代码审计时为 true */
  staticOnly?: boolean;
}

export interface PenetrationTestNodeData {
  /** 渗透测试目标只能从扫描目标节点获取 */
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

function getTestTypeLabel(targetType?: string, staticOnly?: boolean): string {
  if (staticOnly) return '仅静态（代码审计）';
  if (targetType === 'web_url') return '动态（黑盒）';
  if (targetType === 'git_url') return '白盒（Git）';
  if (targetType === 'local_path') return '白盒（本地路径）';
  return '—';
}

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
        targetNodeId: initialData?.targetNodeId,
        instruction: initialData?.instruction,
        scanMode: initialData?.scanMode ?? 'deep',
      });
    }
  }, [visible, initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const targetNodeId = values.targetNodeId as string;
      if (!targetNodeId) {
        message.error('请选择扫描目标节点');
        return;
      }
      onSave({
        targetSource: 'targetNode',
        targetNodeId,
        instruction: values.instruction || undefined,
        scanMode: values.scanMode ?? 'deep',
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
      <Typography.Paragraph type="secondary" style={{ marginBottom: 16, fontSize: 12 }}>
        <strong>扫描模式说明</strong>：quick 快速检查（分钟级，CI/PR 冒烟）；standard 常规评估（约 30 分钟～1 小时）；deep 深度渗透（约 1～4 小时，全面审计）。
      </Typography.Paragraph>
      <Form form={form} layout="vertical">
        {scanTargetNodes.length === 0 ? (
          <Alert
            type="warning"
            showIcon
            message="请先在流程中添加「扫描目标」节点"
            description="渗透测试的目标只能从流程中的扫描目标节点获取，不能在本节点内填写。请添加扫描目标节点并配置目标后再选择。"
            style={{ marginBottom: 16 }}
          />
        ) : null}
        <Form.Item
          name="targetNodeId"
          label="选择扫描目标节点"
          rules={[{ required: true, message: '请选择扫描目标节点' }]}
          extra="渗透测试目标只能从扫描目标节点获取，将使用所选节点中配置的目标执行扫描（单目标）。"
        >
          <Select
            placeholder="选择流程中的扫描目标节点"
            disabled={scanTargetNodes.length === 0}
            options={scanTargetNodes.map((n) => ({
              value: n.id,
              label: n.label || `扫描目标 (${n.id})`,
            }))}
          />
        </Form.Item>
        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.targetNodeId !== curr.targetNodeId}>
          {({ getFieldValue }) => {
            const id = getFieldValue('targetNodeId');
            const node = id ? scanTargetNodes.find((n) => n.id === id) : null;
            const testTypeLabel = node ? getTestTypeLabel(node.targetType, node.staticOnly) : null;
            if (!testTypeLabel || testTypeLabel === '—') return null;
            return (
              <Typography.Paragraph type="secondary" style={{ marginTop: -8, marginBottom: 16, fontSize: 12 }}>
                当前目标测试类型：<strong>{testTypeLabel}</strong>
              </Typography.Paragraph>
            );
          }}
        </Form.Item>
        <Form.Item
          name="scanMode"
          label="扫描模式"
          rules={[{ required: true }]}
        >
          <Select options={SCAN_MODES} />
        </Form.Item>
        <Form.Item name="instruction" label="自定义指令（可选）">
          <Input.TextArea rows={2} placeholder="如：仅测认证与越权" />
        </Form.Item>
      </Form>
    </Drawer>
  );
};
