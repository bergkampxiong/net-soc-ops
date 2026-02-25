import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, Select, message } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import type { ConfigBackupNode } from '../../../types/automation';

export interface DeviceConnectNodeOption {
  id: string;
  label?: string;
}

interface ConfigBackupPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: Partial<ConfigBackupNode>;
  onSave: (data: Partial<ConfigBackupNode>) => void;
  /** 流程中所有设备连接节点，用于「设备来源」下拉 */
  deviceConnectNodes?: DeviceConnectNodeOption[];
}

export const PDConfigBackupPanel: React.FC<ConfigBackupPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
  deviceConnectNodes = [],
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      form.setFieldsValue({
        useDeviceFromNodeId: initialData?.useDeviceFromNodeId,
        remark: initialData?.remark,
        backupCommand: initialData?.backupCommand,
      });
    }
  }, [visible, initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      onSave({
        useDeviceFromNodeId: values.useDeviceFromNodeId,
        remark: values.remark,
        backupCommand: values.backupCommand || undefined,
        isConfigured: true,
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
      <Form form={form} layout="vertical" disabled={loading}>
        <Form.Item
          name="useDeviceFromNodeId"
          label="设备来源"
          rules={[{ required: true, message: '请选择要备份的设备来源' }]}
        >
          <Select
            placeholder="使用流程中哪个设备连接节点的设备"
            options={deviceConnectNodes.map((n) => ({
              value: n.id,
              label: n.label || `设备连接 (${n.id})`,
            }))}
          />
        </Form.Item>

        <Form.Item name="remark" label="备注（写入配置管理库时显示）">
          <Input placeholder="如：日常备份、变更前快照" />
        </Form.Item>

        <Form.Item
          name="backupCommand"
          label="备份命令（可选覆盖）"
          extra="留空则按设备类型自动选择命令（如 show running-config / display current-configuration）"
        >
          <Input placeholder="如：show running-config" />
        </Form.Item>
      </Form>
    </Drawer>
  );
};
