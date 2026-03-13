import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, message, Select } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import request from '../../../utils/request';

/** 日常巡检节点保存数据结构 */
export interface DailyInspectionNodeData {
  checklistId?: number | string;
  reportTitle?: string;
  webhookUrl?: string;
  configured?: boolean;
  [key: string]: unknown;
}

interface PDStatusCheckPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: DailyInspectionNodeData;
  onSave: (data: DailyInspectionNodeData) => void;
}

interface ChecklistOption {
  id: number;
  name: string;
  item_count?: number;
}

export const PDStatusCheckPanel: React.FC<PDStatusCheckPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [checklists, setChecklists] = useState<ChecklistOption[]>([]);

  useEffect(() => {
    if (visible) {
      form.setFieldsValue({
        checklistId: initialData?.checklistId ?? undefined,
        reportTitle: initialData?.reportTitle ?? '',
        webhookUrl: initialData?.webhookUrl ?? '',
      });
    }
  }, [visible, initialData, form]);

  useEffect(() => {
    if (visible) {
      request
        .get<ChecklistOption[]>('inspection/checklists', { params: { skip: 0, limit: 500 } })
        .then((res) => {
          const data = res?.data ?? res;
          setChecklists(Array.isArray(data) ? data : []);
        })
        .catch(() => setChecklists([]));
    }
  }, [visible]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      onSave({
        checklistId: values.checklistId,
        reportTitle: values.reportTitle?.trim() ?? '',
        webhookUrl: values.webhookUrl?.trim() ?? '',
        configured: true,
      });
      onClose();
      message.success('配置已保存');
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return;
      message.error('请检查配置信息');
    }
  };

  return (
    <Drawer
      title={
        <Space>
          <CheckCircleOutlined />
          <span>日常巡检节点配置</span>
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
      <Form form={form} layout="vertical" disabled={loading}>
        <Form.Item
          name="checklistId"
          label="选择巡检清单"
          rules={[{ required: true, message: '请选择巡检清单' }]}
        >
          <Select
            placeholder="请选择已创建的巡检清单"
            showSearch
            optionFilterProp="label"
            options={checklists.map((c) => ({ value: c.id, label: `${c.name}${c.item_count != null ? ` (${c.item_count} 项)` : ''}` }))}
          />
        </Form.Item>

        <Form.Item
          name="reportTitle"
          label="报告标题"
          rules={[{ required: true, message: '请输入报告标题' }]}
          extra="将作为 Webhook 报告中的标题，便于区分任务或周期"
        >
          <Input placeholder="如：核心网络每日巡检" />
        </Form.Item>

        <Form.Item
          name="webhookUrl"
          label="Webhook 地址"
          rules={[{ required: true, message: '请输入 Webhook 地址' }]}
          extra="执行完成后将巡检结果报告 POST 到该地址"
        >
          <Input placeholder="https://your-webhook.example.com/inspection" />
        </Form.Item>
      </Form>
    </Drawer>
  );
};
