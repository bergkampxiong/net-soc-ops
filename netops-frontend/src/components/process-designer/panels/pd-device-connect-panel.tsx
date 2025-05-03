import React, { useEffect, useState } from 'react';
import { Drawer, Form, Select, Button, Space, message, Radio } from 'antd';
import { CloudServerOutlined } from '@ant-design/icons';
import { deviceGroupApi } from '../../../api/device';
import { getSSHConfigs } from '../../../services/sshConfig';
import type { DeviceGroup } from '../../../types/device';
import type { SSHConfig } from '../../../services/sshConfig';
import request from '../../../utils/request';

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
  const [ipAddresses, setIpAddresses] = useState<string[]>([]);

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
      // 加载SSH配置列表
      const sshConfigsData = await getSSHConfigs();
      setSSHConfigs(sshConfigsData);

      // 加载设备分组列表
      const deviceGroupsResponse = await request.get('/device/category/groups');
      setDeviceGroups(deviceGroupsResponse.data);

      // 如果有初始数据，加载对应的IP地址列表
      if (initialData?.deviceGroupId) {
        const ipAddressesResponse = await request.get(`/api/device/category/groups/${initialData.deviceGroupId}/members`);
        setIpAddresses(ipAddressesResponse.data.map((member: any) => member.ip_address));
      }

      // 设置表单初始值
      form.setFieldsValue({
        ...initialData,
        // 默认选择网络设备连接池
        poolType: initialData?.poolType || 'device'
      });
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理设备组选择
  const handleGroupChange = async (groupId: string) => {
    if (!groupId) {
      setIpAddresses([]);
      return;
    }

    setLoading(true);
    try {
      const ipAddressesResponse = await request.get(`/api/device/category/groups/${groupId}/members`);
      setIpAddresses(ipAddressesResponse.data.map((member: any) => member.ip_address));
    } catch (error) {
      message.error('加载IP地址列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理保存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      // 获取选中的SSH配置的完整信息
      const selectedSSHConfig = sshConfigs.find(config => config.id === values.sshConfigId);
      if (!selectedSSHConfig) {
        message.error('未找到选中的SSH配置');
        return;
      }
      
      // 获取选中的设备分组的完整信息
      const selectedDeviceGroup = deviceGroups.find(group => group.id === values.deviceGroupId);
      if (!selectedDeviceGroup) {
        message.error('未找到选中的设备分组');
        return;
      }
      
      onSave({
        ...values,
        // 保存SSH配置的完整信息
        sshConfig: selectedSSHConfig,
        // 保存设备分组的完整信息
        deviceGroup: selectedDeviceGroup,
        // 保存选中的设备IP地址
        selectedDevices: ipAddresses,
        // 标记为已配置
        isConfigured: true,
        configured: true
      });
      onClose();
      message.success('配置已保存');
    } catch (error) {
      message.error('请检查配置信息');
      console.error('保存配置失败:', error);
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
          name="poolType"
          label="连接池类型"
          rules={[{ required: true, message: '请选择连接池类型' }]}
        >
          <Radio.Group>
            <Radio.Button value="redis">Redis通信连接池</Radio.Button>
            <Radio.Button value="device">网络设备连接池</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          name="sshConfigId"
          label="SSH配置"
          rules={[{ required: true, message: '请选择SSH配置' }]}
        >
          <Select
            placeholder="请选择SSH配置"
            loading={loading}
          >
            {sshConfigs.map(config => (
              <Option key={config.id} value={config.id}>
                {config.name}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="deviceGroupId"
          label="设备分组"
          rules={[{ required: true, message: '请选择设备分组' }]}
        >
          <Select
            placeholder="请选择设备分组"
            loading={loading}
            onChange={handleGroupChange}
          >
            {deviceGroups.map(group => (
              <Option key={group.id} value={group.id}>
                {group.name}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="selectedDevices"
          label="目标设备IP"
          rules={[{ required: true, message: '请选择目标设备IP' }]}
        >
          <Select
            mode="multiple"
            placeholder="请选择目标设备IP"
            options={ipAddresses.map(ip => ({ label: ip, value: ip }))}
            loading={loading}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 