import React, { useState, useEffect } from 'react';
import { 
  Table, Button, Space, Modal, Form, Input, 
  Select, Switch, message, Popconfirm, Tag, Tooltip, Typography, Card, Row, Col, Statistic 
} from 'antd';
import { 
  UserOutlined, LockOutlined, SafetyOutlined, 
  EditOutlined, DeleteOutlined, PlusOutlined, 
  QuestionCircleOutlined, SyncOutlined, StopOutlined, CheckCircleOutlined, UserAddOutlined, TeamOutlined,
  SearchOutlined
} from '@ant-design/icons';
import request from '../../utils/request';

const { Option } = Select;
const { Title } = Typography;

interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_ldap_user: boolean;
  department: string;
  role: string;
  totp_enabled: boolean;
  last_login: string;
  created_at: string;
  permissions?: {
    [key: string]: boolean;
  };
}

interface LDAPUser {
  username: string;
  email: string;
  department: string;
  displayName: string;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [form] = Form.useForm();
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [resetPasswordModal, setResetPasswordModal] = useState(false);
  const [resetPasswordForm] = Form.useForm();
  const [userType, setUserType] = useState<'local' | 'ldap'>('local');
  const [ldapUser, setLdapUser] = useState<LDAPUser | null>(null);
  const [searchingLdap, setSearchingLdap] = useState(false);

  const roleOptions = [
    { label: '管理员', value: 'admin' },
    { label: '普通用户', value: 'user' }
  ];

  // 获取用户列表
  const fetchUsers = async () => {
    setLoading(true);
    try {
      console.log('Fetching users...');
      // 先检查认证状态
      const authCheck = await request.get('/auth/verify');
      console.log('Auth check:', authCheck.data);
      
      // 获取用户列表
      const response = await request.get('/users/');
      console.log('Users response:', response.data);
      setUsers(response.data);
    } catch (error: any) {
      console.error('获取用户列表失败:', error);
      
      // 如果是403错误，显示权限不足的消息
      if (error.response && error.response.status === 403) {
        message.error('您没有权限访问用户列表');
      } 
      // 如果是401错误，让拦截器处理（重定向到登录页）
      else if (error.response && error.response.status === 401) {
        console.log('认证失败，将重定向到登录页');
      }
      // 其他错误
      else {
        message.error('获取用户列表失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // 搜索LDAP用户
  const searchLdapUser = async (username: string) => {
    setSearchingLdap(true);
    try {
      const response = await request.get(`/ldap/search?username=${username}`);
      if (response.data) {
        setLdapUser(response.data);
        // 自动填充表单
        form.setFieldsValue({
          email: response.data.email,
          department: response.data.department
        });
      } else {
        message.warning('未找到LDAP用户');
        setLdapUser(null);
      }
    } catch (error) {
      console.error('搜索LDAP用户失败:', error);
      message.error('搜索LDAP用户失败');
      setLdapUser(null);
    } finally {
      setSearchingLdap(false);
    }
  };

  // 打开创建用户模态框
  const showCreateModal = () => {
    setModalTitle('创建用户');
    setEditingUser(null);
    setLdapUser(null);
    setUserType('local');
    form.resetFields();
    setModalVisible(true);
  };

  // 显示编辑用户模态框
  const showEditModal = (user: User) => {
    setEditingUser(user);
    setModalTitle('编辑用户');
    
    // 设置表单初始值
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      department: user.department,
      role: user.role,
      is_active: user.is_active,
      totp_enabled: user.totp_enabled,
      permissions: user.permissions || {}
    });
    
    setModalVisible(true);
  };

  // 打开重置密码模态框
  const showResetPasswordModal = (user: User) => {
    setEditingUser(user);
    resetPasswordForm.resetFields();
    setResetPasswordModal(true);
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingUser) {
        // 更新用户
        await request.put(`/users/${editingUser.id}`, values);
        message.success('用户更新成功');
      } else {
        // 创建用户
        const createData = {
          ...values,
          is_ldap_user: userType === 'ldap'
        };
        await request.post('/users/', createData);
        message.success('用户创建成功');
      }
      
      setModalVisible(false);
      fetchUsers();
    } catch (error) {
      console.error('提交表单失败:', error);
      message.error('操作失败，请重试');
    }
  };

  // 重置密码
  const handleResetPassword = async () => {
    try {
      const values = await resetPasswordForm.validateFields();
      
      await request.post('/users/reset-password', {
        username: editingUser?.username,
        new_password: values.password
      });
      
      message.success('密码重置成功');
      setResetPasswordModal(false);
    } catch (error) {
      console.error('重置密码失败:', error);
      message.error('重置密码失败，请重试');
    }
  };

  // 禁用/启用用户
  const toggleUserStatus = async (user: User) => {
    try {
      await request.post('/users/disable', {
        username: user.username,
        enable: !user.is_active
      });
      
      message.success(`用户${user.is_active ? '禁用' : '启用'}成功`);
      fetchUsers();
    } catch (error) {
      console.error('更改用户状态失败:', error);
      message.error('操作失败，请重试');
    }
  };

  // 启用/禁用2FA
  const toggle2FA = async (user: User) => {
    try {
      await request.post('/users/toggle-2fa', {
        username: user.username,
        enable: !user.totp_enabled
      });
      
      message.success(`${user.totp_enabled ? '禁用' : '启用'}双因素认证成功`);
      fetchUsers();
    } catch (error) {
      console.error('更改2FA状态失败:', error);
      message.error('操作失败，请重试');
    }
  };

  // 删除用户
  const deleteUser = async (user: User) => {
    try {
      await request.post('/users/delete', {
        username: user.username
      });
      
      message.success('用户删除成功');
      fetchUsers();
    } catch (error) {
      console.error('删除用户失败:', error);
      message.error('操作失败，请重试');
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      render: (text: string) => text || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        let color = 'blue';
        if (role === 'admin') color = 'red';
        if (role === 'auditor') color = 'green';
        return <Tag color={color}>{roleOptions.find(opt => opt.value === role)?.label || role}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '账号类型',
      dataIndex: 'is_ldap_user',
      key: 'is_ldap_user',
      render: (isLdap: boolean) => (
        <Tag color={isLdap ? 'purple' : 'blue'}>
          {isLdap ? 'LDAP' : '本地'}
        </Tag>
      ),
    },
    {
      title: '双因素认证',
      dataIndex: 'totp_enabled',
      key: 'totp_enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'orange'}>
          {enabled ? '已启用' : '未启用'}
        </Tag>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (text: string) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: User) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => showEditModal(record)} 
              disabled={record.is_ldap_user}
            />
          </Tooltip>
          <Tooltip title="重置密码">
            <Button 
              type="text" 
              icon={<LockOutlined />} 
              onClick={() => showResetPasswordModal(record)}
              disabled={record.is_ldap_user}
            />
          </Tooltip>
          <Tooltip title={record.totp_enabled ? "禁用2FA" : "启用2FA"}>
            <Button 
              type="text" 
              icon={<SafetyOutlined />} 
              onClick={() => toggle2FA(record)}
            />
          </Tooltip>
          <Tooltip title={record.is_active ? "禁用" : "启用"}>
            <Popconfirm
              title={`确定要${record.is_active ? '禁用' : '启用'}该用户吗?`}
              onConfirm={() => toggleUserStatus(record)}
              okText="确定"
              cancelText="取消"
              icon={<QuestionCircleOutlined style={{ color: 'red' }} />}
            >
              <Button 
                type="text" 
                danger={record.is_active}
                icon={record.is_active ? <StopOutlined /> : <CheckCircleOutlined />}
              />
            </Popconfirm>
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定要删除该用户吗？此操作不可恢复！"
              onConfirm={() => deleteUser(record)}
              okText="确定"
              cancelText="取消"
              icon={<QuestionCircleOutlined style={{ color: 'red' }} />}
            >
              <Button 
                type="text" 
                danger
                icon={<DeleteOutlined />}
                disabled={record.username === 'admin'} // 不允许删除admin用户
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="user-management">
      <Card>
        <Title level={3}>用户管理</Title>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card>
              <Statistic
                title="总用户数"
                value={users.length}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="活跃用户"
                value={users.filter(user => user.is_active).length}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="管理员数量"
                value={users.filter(user => user.role === 'admin').length}
                prefix={<LockOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Button 
          type="primary" 
          icon={<UserAddOutlined />} 
          onClick={showCreateModal}
          style={{ marginBottom: 16 }}
        >
          添加用户
        </Button>

        <Table 
          columns={columns} 
          dataSource={users} 
          rowKey="id" 
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
        
        {/* 创建/编辑用户模态框 */}
        <Modal
          title={modalTitle}
          open={modalVisible}
          onOk={handleSubmit}
          onCancel={() => setModalVisible(false)}
          okText="确定"
          cancelText="取消"
          width={600}
        >
          <Form
            form={form}
            layout="vertical"
          >
            {!editingUser && (
              <Form.Item
                name="userType"
                label="用户类型"
                rules={[{ required: true, message: '请选择用户类型' }]}
                initialValue="local"
              >
                <Select onChange={(value) => setUserType(value)}>
                  <Option value="local">本地用户</Option>
                  <Option value="ldap">LDAP用户</Option>
                </Select>
              </Form.Item>
            )}

            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input 
                prefix={<UserOutlined />} 
                disabled={!!editingUser}
                suffix={userType === 'ldap' && !editingUser && (
                  <Button 
                    type="link" 
                    icon={<SearchOutlined />} 
                    onClick={() => searchLdapUser(form.getFieldValue('username'))}
                    loading={searchingLdap}
                  />
                )}
              />
            </Form.Item>

            {userType === 'local' && !editingUser && (
              <Form.Item
                name="password"
                label="密码"
                rules={[{ required: true, message: '请输入密码' }]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>
            )}
            
            <Form.Item
              name="email"
              label="邮箱"
              rules={[
                { type: 'email', message: '请输入有效的邮箱地址' },
                { required: true, message: '请输入邮箱' }
              ]}
            >
              <Input disabled={userType === 'ldap' && !!ldapUser} />
            </Form.Item>
            
            <Form.Item
              name="department"
              label="部门"
            >
              <Input disabled={userType === 'ldap' && !!ldapUser} />
            </Form.Item>
            
            <Form.Item
              name="role"
              label="角色"
              rules={[{ required: true, message: '请选择角色' }]}
            >
              <Select>
                <Select.Option value="admin">管理员</Select.Option>
                <Select.Option value="operator">操作员</Select.Option>
                <Select.Option value="auditor">审计员</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name="totp_enabled"
              label="启用双因素认证"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
            
            <Form.Item
              name="is_active"
              label="启用账户"
              valuePropName="checked"
              initialValue={true}
            >
              <Switch />
            </Form.Item>

            {userType === 'ldap' && ldapUser && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Typography.Text type="secondary">LDAP用户信息</Typography.Text>
                <div>显示名称: {ldapUser.displayName}</div>
                <div>邮箱: {ldapUser.email}</div>
                <div>部门: {ldapUser.department}</div>
              </Card>
            )}

            <Form.Item
              name="permissions"
              label="权限设置"
              tooltip="设置用户的具体权限"
            >
              <Card size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Form.Item
                    name={['permissions', 'can_view_devices']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="查看设备" unCheckedChildren="查看设备" />
                  </Form.Item>
                  <Form.Item
                    name={['permissions', 'can_edit_devices']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="编辑设备" unCheckedChildren="编辑设备" />
                  </Form.Item>
                  <Form.Item
                    name={['permissions', 'can_delete_devices']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="删除设备" unCheckedChildren="删除设备" />
                  </Form.Item>
                  <Form.Item
                    name={['permissions', 'can_view_credentials']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="查看凭据" unCheckedChildren="查看凭据" />
                  </Form.Item>
                  <Form.Item
                    name={['permissions', 'can_edit_credentials']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="编辑凭据" unCheckedChildren="编辑凭据" />
                  </Form.Item>
                  <Form.Item
                    name={['permissions', 'can_delete_credentials']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="删除凭据" unCheckedChildren="删除凭据" />
                  </Form.Item>
                  <Form.Item
                    name={['permissions', 'can_view_audit_logs']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="查看审计日志" unCheckedChildren="查看审计日志" />
                  </Form.Item>
                  <Form.Item
                    name={['permissions', 'can_export_audit_logs']}
                    valuePropName="checked"
                    noStyle
                  >
                    <Switch checkedChildren="导出审计日志" unCheckedChildren="导出审计日志" />
                  </Form.Item>
                </Space>
              </Card>
            </Form.Item>
          </Form>
        </Modal>
        
        {/* 重置密码模态框 */}
        <Modal
          title="重置密码"
          open={resetPasswordModal}
          onOk={handleResetPassword}
          onCancel={() => setResetPasswordModal(false)}
          okText="确定"
          cancelText="取消"
        >
          <Form
            form={resetPasswordForm}
            layout="vertical"
          >
            <Form.Item
              name="password"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 6, message: '密码长度不能少于6个字符' }
              ]}
            >
              <Input.Password prefix={<LockOutlined />} />
            </Form.Item>
            
            <Form.Item
              name="confirmPassword"
              label="确认密码"
              dependencies={['password']}
              rules={[
                { required: true, message: '请确认密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
            >
              <Input.Password prefix={<LockOutlined />} />
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  );
};

export default UserManagement; 