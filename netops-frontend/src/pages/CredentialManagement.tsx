import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Typography,
  Popconfirm,
  message,
  Tabs,
  Descriptions,
  Tag,
  Row,
  Col,
  Divider,
  Statistic,
  Badge
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  KeyOutlined,
  ApiOutlined,
  UserOutlined,
  QuestionCircleOutlined,
  EyeInvisibleOutlined,
  LockOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { formatBeijingToSecond } from '@/utils/formatTime';
import request from '../utils/request';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;
const { Password } = Input;

// 定义凭证类型枚举
enum CredentialType {
  SSH_PASSWORD = 'ssh_password',
  API_KEY = 'api_key',
  SSH_KEY = 'ssh_key',
  WINDOWS_DOMAIN = 'windows_domain'
}

// API 类型选项（与后端 APIVendor 一致）
const API_VENDOR_OPTIONS = [
  { value: 'generic', label: '常规 API' },
  { value: 'aws', label: 'AWS' },
  { value: 'aliyun', label: '阿里云' },
  { value: 'tencent', label: '腾讯云' },
  { value: 'huawei', label: '华为云' },
  { value: 'vmware', label: 'VMware' },
  { value: 'zscaler', label: 'Zscaler' },
];

// 定义凭证接口
interface Credential {
  id: number;
  name: string;
  description: string;
  credential_type: CredentialType;
  username?: string;
  password?: string;
  enable_password?: string;
  api_key?: string;
  api_secret?: string;
  api_vendor?: string;
  private_key?: string;
  passphrase?: string;
  domain?: string;
  created_at: string;
  updated_at: string;
  status: string;
}

const CredentialManagement: React.FC = () => {
  // 状态定义
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [modalType, setModalType] = useState<'create' | 'edit'>('create');
  const [currentCredential, setCurrentCredential] = useState<Credential | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState<boolean>(false);
  const [credentialTypeFilter, setCredentialTypeFilter] = useState<string | null>(null);
  const [createModalVisible, setCreateModalVisible] = useState<boolean>(false);
  const [selectedCredentialType, setSelectedCredentialType] = useState<CredentialType | null>(null);
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showPassword, setShowPassword] = useState<{ [key: number]: boolean }>({});
  const [testWindowsModalVisible, setTestWindowsModalVisible] = useState<boolean>(false);
  const [testWindowsLoading, setTestWindowsLoading] = useState<boolean>(false);
  const [testWindowsCredential, setTestWindowsCredential] = useState<Credential | null>(null);
  const [testWindowsForm] = Form.useForm();
  const [credentialTypes] = useState([
    { value: 'ssh', label: 'SSH密钥', icon: <KeyOutlined /> },
    { value: 'password', label: '密码', icon: <LockOutlined /> },
    { value: 'api', label: 'API密钥', icon: <SafetyCertificateOutlined /> },
    { value: 'database', label: '数据库', icon: <DatabaseOutlined /> },
    { value: 'cloud', label: '云服务', icon: <CloudServerOutlined /> }
  ]);

  // 加载凭证数据
  const fetchCredentials = async () => {
    setLoading(true);
    try {
      let url = '/device/credential/';
      if (credentialTypeFilter) {
        url += `?credential_type=${credentialTypeFilter}`;
      }
      const response = await request.get(url);
      setCredentials(response.data);
    } catch (error) {
      console.error('获取凭证列表失败:', error);
      message.error('获取凭证列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 页面加载时获取凭证列表
  useEffect(() => {
    fetchCredentials();
  }, [credentialTypeFilter]);

  // 打开选择凭证类型模态框
  const showCreateTypeModal = () => {
    setCreateModalVisible(true);
  };

  // 处理凭证类型选择
  const handleCredentialTypeSelect = (type: CredentialType) => {
    setSelectedCredentialType(type);
    setCreateModalVisible(false);
    
    // 重置表单并打开创建模态框
    form.resetFields();
    form.setFieldsValue({
      credential_type: type
    });
    setModalType('create');
    setCurrentCredential(null);
    setModalVisible(true);
  };

  // 打开编辑凭证模态框
  const showEditModal = (record: Credential) => {
    setModalType('edit');
    setCurrentCredential(record);
    form.setFieldsValue({
      name: record.name,
      description: record.description,
      credential_type: record.credential_type,
      username: record.username,
      api_key: record.api_key,
      api_vendor: record.api_vendor,
      api_secret: '', // 出于安全考虑，不预填密码和密钥
      private_key: record.private_key,
      passphrase: '',
      domain: record.domain
    });
    setModalVisible(true);
  };

  // 显示凭证详情
  const showDetailModal = (record: Credential) => {
    setCurrentCredential(record);
    setDetailModalVisible(true);
  };

  // 处理模态框取消
  const handleCancel = () => {
    setModalVisible(false);
    form.resetFields();
  };

  // 处理凭证类型选择模态框取消
  const handleCreateModalCancel = () => {
    setCreateModalVisible(false);
    setSelectedCredentialType(null);
  };

  // 处理凭证创建/编辑提交
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (modalType === 'create') {
        // 创建凭证
        let url = '';
        switch (values.credential_type) {
          case CredentialType.SSH_PASSWORD:
            url = '/device/credential/ssh-password';
            break;
          case CredentialType.API_KEY:
            url = '/device/credential/api-key';
            break;
          case CredentialType.WINDOWS_DOMAIN:
            url = '/device/credential/windows-domain';
            await request.post(url, {
              name: values.name,
              description: values.description,
              username: values.username,
              password: values.password,
              domain: values.domain
            });
            message.success('凭证创建成功');
            setModalVisible(false);
            form.resetFields();
            fetchCredentials();
            return;
        }
        if (url) {
          await request.post(url, values);
          message.success('凭证创建成功');
        }
      } else if (modalType === 'edit' && currentCredential) {
        // 编辑凭证
        // 仅发送更改的字段
        const updateData: any = {};
        for (const key in values) {
          if (values[key] !== undefined && values[key] !== '') {
            updateData[key] = values[key];
          }
        }
        
        await request.put(`/device/credential/${currentCredential.id}`, updateData);
        message.success('凭证更新成功');
      }
      
      setModalVisible(false);
      form.resetFields();
      fetchCredentials();
    } catch (error: any) {
      console.error('提交凭证失败:', error);
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  // 处理凭证删除
  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/device/credential/${id}`);
      message.success('凭证删除成功');
      fetchCredentials();
    } catch (error) {
      console.error('删除凭证失败:', error);
      message.error('删除凭证失败');
    }
  };

  // Windows/域控凭证测试连接
  const handleTestWindowsCredential = async () => {
    if (!testWindowsCredential) return;
    try {
      const values = await testWindowsForm.validateFields();
      setTestWindowsLoading(true);
      const res = await request.post(
        `/device/credential/${testWindowsCredential.id}/test-windows`,
        { host: values.host, port: values.port ?? 5985, use_ssl: !!values.use_ssl }
      );
      const data = res.data as { success: boolean; message: string };
      if (data.success) {
        message.success(data.message || '连接成功');
        setTestWindowsModalVisible(false);
        testWindowsForm.resetFields();
      } else {
        message.error(data.message || '连接失败');
      }
    } catch (error: any) {
      if (error?.errorFields) return;
      const msg = error?.response?.data?.detail || error?.message || '测试失败';
      message.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setTestWindowsLoading(false);
    }
  };

  // 渲染凭证类型标签
  const renderCredentialTypeTag = (type: CredentialType) => {
    switch (type) {
      case CredentialType.SSH_PASSWORD:
        return <Tag color="blue" icon={<UserOutlined />}>SSH密码凭证</Tag>;
      case CredentialType.API_KEY:
        return <Tag color="green" icon={<ApiOutlined />}>API凭证</Tag>;
      case CredentialType.SSH_KEY:
        return <Tag color="purple" icon={<KeyOutlined />}>SSH密钥凭证</Tag>;
      case CredentialType.WINDOWS_DOMAIN:
        return <Tag color="orange" icon={<CloudServerOutlined />}>Windows/域控凭证</Tag>;
      default:
        return <Tag>未知类型</Tag>;
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '凭证名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'credential_type',
      key: 'credential_type',
      render: (type: CredentialType) => renderCredentialTypeTag(type),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => formatBeijingToSecond(text),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (text: string) => formatBeijingToSecond(text),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Credential) => (
        <Space size="middle">
          <Button 
            type="text" 
            icon={<EyeOutlined />} 
            title="查看详情"
            onClick={() => showDetailModal(record)}
          />
          <Button 
            type="text" 
            icon={<EditOutlined />} 
            title="编辑"
            onClick={() => showEditModal(record)}
          />
          {record.credential_type === CredentialType.WINDOWS_DOMAIN && (
            <Button
              type="text"
              icon={<CheckCircleOutlined />}
              title="测试连接"
              onClick={() => {
                setTestWindowsCredential(record);
                testWindowsForm.setFieldsValue({ host: '', port: 5985, use_ssl: false });
                setTestWindowsModalVisible(true);
              }}
            />
          )}
          <Popconfirm
            title="确定要删除此凭证吗?"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} title="删除" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 凭证类型变更处理
  const handleCredentialTypeChange = (value: CredentialType) => {
    form.setFieldsValue({
      username: undefined,
      password: undefined,
      enable_password: undefined,
      api_key: undefined,
      api_secret: undefined,
      api_vendor: undefined,
      private_key: undefined,
      passphrase: undefined,
      domain: undefined
    });
  };

  // 渲染不同类型凭证的表单项
  const renderCredentialTypeFormItems = () => {
    const credentialType = form.getFieldValue('credential_type');
    
    switch (credentialType) {
      case CredentialType.SSH_PASSWORD:
        return (
          <>
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
              rules={[{ required: modalType === 'create', message: '请输入密码' }]}
              extra="编辑模式下，如不修改密码可留空"
            >
              <Password placeholder="请输入密码" />
            </Form.Item>
            <Form.Item
              name="enable_password"
              label="Enable密码"
              extra="适用于Cisco等网络设备的特权模式访问（可选）"
            >
              <Password placeholder="Cisco设备的Enable密码（可选）" />
            </Form.Item>
          </>
        );
      
      case CredentialType.API_KEY:
        return (
          <>
            <Form.Item name="api_vendor" label="API 类型">
              <Select placeholder="请选择 API 类型" allowClear options={API_VENDOR_OPTIONS} />
            </Form.Item>
            <Form.Item
              name="api_key"
              label="API Key"
              extra="目标接口不需要认证时可留空"
            >
              <Input placeholder="请输入API Key（不需要认证时可留空）" />
            </Form.Item>
            <Form.Item
              name="api_secret"
              label="API Secret"
              extra="编辑模式下如不修改可留空；目标不需要认证时可留空"
            >
              <Password placeholder="请输入API Secret（不需要认证时可留空）" />
            </Form.Item>
          </>
        );
      
      case CredentialType.WINDOWS_DOMAIN:
        return (
          <>
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input placeholder="Windows / 域账号" />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: modalType === 'create', message: '请输入密码' }]}
              extra="编辑模式下，如不修改密码可留空"
            >
              <Password placeholder="请输入密码" />
            </Form.Item>
            <Form.Item name="domain" label="域" extra="可选，域控时填写">
              <Input placeholder="例如：EXAMPLE" />
            </Form.Item>
          </>
        );
      
      default:
        return null;
    }
  };

  // 渲染凭证类型选择卡片
  const renderCredentialTypeCard = (type: CredentialType, title: string, icon: React.ReactNode, description: string) => (
    <Card 
      hoverable 
      style={{ height: '100%' }}
      onClick={() => handleCredentialTypeSelect(type)}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 36, marginBottom: 16 }}>{icon}</div>
        <Title level={4}>{title}</Title>
        <Text type="secondary">{description}</Text>
      </div>
    </Card>
  );

  return (
    <div className="credential-management">
      <Card>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总凭证数"
                value={credentials.length}
                prefix={<SafetyCertificateOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃凭证"
                value={credentials.filter(c => c.status === 'active').length}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="待验证"
                value={credentials.filter(c => c.status === 'pending').length}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已过期"
                value={credentials.filter(c => c.status === 'expired').length}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>

        <div style={{ marginBottom: 16 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={showCreateTypeModal}
          >
            添加凭证
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={credentials}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 凭证类型选择模态框 */}
      <Modal
        title="选择凭证类型"
        open={createModalVisible}
        onCancel={handleCreateModalCancel}
        footer={null}
        width={800}
      >
        <Row gutter={[16, 16]}>
          <Col span={8}>
            {renderCredentialTypeCard(
              CredentialType.SSH_PASSWORD,
              "SSH密码凭证",
              <UserOutlined style={{ color: '#1890ff' }} />,
              "使用用户名和密码的SSH凭证，支持Cisco设备的enable密码"
            )}
          </Col>
          <Col span={8}>
            {renderCredentialTypeCard(
              CredentialType.API_KEY,
              "API凭证",
              <ApiOutlined style={{ color: '#52c41a' }} />,
              "用于API访问的密钥凭证，支持多云/厂商类型（AWS、阿里云等）"
            )}
          </Col>
          <Col span={8}>
            {renderCredentialTypeCard(
              CredentialType.WINDOWS_DOMAIN,
              "Windows/域控凭证",
              <CloudServerOutlined style={{ color: '#fa8c16' }} />,
              "Windows 登录或域控账号密码，用于 WinRM 等场景"
            )}
          </Col>
        </Row>
        <Divider />
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            <QuestionCircleOutlined /> 选择适合您需求的凭证类型。不同的凭证类型适用于不同的设备和服务。
          </Text>
        </div>
      </Modal>

      {/* 创建/编辑凭证模态框 */}
      <Modal
        title={modalType === 'create' ? '添加凭证' : '编辑凭证'}
        open={modalVisible}
        onCancel={handleCancel}
        onOk={handleSubmit}
        width={700}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          preserve={false}
          name="credential_form"
        >
          <Form.Item
            name="credential_type"
            label="凭证类型"
            rules={[{ required: true, message: '请选择凭证类型' }]}
          >
            <Select 
              placeholder="请选择凭证类型" 
              onChange={handleCredentialTypeChange}
              disabled={modalType === 'edit'}
            >
              <Option value={CredentialType.SSH_PASSWORD}>SSH密码凭证</Option>
              <Option value={CredentialType.API_KEY}>API凭证</Option>
              <Option value={CredentialType.WINDOWS_DOMAIN}>Windows/域控凭证</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="name"
            label="凭证名称"
            rules={[{ required: true, message: '请输入凭证名称' }]}
          >
            <Input placeholder="请输入凭证名称" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={2} placeholder="请输入凭证描述（可选）" />
          </Form.Item>
          
          {renderCredentialTypeFormItems()}
        </Form>
      </Modal>

      {/* Windows/域控凭证测试连接 */}
      <Modal
        title="测试连接"
        open={testWindowsModalVisible}
        onCancel={() => { setTestWindowsModalVisible(false); testWindowsForm.resetFields(); }}
        onOk={handleTestWindowsCredential}
        confirmLoading={testWindowsLoading}
        okText="测试"
        destroyOnClose
      >
        <div style={{ marginBottom: 8 }}>
          {testWindowsCredential && (
            <Text type="secondary">使用凭证「{testWindowsCredential.name}」连接以下主机以验证账号密码是否正确。</Text>
          )}
        </div>
        <Form form={testWindowsForm} layout="vertical" initialValues={{ port: 5985, use_ssl: false }}>
          <Form.Item
            name="host"
            label="目标主机"
            rules={[{ required: true, message: '请输入主机 IP 或主机名' }]}
          >
            <Input placeholder="例如 192.168.1.1 或 dc.example.com" />
          </Form.Item>
          <Form.Item name="port" label="WinRM 端口">
            <Input type="number" placeholder="5985" />
          </Form.Item>
          <Form.Item name="use_ssl" valuePropName="checked" label="使用 HTTPS (WinRM 5986)">
            <Select options={[{ value: false, label: '否 (5985)' }, { value: true, label: '是 (5986)' }]} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 凭证详情模态框 */}
      <Modal
        title="凭证详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {currentCredential && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="凭证名称">{currentCredential.name}</Descriptions.Item>
            <Descriptions.Item label="凭证类型">
              {renderCredentialTypeTag(currentCredential.credential_type)}
            </Descriptions.Item>
            <Descriptions.Item label="描述">{currentCredential.description || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {formatBeijingToSecond(currentCredential.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {formatBeijingToSecond(currentCredential.updated_at)}
            </Descriptions.Item>
            
            {currentCredential.credential_type === CredentialType.SSH_PASSWORD && (
              <>
                <Descriptions.Item label="用户名">{currentCredential.username || '-'}</Descriptions.Item>
                <Descriptions.Item label="密码"><Tag color="red">已加密</Tag></Descriptions.Item>
                <Descriptions.Item label="Enable密码">
                  {currentCredential.enable_password ? <Tag color="red">已加密</Tag> : '-'}
                </Descriptions.Item>
              </>
            )}
            
            {currentCredential.credential_type === CredentialType.API_KEY && (
              <>
                <Descriptions.Item label="API 类型">
                  {API_VENDOR_OPTIONS.find(o => o.value === currentCredential.api_vendor)?.label || currentCredential.api_vendor || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="API Key">{currentCredential.api_key || '-'}</Descriptions.Item>
                <Descriptions.Item label="API Secret"><Tag color="red">已加密</Tag></Descriptions.Item>
              </>
            )}
            
            {currentCredential.credential_type === CredentialType.WINDOWS_DOMAIN && (
              <>
                <Descriptions.Item label="用户名">{currentCredential.username || '-'}</Descriptions.Item>
                <Descriptions.Item label="域">{currentCredential.domain || '-'}</Descriptions.Item>
                <Descriptions.Item label="密码"><Tag color="red">已加密</Tag></Descriptions.Item>
              </>
            )}
            
            {currentCredential.credential_type === CredentialType.SSH_KEY && (
              <>
                <Descriptions.Item label="用户名">{currentCredential.username || '-'}</Descriptions.Item>
                <Descriptions.Item label="私钥">
                  <Tag color="red">已加密</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="密钥密码">
                  {currentCredential.passphrase ? <Tag color="red">已加密</Tag> : '-'}
                </Descriptions.Item>
              </>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* 额外的隐藏表单，确保useForm与Form关联 */}
      <Form form={form} name="hidden_form" hidden />
    </div>
  );
};

export default CredentialManagement; 