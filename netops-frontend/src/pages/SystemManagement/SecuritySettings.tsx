import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Switch,
  message,
  Typography,
  Space,
  Alert,
  Divider,
  Row,
  Col,
  Statistic,
  Tabs
} from 'antd';
import {
  SaveOutlined,
  SafetyOutlined,
  ClockCircleOutlined,
  LockOutlined,
  UserOutlined,
  KeyOutlined
} from '@ant-design/icons';
import request from '../../utils/request';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;

// 后端返回的数据结构
interface BackendSecuritySettings {
  password_expiry_days: number;
  max_failed_attempts: number;
  lockout_duration_minutes: number;
  session_timeout_minutes: number;
  require_2fa_for_admins: boolean;
  password_complexity_enabled: boolean;
  password_min_length: number;
  password_require_uppercase: boolean;
  password_require_lowercase: boolean;
  password_require_numbers: boolean;
  password_require_special: boolean;
}

const SecuritySettings: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState<BackendSecuritySettings | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await request.get('security/settings');
      setSettings(response.data);
      form.setFieldsValue(response.data);
    } catch (error) {
      message.error('获取安全设置失败');
    }
  };

  const handleSubmit = async (values: BackendSecuritySettings) => {
    setLoading(true);
    try {
      // 确保所有必需的字段都存在
      const settingsData = {
        password_expiry_days: values.password_expiry_days,
        max_failed_attempts: values.max_failed_attempts,
        lockout_duration_minutes: values.lockout_duration_minutes,
        session_timeout_minutes: values.session_timeout_minutes,
        require_2fa_for_admins: values.require_2fa_for_admins,
        password_complexity_enabled: values.password_complexity_enabled,
        password_min_length: values.password_min_length,
        password_require_uppercase: values.password_require_uppercase,
        password_require_lowercase: values.password_require_lowercase,
        password_require_numbers: values.password_require_numbers,
        password_require_special: values.password_require_special
      };
      
      await request.put('security/settings', settingsData);
      message.success('安全设置保存成功');
      fetchSettings();
    } catch (error) {
      message.error('保存安全设置失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="security-settings">
      <Card>
        <Title level={3}>安全设置</Title>

        {settings && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="密码有效期"
                  value={settings.password_expiry_days}
                  suffix="天"
                  prefix={<KeyOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="会话超时"
                  value={settings.session_timeout_minutes}
                  suffix="分钟"
                  prefix={<ClockCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="双因素认证"
                  value={settings.require_2fa_for_admins ? '已启用' : '已禁用'}
                  valueStyle={{
                    color: settings.require_2fa_for_admins ? '#3f8600' : '#cf1322'
                  }}
                  prefix={<SafetyOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="密码复杂度"
                  value={settings.password_complexity_enabled ? '已启用' : '已禁用'}
                  valueStyle={{
                    color: settings.password_complexity_enabled ? '#3f8600' : '#cf1322'
                  }}
                  prefix={<LockOutlined />}
                />
              </Card>
            </Col>
          </Row>
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={24}>
            <Col span={8}>
              <Card title="密码策略" style={{ marginBottom: 24 }}>
                <Form.Item
                  name="password_min_length"
                  label="最小密码长度"
                  rules={[{ required: true, message: '请输入最小密码长度' }]}
                >
                  <Input type="number" min={8} />
                </Form.Item>
                
                <Form.Item
                  name="password_expiry_days"
                  label="密码有效期（天）"
                  rules={[{ required: true, message: '请输入密码有效期' }]}
                >
                  <Input type="number" min={1} />
                </Form.Item>
                
                <Form.Item
                  name="password_complexity_enabled"
                  label="启用密码复杂度要求"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
                
                <Title level={5}>密码复杂度要求</Title>
                <Form.Item
                  name="password_require_uppercase"
                  label="要求大写字母"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
                <Form.Item
                  name="password_require_lowercase"
                  label="要求小写字母"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
                <Form.Item
                  name="password_require_numbers"
                  label="要求数字"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
                <Form.Item
                  name="password_require_special"
                  label="要求特殊字符"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
              </Card>
            </Col>
            
            <Col span={8}>
              <Card title="会话策略" style={{ marginBottom: 24 }}>
                <Form.Item
                  name="session_timeout_minutes"
                  label="会话超时时间（分钟）"
                  rules={[{ required: true, message: '请输入会话超时时间' }]}
                >
                  <Input type="number" min={1} />
                </Form.Item>
                
                <Form.Item
                  name="max_failed_attempts"
                  label="最大失败尝试次数"
                  rules={[{ required: true, message: '请输入最大失败尝试次数' }]}
                >
                  <Input type="number" min={1} />
                </Form.Item>
                
                <Form.Item
                  name="lockout_duration_minutes"
                  label="账户锁定时间（分钟）"
                  rules={[{ required: true, message: '请输入账户锁定时间' }]}
                >
                  <Input type="number" min={1} />
                </Form.Item>
              </Card>
            </Col>
            
            <Col span={8}>
              <Card title="双因素认证" style={{ marginBottom: 24 }}>
                <Form.Item
                  name="require_2fa_for_admins"
                  label="管理员强制启用双因素认证"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
                <Paragraph type="secondary">
                  启用后，所有管理员用户必须设置双因素认证才能登录系统
                </Paragraph>
              </Card>
            </Col>
          </Row>

          <Divider />
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={loading}
            >
              保存设置
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default SecuritySettings; 