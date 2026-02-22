import React, { useState } from 'react';
import {
  Card, Table, Button, Typography, Modal, Form, Input, Select, InputNumber, Row, Space, message, Spin,
} from 'antd';
import { LoadingOutlined, DatabaseOutlined } from '@ant-design/icons';
import request from '../../utils/request';
import './Discovery.css';

const { Title, Text } = Typography;
const { Option } = Select;

// Simple Icons CDN 真实品牌 Logo
const SIMPLE_ICONS_CDN = 'https://cdn.simpleicons.org';

// 发现类型配置项
interface DiscoveryTypeRecord {
  key: string;
  title: string;
  description: string;
  slug: string | null;
  color: string;
}

// 发现类型单元格：带品牌 logo（CDN）+ 加载失败时回退为图标
const DiscoveryTypeCell: React.FC<{ record: DiscoveryTypeRecord }> = ({ record }) => {
  const [logoFailed, setLogoFailed] = useState(false);
  const showImg = record.slug && !logoFailed;
  return (
    <Space align="center">
      <span className="discovery-type-icon">
        {showImg ? (
          <img
            src={`${SIMPLE_ICONS_CDN}/${record.slug}/${record.color}`}
            alt=""
            className="discovery-table-logo"
            onError={() => setLogoFailed(true)}
          />
        ) : (
          <DatabaseOutlined style={{ color: `#${record.color}` }} />
        )}
      </span>
      <Text strong>{record.title}</Text>
    </Space>
  );
};

// 设备发现类型配置：slug 用于 CDN logo，无则用 null 显示 Ant Design 图标
const discoveryTypes: DiscoveryTypeRecord[] = [
  { key: 'cisco-campus', title: 'Cisco园区网络设备发现', description: '发现Cisco园区网络设备，包括交换机、路由器等', slug: 'cisco', color: '049fd9' },
  { key: 'cisco-datacenter', title: 'Cisco数据中心网络设备发现', description: '发现Cisco数据中心网络设备，包括Nexus系列交换机等', slug: 'cisco', color: '049fd9' },
  { key: 'huawei', title: '华为网络设备发现', description: '发现华为网络设备，包括交换机、路由器等', slug: 'huawei', color: 'e60012' },
  { key: 'h3c', title: 'H3C网络设备发现', description: '发现H3C网络设备，包括交换机、路由器等', slug: null, color: '0066b3' },
  { key: 'ruijie', title: '锐捷网络设备发现', description: '发现锐捷网络设备，包括交换机、路由器等', slug: null, color: 'e60012' },
  { key: 'paloalto', title: 'PaloAlto安全设备发现', description: '发现PaloAlto安全设备，包括防火墙等', slug: 'paloaltonetworks', color: 'fa582d' },
  { key: 'fortinet', title: '飞塔安全设备发现', description: '发现飞塔(Fortinet)安全设备，包括防火墙等', slug: 'fortinet', color: 'ee3124' },
  { key: 'vmware', title: 'VMware设备发现', description: '发现VMware虚拟化环境中的设备', slug: 'vmware', color: '607078' },
  { key: 'aws', title: 'AWS设备发现', description: '发现AWS云环境中的设备和资源', slug: 'amazonaws', color: 'ff9900' },
  { key: 'aliyun', title: '阿里云设备发现', description: '发现阿里云环境中的设备和资源', slug: 'alibabacloud', color: 'ff6a00' },
];

/**
 * 设备发现组件（风格与 CMDB 模型管理、资产盘点一致：Card + Table）
 */
const CMDBDiscovery: React.FC = () => {
  const [discoveryModalVisible, setDiscoveryModalVisible] = useState<boolean>(false);
  const [currentDiscoveryType, setCurrentDiscoveryType] = useState<string>('');
  const [discoveryForm] = Form.useForm();
  const [discovering, setDiscovering] = useState<boolean>(false);

  const openDiscoveryModal = (type: string) => {
    setCurrentDiscoveryType(type);
    discoveryForm.resetFields();
    setDiscoveryModalVisible(true);
  };

  const handleDiscovery = async (values: any) => {
    setDiscovering(true);
    try {
      const discoveryParams = { ...values, discovery_type: currentDiscoveryType };
      const response = await request.post('cmdb/discovery', discoveryParams);
      if (response.data?.success) {
        message.success(`成功发现 ${response.data.discovered_count ?? 0} 台设备`);
        setDiscoveryModalVisible(false);
      } else {
        message.error(response.data?.message || '设备发现失败');
      }
    } catch (error) {
      console.error('设备发现失败:', error);
      message.error('设备发现失败，请检查网络连接和参数设置');
    } finally {
      setDiscovering(false);
    }
  };

  const getFormFields = () => {
    const commonFields = (
      <>
        <Form.Item name="ip_range" label="IP范围" rules={[{ required: true, message: '请输入IP范围' }]}>
          <Input placeholder="例如: 192.168.1.0/24 或 192.168.1.1-192.168.1.254" />
        </Form.Item>
        <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
          <Input placeholder="请输入用户名" />
        </Form.Item>
        <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
          <Input.Password placeholder="请输入密码" />
        </Form.Item>
        <Form.Item name="port" label="端口" initialValue={22}>
          <InputNumber min={1} max={65535} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="timeout" label="超时时间(秒)" initialValue={30}>
          <InputNumber min={5} max={300} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="threads" label="并发线程数" initialValue={10}>
          <InputNumber min={1} max={50} style={{ width: '100%' }} />
        </Form.Item>
      </>
    );

    switch (currentDiscoveryType) {
      case 'aws':
        return (
          <>
            <Form.Item name="access_key" label="Access Key" rules={[{ required: true }]}>
              <Input placeholder="请输入AWS Access Key" />
            </Form.Item>
            <Form.Item name="secret_key" label="Secret Key" rules={[{ required: true }]}>
              <Input.Password placeholder="请输入AWS Secret Key" />
            </Form.Item>
            <Form.Item name="region" label="区域" rules={[{ required: true }]}>
              <Select placeholder="请选择区域">
                <Option value="us-east-1">美国东部(弗吉尼亚北部)</Option>
                <Option value="us-west-2">美国西部(俄勒冈)</Option>
                <Option value="ap-northeast-1">亚太地区(东京)</Option>
                <Option value="ap-southeast-1">亚太地区(新加坡)</Option>
                <Option value="eu-central-1">欧洲(法兰克福)</Option>
              </Select>
            </Form.Item>
          </>
        );
      case 'aliyun':
        return (
          <>
            <Form.Item name="access_key" label="Access Key" rules={[{ required: true }]}>
              <Input placeholder="请输入阿里云Access Key" />
            </Form.Item>
            <Form.Item name="secret_key" label="Secret Key" rules={[{ required: true }]}>
              <Input.Password placeholder="请输入阿里云Secret Key" />
            </Form.Item>
            <Form.Item name="region" label="区域" rules={[{ required: true }]}>
              <Select placeholder="请选择区域">
                <Option value="cn-hangzhou">华东1(杭州)</Option>
                <Option value="cn-shanghai">华东2(上海)</Option>
                <Option value="cn-beijing">华北2(北京)</Option>
                <Option value="cn-shenzhen">华南1(深圳)</Option>
                <Option value="cn-hongkong">中国香港</Option>
              </Select>
            </Form.Item>
          </>
        );
      case 'vmware':
        return (
          <>
            <Form.Item name="vcenter_host" label="vCenter主机" rules={[{ required: true }]}>
              <Input placeholder="例如: vcenter.example.com" />
            </Form.Item>
            <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
              <Input placeholder="请输入vCenter用户名" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true }]}>
              <Input.Password placeholder="请输入vCenter密码" />
            </Form.Item>
            <Form.Item name="port" label="端口" initialValue={443}>
              <InputNumber min={1} max={65535} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="verify_ssl" label="验证SSL证书" initialValue={false}>
              <Select>
                <Option value={true}>是</Option>
                <Option value={false}>否</Option>
              </Select>
            </Form.Item>
          </>
        );
      default:
        return commonFields;
    }
  };

  const getModalTitle = () => {
    const t = discoveryTypes.find((type) => type.key === currentDiscoveryType);
    return t ? t.title : '设备发现';
  };

  const columns = [
    {
      title: '发现类型',
      key: 'type',
      width: 280,
      render: (_: unknown, record: DiscoveryTypeRecord) => <DiscoveryTypeCell record={record} />,
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: typeof discoveryTypes[0]) => (
        <Button type="primary" size="small" onClick={() => openDiscoveryModal(record.key)}>
          开始发现
        </Button>
      ),
    },
  ];

  return (
    <div className="cmdb-discovery-page">
      <Card title="设备发现" className="discovery-card">
        <Title level={5}>发现类型</Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          选择设备类型，配置发现参数，自动发现网络中的设备并添加到CMDB资产库
        </Text>
        <Table
          columns={columns}
          dataSource={discoveryTypes}
          rowKey="key"
          pagination={false}
        />
      </Card>

      <Modal
        title={getModalTitle()}
        open={discoveryModalVisible}
        onCancel={() => setDiscoveryModalVisible(false)}
        footer={null}
        width={560}
        destroyOnClose
      >
        <Spin spinning={discovering} indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />}>
          <Form form={discoveryForm} layout="vertical" onFinish={handleDiscovery}>
            {getFormFields()}
            <Form.Item>
              <Row justify="end">
                <Space>
                  <Button onClick={() => setDiscoveryModalVisible(false)}>取消</Button>
                  <Button type="primary" htmlType="submit" loading={discovering}>
                    开始发现
                  </Button>
                </Space>
              </Row>
            </Form.Item>
          </Form>
        </Spin>
      </Modal>
    </div>
  );
};

export default CMDBDiscovery;
