import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Alert, Typography } from 'antd';
import { LockOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import request from '../utils/request';

const { Title, Text } = Typography;

const ChangePassword: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (values: any) => {
    setLoading(true);
    setError(null);
    
    try {
      await request.post('/auth/change-password', values);
      message.success('密码修改成功，请重新登录');
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      navigate('/login');
    } catch (error: any) {
      if (error.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('密码修改失败');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100%',
      padding: '20px'
    }}>
      <Card 
        style={{ 
          width: 400, 
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          borderRadius: '8px'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <Title level={3}>修改密码</Title>
          <Text type="secondary">请输入您的旧密码和新密码</Text>
        </div>
        
        {error && (
          <Alert
            message="错误"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: '16px' }}
          />
        )}
        
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="oldPassword"
            label="旧密码"
            rules={[{ required: true, message: '请输入旧密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入旧密码" />
          </Form.Item>
          
          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码长度不能少于8个字符' },
              {
                pattern: /[A-Z]/,
                message: '密码必须包含至少一个大写字母'
              },
              {
                pattern: /[a-z]/,
                message: '密码必须包含至少一个小写字母'
              },
              {
                pattern: /[0-9]/,
                message: '密码必须包含至少一个数字'
              }
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入新密码" />
          </Form.Item>
          
          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请确认新密码" />
          </Form.Item>
          
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<CheckCircleOutlined />}
              style={{ width: '100%' }}
            >
              确认修改
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default ChangePassword; 