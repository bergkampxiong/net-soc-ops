import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Typography, Space, Steps, Spin } from 'antd';
import { SafetyOutlined, KeyOutlined, QrcodeOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import request from '../utils/request';

const { Title, Paragraph, Text } = Typography;
const { Step } = Steps;

const TwoFactorVerify: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [setupMode, setSetupMode] = useState(false);
  const [totpData, setTotpData] = useState<any>(null);
  const [username, setUsername] = useState('');
  const [currentStep, setCurrentStep] = useState(0);
  const [totpCode, setTotpCode] = useState('');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const user = params.get('username');
    const mode = params.get('mode');
    
    if (user) {
      setUsername(user);
      if (mode === 'setup') {
        setCurrentStep(0);
        setSetupMode(true);
        setupTOTP(user);
      } else {
        setCurrentStep(1);
      }
    } else {
      message.error('缺少用户名参数');
      navigate('/login');
    }
  }, [location, navigate]);

  const setupTOTP = async (user: string) => {
    setLoading(true);
    try {
      const response = await request.post('auth/totp-setup-for-user', {
        username: user
      });
      setTotpData(response.data);
      setCurrentStep(1);
    } catch (error) {
      console.error('设置TOTP失败:', error);
      message.error('设置TOTP失败，请重试');
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setLoading(true);
    try {
      const response = await request.post('auth/totp-verify', {
        username,
        totp_code: totpCode
      });
      
      if (response.status === 200) {
        const { access_token, refresh_token } = response.data;
        localStorage.setItem('token', access_token);
        if (refresh_token) {
          localStorage.setItem('refresh_token', refresh_token);
        }
        localStorage.setItem('username', username);
        message.success('验证成功');
        navigate('/');
      }
    } catch (error) {
      console.error('验证失败:', error);
      message.error('验证码错误，请重试');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => {
        message.success('已复制到剪贴板');
      },
      () => {
        message.error('复制失败');
      }
    );
  };

  const steps = [
    {
      title: '准备',
      icon: <SafetyOutlined />,
      content: (
        <div>
          <Paragraph>
            正在准备双因素认证设置...
          </Paragraph>
        </div>
      ),
    },
    {
      title: '扫描二维码',
      icon: <QrcodeOutlined />,
      content: (
        <div>
          <Paragraph>
            请使用Google Authenticator或其他TOTP应用扫描下方二维码。
          </Paragraph>
          
          {totpData && (
            <>
              <div style={{ textAlign: 'center', margin: '20px 0' }}>
                <img 
                  src={`/api/auth/totp-qrcode?uri=${encodeURIComponent(totpData.uri)}`} 
                  alt="TOTP QR Code" 
                  style={{ maxWidth: '100%', border: '1px solid #f0f0f0', padding: 8 }}
                />
              </div>
              
              <Paragraph>
                或者手动输入以下密钥：
                <Space>
                  <Text code>{totpData.secret}</Text>
                  <Button 
                    type="text" 
                    size="small" 
                    onClick={() => copyToClipboard(totpData.secret)}
                  >
                    复制
                  </Button>
                </Space>
              </Paragraph>
              
              <Paragraph>
                <Text strong>备用验证码：</Text>
                <div style={{ background: '#f5f5f5', padding: 10, borderRadius: 4, marginTop: 8 }}>
                  {totpData.backup_codes.map((code: string, index: number) => (
                    <Text key={index} code style={{ marginRight: 8, marginBottom: 8, display: 'inline-block' }}>
                      {code}
                    </Text>
                  ))}
                </div>
                <Button 
                  type="text" 
                  size="small" 
                  onClick={() => copyToClipboard(totpData.backup_codes.join('\n'))}
                >
                  复制所有
                </Button>
              </Paragraph>
              
              <Form
                onFinish={handleVerify}
                layout="vertical"
              >
                <Form.Item
                  name="totp_code"
                  label="请输入验证器应用生成的6位验证码"
                  rules={[
                    { required: true, message: '请输入验证码' },
                    { len: 6, message: '验证码必须是6位数字' }
                  ]}
                >
                  <Input 
                    prefix={<KeyOutlined />}
                    placeholder="6位验证码"
                    maxLength={6}
                    size="large"
                    style={{ width: '100%' }}
                    onChange={(e) => setTotpCode(e.target.value)}
                  />
                </Form.Item>
                
                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    icon={<SafetyOutlined />}
                    loading={loading}
                    size="large"
                    style={{ width: '100%' }}
                  >
                    验证并完成设置
                  </Button>
                </Form.Item>
              </Form>
            </>
          )}
        </div>
      ),
    },
    {
      title: '完成',
      icon: <CheckCircleOutlined />,
      content: (
        <div>
          <Paragraph>
            <Text strong>双因素认证设置成功！</Text>
          </Paragraph>
          <Paragraph>
            您现在可以使用双因素认证登录系统。请妥善保管您的备用验证码，以防丢失验证器应用。
          </Paragraph>
          <Paragraph>
            正在返回登录页面...
          </Paragraph>
        </div>
      ),
    },
  ];

  return (
    <div className="two-factor-verify">
      <Card style={{ maxWidth: 600, margin: '100px auto' }}>
        <Title level={3}>双因素认证</Title>
        
        {setupMode ? (
          <>
            <Steps
              current={currentStep}
              items={steps.map(item => ({
                title: item.title,
                icon: item.icon,
              }))}
              style={{ marginBottom: 24 }}
            />
            
            <div className="steps-content">
              {steps[currentStep].content}
            </div>
          </>
        ) : (
          <>
            <Paragraph>
              请输入您的验证器应用生成的6位验证码。
            </Paragraph>
            
            <Form
              onFinish={handleVerify}
              layout="vertical"
            >
              <Form.Item
                name="totp_code"
                rules={[
                  { required: true, message: '请输入验证码' },
                  { len: 6, message: '验证码必须是6位数字' }
                ]}
              >
                <Input 
                  prefix={<KeyOutlined />}
                  placeholder="6位验证码"
                  maxLength={6}
                  size="large"
                  style={{ width: '100%' }}
                  onChange={(e) => setTotpCode(e.target.value)}
                />
              </Form.Item>
              
              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  icon={<SafetyOutlined />}
                  loading={loading}
                  size="large"
                  style={{ width: '100%' }}
                >
                  验证
                </Button>
              </Form.Item>
              
            </Form>
          </>
        )}
      </Card>
    </div>
  );
};

export default TwoFactorVerify; 