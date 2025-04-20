import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Typography, Steps, Spin } from 'antd';
import { UserOutlined, LockOutlined, SafetyOutlined, QrcodeOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import request from '../utils/request';

const { Title, Paragraph, Text } = Typography;
const { Step } = Steps;

interface LoginFormValues {
  username: string;
  password: string;
}

const Setup2FA: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [username, setUsername] = useState('');
  const [totpData, setTotpData] = useState<any>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [token, setToken] = useState('');
  const navigate = useNavigate();
  const location = useLocation();

  // 检查用户是否已登录
  useEffect(() => {
    const checkLoginStatus = async () => {
      console.log('Checking login status...');
      console.log('Current location:', location.pathname, location.search);
      
      const params = new URLSearchParams(location.search);
      const user = params.get('username');
      console.log('Username from URL:', user);
      
      if (user) {
        console.log('Setting username from URL:', user);
        setUsername(user);
        setupTOTP(user);
      } else {
        const savedToken = localStorage.getItem('token');
        const savedUsername = localStorage.getItem('username');
        console.log('Saved token exists:', !!savedToken);
        console.log('Saved username:', savedUsername);
        
        if (savedToken && savedUsername) {
          try {
            // 验证token是否有效
            console.log('Verifying token...');
            const response = await request.get('/api/auth/verify');
            
            if (response.status === 200) {
              console.log('Token verified successfully');
              setIsLoggedIn(true);
              setToken(savedToken);
              setUsername(savedUsername);
              message.success(`已登录为 ${savedUsername}`);
            }
          } catch (error: any) {
            console.error('Token验证失败:', error);
            // 清除无效的token
            localStorage.removeItem('token');
            localStorage.removeItem('username');
          }
        } else {
          console.log('No saved token or username found');
        }
      }
    };
    
    checkLoginStatus();
  }, [location]);

  // 用户登录
  const handleLogin = async (values: LoginFormValues) => {
    setLoading(true);
    try {
      console.log('Logging in user:', values.username);
      
      // 使用登录API验证用户身份
      const formData = new URLSearchParams();
      formData.append('username', values.username);
      formData.append('password', values.password);
      
      console.log('Sending login request with form data:', {
        username: values.username,
        password: '******' // 隐藏密码
      });
      
      const loginResponse = await request.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      console.log('Login response:', loginResponse.data);
      
      if (loginResponse.status === 200) {
        // 检查是否返回了token
        if (loginResponse.data.access_token) {
          const token = loginResponse.data.access_token;
          console.log('Full token:', token);
          
          // 如果token以2FA_REQUIRED_开头，说明需要2FA验证
          if (token.startsWith('2FA_REQUIRED_')) {
            // 检查是否是首次设置2FA
            const needSetup = token.includes('_SETUP_');
            console.log('2FA required, setup mode:', needSetup, 'token:', token);
            
            // 无论是否是首次设置，都进入设置流程
            console.log('User needs to setup 2FA, proceeding with setup');
            // 保存用户名
            setUsername(values.username);
            // 直接进入设置TOTP步骤
            setupTOTP(values.username);
            return;
          }
          
          // 正常token，保存并继续
          const newToken = loginResponse.data.access_token;
          localStorage.setItem('token', newToken);
          localStorage.setItem('username', values.username);
          
          setIsLoggedIn(true);
          setToken(newToken);
          setUsername(values.username);
          message.success(`登录成功，欢迎 ${values.username}`);
          
          // 直接进入设置TOTP步骤
          console.log('Login successful, proceeding to setup TOTP');
          setTimeout(() => {
            setupTOTP(values.username);
          }, 500); // 短暂延迟，确保状态更新
        } else {
          message.error('登录成功但未返回token，请重试');
        }
      } else {
        message.error('用户名或密码错误');
      }
    } catch (error) {
      console.error('登录失败:', error);
      message.error('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 设置TOTP
  const setupTOTP = async (user: string) => {
    setLoading(true);
    try {
      console.log('Setting up TOTP for user:', user);
      console.log('Is user logged in:', isLoggedIn);
      console.log('Current token:', token ? token.substring(0, 10) + '...' : 'none');
      
      let response;
      
      // 根据用户是否已登录选择不同的API端点
      if (isLoggedIn && token) {
        // 已登录用户使用/auth/totp-setup端点
        console.log('Using /auth/totp-setup endpoint for logged in user');
        response = await request.post('/auth/totp-setup', {}, {
          headers: {
            'Content-Type': 'application/json'
          }
        });
      } else {
        // 未登录用户或首次设置2FA的用户使用/auth/totp-setup-for-user端点
        console.log('Using /auth/totp-setup-for-user endpoint for user:', user);
        
        // 使用URLSearchParams格式发送请求
        const formData = new URLSearchParams();
        formData.append('username', user);
        
        console.log('Sending request with form data:', formData.toString());
        
        response = await request.post('/auth/totp-setup-for-user', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        });
      }
      
      console.log('TOTP setup response:', response.data);
      setTotpData(response.data);
      setCurrentStep(1); // 移动到扫描二维码步骤
    } catch (error) {
      console.error('设置TOTP失败:', error);
      message.error('设置双因素认证失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 验证TOTP
  const verifyTOTP = async (values: { totp_code: string }) => {
    setLoading(true);
    try {
      console.log('Verifying TOTP for user:', username, 'code:', values.totp_code);
      const response = await request.post('/auth/totp-verify', {
        totp_code: values.totp_code,
        username: username
      });
      
      console.log('TOTP verification response:', response.data);
      
      if (response.data.access_token) {
        // 验证成功，显示完成步骤
        setCurrentStep(2); // 移动到完成步骤
        message.success('双因素认证设置成功');
        
        // 更新token
        localStorage.setItem('token', response.data.access_token);
        
        // 3秒后返回首页
        setTimeout(() => {
          navigate('/');
        }, 3000);
      } else {
        message.error('验证失败，请重试');
      }
    } catch (error: any) {
      console.error('验证失败:', error);
      
      // 打印更详细的错误信息
      if (error.response) {
        // 服务器响应了，但状态码不在2xx范围内
        console.error('错误响应数据:', error.response.data);
        console.error('错误状态码:', error.response.status);
        
        if (error.response.data && error.response.data.detail) {
          message.error(`验证失败: ${error.response.data.detail}`);
        } else {
          message.error(`验证失败: 服务器返回 ${error.response.status} 错误`);
        }
      } else if (error.request) {
        // 请求已发送但没有收到响应
        console.error('未收到响应:', error.request);
        message.error('验证失败: 未收到服务器响应');
      } else {
        // 设置请求时发生错误
        console.error('请求错误:', error.message);
        message.error(`验证失败: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  // 复制到剪贴板
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

  // 登出
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setIsLoggedIn(false);
    setToken('');
    setUsername('');
    setCurrentStep(0);
    message.success('已登出');
  };

  // 登录表单
  const renderLoginForm = () => (
    <div>
      <Paragraph>
        请先登录您的账号，然后再设置双因素认证。
      </Paragraph>
      <Form
        name="login_form"
        onFinish={handleLogin}
        layout="vertical"
      >
        <Form.Item
          name="username"
          label="用户名"
          rules={[{ required: true, message: '请输入用户名' }]}
        >
          <Input 
            prefix={<UserOutlined />} 
            placeholder="用户名" 
            size="large"
          />
        </Form.Item>
        
        <Form.Item
          name="password"
          label="密码"
          rules={[{ required: true, message: '请输入密码' }]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="密码"
            size="large"
          />
        </Form.Item>
        
        <Form.Item>
          <Button 
            type="primary" 
            htmlType="submit" 
            loading={loading}
            size="large"
            style={{ width: '100%' }}
          >
            登录
          </Button>
        </Form.Item>
      </Form>
    </div>
  );

  // 已登录状态
  const renderLoggedInState = () => (
    <div>
      <Paragraph>
        您已登录为 <Text strong>{username}</Text>
      </Paragraph>
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <Button 
          type="primary" 
          onClick={() => setupTOTP(username)}
          loading={loading}
          size="large"
          style={{ flex: 1 }}
        >
          设置双因素认证
        </Button>
        <Button 
          onClick={handleLogout}
          size="large"
        >
          登出
        </Button>
      </div>
    </div>
  );

  // 扫描二维码步骤
  const renderQRCodeStep = () => (
    <div>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16 }}>
            正在加载TOTP数据...
          </Paragraph>
        </div>
      ) : totpData ? (
        <>
          <Paragraph>
            请使用Google Authenticator或其他TOTP应用扫描下方二维码。
          </Paragraph>
          
          <div style={{ textAlign: 'center', margin: '20px 0' }}>
            <img 
              src={`/api/auth/totp-qrcode?uri=${encodeURIComponent(totpData.uri)}`} 
              alt="TOTP QR Code" 
              style={{ maxWidth: '100%', border: '1px solid #f0f0f0', padding: 8 }}
            />
          </div>
          
          <Paragraph>
            或者手动输入以下密钥：
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '8px 0' }}>
              <Text code>{totpData.secret}</Text>
              <Button 
                type="text" 
                size="small" 
                onClick={() => copyToClipboard(totpData.secret)}
              >
                复制
              </Button>
            </div>
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
            onFinish={verifyTOTP}
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
                prefix={<SafetyOutlined />}
                placeholder="6位验证码"
                maxLength={6}
                size="large"
                style={{ width: '100%' }}
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
      ) : (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text type="danger">加载TOTP数据失败，请返回重试</Text>
          <Button 
            type="primary" 
            onClick={() => setCurrentStep(0)} 
            style={{ marginTop: 16 }}
          >
            返回
          </Button>
        </div>
      )}
    </div>
  );

  // 完成步骤
  const renderCompletionStep = () => (
    <div>
      <Paragraph>
        <Text strong>双因素认证设置成功！</Text>
      </Paragraph>
      <Paragraph>
        您现在可以使用双因素认证登录系统。请妥善保管您的备用验证码，以防丢失验证器应用。
      </Paragraph>
      <Paragraph>
        正在返回首页...
      </Paragraph>
    </div>
  );

  // 步骤内容
  const steps = [
    {
      title: '登录',
      icon: <UserOutlined />,
      content: isLoggedIn ? renderLoggedInState() : renderLoginForm(),
    },
    {
      title: '扫描二维码',
      icon: <QrcodeOutlined />,
      content: renderQRCodeStep(),
    },
    {
      title: '完成',
      icon: <CheckCircleOutlined />,
      content: renderCompletionStep(),
    },
  ];

  return (
    <div className="setup-2fa">
      <Card style={{ maxWidth: 600, margin: '100px auto' }}>
        <Title level={3}>设置双因素认证</Title>
        
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
      </Card>
    </div>
  );
};

export default Setup2FA; 