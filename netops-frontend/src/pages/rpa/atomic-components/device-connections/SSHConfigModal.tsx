import React, { useEffect, useState } from 'react';
import { Modal, Form, Input, Select, InputNumber, Switch, Row, Col, message, Spin, Button, Space, Card } from 'antd';
import { Typography } from 'antd';
import { getDeviceTypes, createSSHConfig, updateSSHConfig } from '../../../../services/sshConfig';
import request from '../../../../utils/request';
import { getCredentials, getFullCredential, Credential, FullCredential } from '../../../../services/credential';

const { Text } = Typography;

/**
 * SSH配置模态框组件的属性接口
 */
interface SSHConfigModalProps {
  visible: boolean;              // 模态框是否可见
  onCancel: () => void;         // 取消按钮回调函数
  onSuccess: () => void;        // 成功提交后的回调函数
  initialValues?: any;          // 初始值，用于编辑模式
}

const { Option } = Select;

/**
 * SSH配置模态框组件
 * 用于创建和编辑SSH连接配置，包含基本连接信息和Netmiko特定参数
 */
const SSHConfigModal: React.FC<SSHConfigModalProps> = ({
  visible,
  onCancel,
  onSuccess,
  initialValues,
}) => {
  const [form] = Form.useForm();                    // 表单实例
  const [deviceTypes, setDeviceTypes] = useState<string[]>([]);  // 设备类型列表
  const [credentials, setCredentials] = useState<Credential[]>([]); // 凭证列表
  const [loading, setLoading] = useState(false);    // 加载状态
  const [selectedDeviceType, setSelectedDeviceType] = useState<string>('');  // 用于控制enable密码字段的显示
  const [selectedCredential, setSelectedCredential] = useState<FullCredential | null>(null); // 选中的完整凭证信息

  /**
   * 获取设备类型列表
   * 在组件挂载时调用
   */
  useEffect(() => {
    const fetchDeviceTypes = async () => {
      try {
        const types = await getDeviceTypes();
        setDeviceTypes(types);
      } catch (error) {
        message.error('获取设备类型列表失败');
      }
    };
    fetchDeviceTypes();
  }, []);

  /**
   * 获取凭证列表
   * 在组件挂载时调用
   */
  useEffect(() => {
    const fetchCredentials = async () => {
      try {
        const creds = await getCredentials();
        setCredentials(creds);
      } catch (error) {
        console.error('获取凭证列表失败:', error);
        message.error('获取凭证列表失败');
      }
    };
    fetchCredentials();
  }, []);

  /**
   * 处理凭证选择变化
   * 获取完整凭证信息
   */
  const handleCredentialChange = async (credentialId: number) => {
    try {
      const fullCredential = await getFullCredential(credentialId);
      setSelectedCredential(fullCredential);
      console.log('获取到完整凭证信息:', fullCredential);
      
      // 更新表单中的用户名和密码
      form.setFieldsValue({
        username: fullCredential.username,
        password: fullCredential.password,
        enable_secret: fullCredential.enable_password
      });
    } catch (error) {
      console.error('获取完整凭证信息失败:', error);
      message.error('获取完整凭证信息失败');
    }
  };

  /**
   * 处理表单提交
   * 根据是否有initialValues决定是创建还是更新操作
   */
  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      
      // 确保所有必需字段都存在
      if (!values.name || !values.device_type || !values.credential_id) {
        message.error('请填写所有必需字段');
        return;
      }

      // 如果选择了凭证，使用凭证中的信息
      if (selectedCredential) {
        values.username = selectedCredential.username;
        values.password = selectedCredential.password;
        if (values.device_type?.startsWith('cisco_')) {
          values.enable_secret = values.enable_secret || selectedCredential.enable_password;
        }
      } else {
        message.error('请选择认证信息');
        return;
      }

      if (initialValues?.id) {
        await updateSSHConfig(initialValues.id, values);
        message.success('SSH配置更新成功');
      } else {
        await createSSHConfig(values);
        message.success('SSH配置创建成功');
      }

      form.resetFields();
      onSuccess();
    } catch (error: any) {
      console.error('提交表单失败:', error);
      if (error.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('操作失败: ' + (error.message || '未知错误'));
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * 处理设备类型变化
   * 用于控制enable密码字段的显示/隐藏
   */
  const handleDeviceTypeChange = (value: string) => {
    setSelectedDeviceType(value);
  };

  return (
    <Modal
      title={initialValues ? '编辑SSH配置' : '新增SSH配置'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      confirmLoading={loading}
      width={800}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          确定
        </Button>
      ]}
    >
      <Spin spinning={loading}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            ...initialValues,
            port: initialValues?.port || 22,
            // Netmiko默认参数
            global_delay_factor: initialValues?.global_delay_factor || 1,
            auth_timeout: initialValues?.auth_timeout || 20,
            banner_timeout: initialValues?.banner_timeout || 20,
            fast_cli: initialValues?.fast_cli || false,
            session_timeout: initialValues?.session_timeout || 60,
            conn_timeout: initialValues?.conn_timeout || 10,
            keepalive: initialValues?.keepalive || 10,
            verbose: initialValues?.verbose || false,
          }}
        >
          {/* 基本信息部分 */}
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="SSH连接名称"
                rules={[{ required: true, message: '请输入SSH连接名称' }]}
                tooltip="此名称将用于流程设计器中标识该连接配置"
              >
                <Input placeholder="请输入SSH连接名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="device_type"
                label="设备类型"
                rules={[{ required: true, message: '请选择设备类型' }]}
                tooltip="选择Netmiko支持的设备类型"
              >
                <Select 
                  placeholder="请选择设备类型"
                  onChange={handleDeviceTypeChange}
                >
                  {deviceTypes.map((type) => (
                    <Option key={type} value={type}>
                      {type}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="port"
                label="SSH端口"
                rules={[{ required: true, message: '请输入SSH端口' }]}
                tooltip="SSH连接端口号"
              >
                <InputNumber min={1} max={65535} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="credential_id"
                label="认证信息"
                rules={[{ required: true, message: '请选择认证信息' }]}
                tooltip="选择包含用户名和密码的认证信息"
              >
                <Select 
                  placeholder="请选择认证信息"
                  onChange={handleCredentialChange}
                >
                  {credentials.map((credential) => (
                    <Option key={credential.id} value={credential.id}>
                      {credential.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {/* 思科设备特有的Enable密码配置 */}
          {selectedDeviceType.startsWith('cisco_') && (
            <Row gutter={24}>
              <Col span={12}>
                <Form.Item
                  name="enable_secret"
                  label="Enable密码"
                  tooltip="思科设备的特权模式密码"
                >
                  <Input.Password placeholder="请输入Enable密码" />
                </Form.Item>
              </Col>
            </Row>
          )}

          {/* 显示选中的凭证信息 */}
          {selectedCredential && (
            <Row gutter={24}>
              <Col span={24}>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <p><strong>用户名:</strong> {selectedCredential.username}</p>
                  <p><strong>密码:</strong> {selectedCredential.password}</p>
                  {selectedCredential.enable_password && (
                    <p><strong>Enable密码:</strong> {selectedCredential.enable_password}</p>
                  )}
                </Card>
              </Col>
            </Row>
          )}

          {/* Netmiko特定参数部分 */}
          <Typography.Title level={4}>Netmiko特定参数</Typography.Title>
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="global_delay_factor"
                label="全局延迟因子"
                tooltip="调整命令执行延迟的因子，值越大延迟越长"
              >
                <InputNumber min={0.1} max={10} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="auth_timeout"
                label="认证超时时间(秒)"
                tooltip="SSH认证超时时间"
              >
                <InputNumber min={1} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="banner_timeout"
                label="Banner超时时间(秒)"
                tooltip="等待设备banner的超时时间"
              >
                <InputNumber min={1} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="fast_cli"
                label="快速CLI模式"
                tooltip="是否启用快速CLI模式，可提高命令执行速度"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="session_timeout"
                label="会话超时时间(秒)"
                tooltip="SSH会话超时时间"
              >
                <InputNumber min={1} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="conn_timeout"
                label="连接超时时间(秒)"
                tooltip="建立SSH连接的超时时间"
              >
                <InputNumber min={1} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="keepalive"
                label="保活间隔(秒)"
                tooltip="SSH连接保活间隔"
              >
                <InputNumber min={1} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="verbose"
                label="详细日志"
                tooltip="是否启用详细日志输出"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
            tooltip="SSH连接配置的描述信息"
          >
            <Input.TextArea rows={4} placeholder="请输入描述信息" />
          </Form.Item>
        </Form>
      </Spin>
    </Modal>
  );
};

export default SSHConfigModal; 