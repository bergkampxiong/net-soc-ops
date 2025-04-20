import React, { useState } from 'react';
import { Form, Input, Select, InputNumber, Button, Space, Card, Upload, Switch, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';

const { Option } = Select;

const DeviceConnections = () => {
  const [loading, setLoading] = useState(false);

  // 表单实例
  const [form] = Form.useForm();

  // 处理表单提交
  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      // 这里添加表单提交逻辑
      console.log('Form values:', values);
      message.success('保存成功');
    } catch (error) {
      console.error('保存失败:', error);
      message.error('保存失败');
    } finally {
      setLoading(false);
    }
  };

  // 渲染表单
  const renderForm = () => (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        api_type: 'netmiko',
        device_type: 'cisco_ios',
        timeout: 30,
        retry_count: 3,
        retry_delay: 5,
        port: 22,
        auth_type: 'password'
      }}
    >
      <Form.Item
        name="name"
        label="连接名称"
        rules={[{ required: true, message: '请输入连接名称' }]}
      >
        <Input placeholder="请输入连接名称" />
      </Form.Item>

      <Form.Item
        name="description"
        label="描述"
      >
        <Input.TextArea rows={4} placeholder="请输入描述" />
      </Form.Item>

      <Form.Item
        name="api_type"
        label="API类型"
        rules={[{ required: true, message: '请选择API类型' }]}
      >
        <Select>
          <Option value="netmiko">Netmiko</Option>
          <Option value="napalm">NAPALM</Option>
          <Option value="ansible">Ansible</Option>
        </Select>
      </Form.Item>

      <Form.Item
        name="device_type"
        label="设备类型"
        rules={[{ required: true, message: '请选择设备类型' }]}
      >
        <Select>
          <Option value="cisco_ios">Cisco IOS</Option>
          <Option value="cisco_nxos">Cisco NX-OS</Option>
          <Option value="huawei_vrp">Huawei VRP</Option>
          <Option value="ruijie_os">Ruijie OS</Option>
          <Option value="hp_comware">HP Comware</Option>
        </Select>
      </Form.Item>

      <Form.Item
        name="host"
        label="主机地址"
        rules={[{ required: true, message: '请输入主机地址' }]}
      >
        <Input placeholder="请输入主机地址" />
      </Form.Item>

      <Form.Item
        name="port"
        label="端口"
        rules={[{ required: true, message: '请输入端口' }]}
      >
        <InputNumber min={1} max={65535} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="auth_type"
        label="认证方式"
        rules={[{ required: true, message: '请选择认证方式' }]}
      >
        <Select>
          <Option value="password">密码认证</Option>
          <Option value="key">密钥认证</Option>
        </Select>
      </Form.Item>

      <Form.Item
        name="username"
        label="用户名"
        rules={[{ required: true, message: '请输入用户名' }]}
      >
        <Input placeholder="请输入用户名" />
      </Form.Item>

      <Form.Item
        name="password"
        label="密码"
        rules={[{ required: true, message: '请输入密码' }]}
      >
        <Input.Password placeholder="请输入密码" />
      </Form.Item>

      <Form.Item
        name="key_file"
        label="密钥文件"
        rules={[{ required: true, message: '请选择密钥文件' }]}
      >
        <Upload
          beforeUpload={() => false}
          maxCount={1}
          accept=".pem,.key"
        >
          <Button icon={<UploadOutlined />}>选择密钥文件</Button>
        </Upload>
      </Form.Item>

      <Form.Item
        name="timeout"
        label="超时时间(秒)"
        rules={[{ required: true, message: '请输入超时时间' }]}
      >
        <InputNumber min={1} max={300} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="retry_count"
        label="重试次数"
        rules={[{ required: true, message: '请输入重试次数' }]}
      >
        <InputNumber min={0} max={10} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="retry_delay"
        label="重试延迟(秒)"
        rules={[{ required: true, message: '请输入重试延迟' }]}
      >
        <InputNumber min={0} max={60} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="enable_password"
        label="Enable密码"
      >
        <Input.Password placeholder="请输入Enable密码" />
      </Form.Item>

      <Form.Item
        name="secret"
        label="Secret密码"
      >
        <Input.Password placeholder="请输入Secret密码" />
      </Form.Item>

      <Form.Item
        name="global_delay_factor"
        label="全局延迟因子"
      >
        <InputNumber min={1} max={8} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="fast_cli"
        label="快速CLI"
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        name="session_timeout"
        label="会话超时(秒)"
      >
        <InputNumber min={1} max={3600} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="keepalive"
        label="保持连接"
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        name="keepalive_interval"
        label="保持连接间隔(秒)"
      >
        <InputNumber min={1} max={60} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="keepalive_count"
        label="保持连接次数"
      >
        <InputNumber min={1} max={10} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="verbose"
        label="详细日志"
        valuePropName="checked"
      >
        <Switch />
      </Form.Item>

      <Form.Item
        name="log_file"
        label="日志文件"
      >
        <Input placeholder="请输入日志文件路径" />
      </Form.Item>

      <Form.Item
        name="log_level"
        label="日志级别"
      >
        <Select>
          <Option value="DEBUG">DEBUG</Option>
          <Option value="INFO">INFO</Option>
          <Option value="WARNING">WARNING</Option>
          <Option value="ERROR">ERROR</Option>
          <Option value="CRITICAL">CRITICAL</Option>
        </Select>
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading}>
            保存
          </Button>
          <Button onClick={() => form.resetFields()}>
            重置
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );

  return (
    <div className="device-connections-page">
      <Card title="设备连接配置">
        {renderForm()}
      </Card>
    </div>
  );
};

export default DeviceConnections; 