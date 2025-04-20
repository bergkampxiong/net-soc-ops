import React, { useEffect, useState } from 'react';
import { Drawer, Form, Select, Button, Space, message } from 'antd';
import { CloudServerOutlined } from '@ant-design/icons';
import { deviceGroupApi } from '../../../api/device';
import { sshConfigApi } from '../../../api/rpa';
import type { DeviceGroup, DeviceMember } from '../../../types/device';
import type { SSHConfig } from '../../../types/rpa';

const { Option } = Select;

interface DeviceConnectPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: any;
  onSave: (data: any) => void;
}

export const PDDeviceConnectPanel: React.FC<DeviceConnectPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [sshConfigs, setSSHConfigs] = useState<SSHConfig[]>([]);
  const [deviceGroups, setDeviceGroups] = useState<DeviceGroup[]>([]);
  const [groupMembers, setGroupMembers] = useState<DeviceMember[]>([]);

  // 只在面板打开时加载数据
  useEffect(() => {
    if (visible) {
      loadInitialData();
    }
  }, [visible]);

  // 加载初始数据
  const loadInitialData = async () => {
    setLoading(true);
    try {
      // TODO: 替换为实际的API调用
      // const [sshConfigsData, deviceGroupsData] = await Promise.all([
      //   fetchSSHConfigs(),
      //   fetchDeviceGroups()
      // ]);
      // setSSHConfigs(sshConfigsData);
      // setDeviceGroups(deviceGroupsData);

      // 加载SSH配置列表
      const response = await sshConfigApi.getList();
      setSSHConfigs(response.data.data);

      // 加载设备分组列表
      const deviceGroupsResponse = await deviceGroupApi.getList();
      setDeviceGroups(deviceGroupsResponse.data.data);

      // 如果有初始数据，加载对应的设备列表
      if (initialData?.deviceGroupId) {
        // const members = await fetchGroupMembers(initialData.deviceGroupId);
        // setGroupMembers(members);
      }

      // 设置表单初始值
      form.setFieldsValue(initialData);
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理设备组选择
  const handleGroupChange = async (groupId: string) => {
    if (!groupId) {
      setGroupMembers([]);
      return;
    }

    setLoading(true);
    try {
      // TODO: 替换为实际的API调用
      // const members = await fetchGroupMembers(groupId);
      // setGroupMembers(members);
    } catch (error) {
      message.error('加载设备列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理保存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      onSave({
        ...values,
        isConfigured: true  // 标记为已配置
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
          <CloudServerOutlined />
          <span>设备连接配置</span>
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
          name="sshConfigId"
          label="SSH配置"
          rules={[{ required: true, message: '请选择SSH配置' }]}
        >
          <Select
            placeholder="请选择SSH配置"
            options={sshConfigs}
            loading={loading}
          />
        </Form.Item>

        <Form.Item
          name="deviceGroupId"
          label="设备分组"
          rules={[{ required: true, message: '请选择设备分组' }]}
        >
          <Select
            placeholder="请选择设备分组"
            options={deviceGroups}
            loading={loading}
            onChange={handleGroupChange}
          />
        </Form.Item>

        <Form.Item
          name="selectedDevices"
          label="目标设备"
          rules={[{ required: true, message: '请选择目标设备' }]}
        >
          <Select
            mode="multiple"
            placeholder="请选择目标设备"
            options={groupMembers}
            loading={loading}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 