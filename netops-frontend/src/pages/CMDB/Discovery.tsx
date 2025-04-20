import React, { useState } from 'react';
import { Card, Row, Col, Typography, Button, Modal, Form, Input, Select, InputNumber, Space, message, Spin } from 'antd';
import {
  ApiOutlined, CloudOutlined, SafetyCertificateOutlined, 
  DesktopOutlined, GlobalOutlined, AmazonOutlined, 
  AliyunOutlined, LoadingOutlined
} from '@ant-design/icons';
import request from '../../utils/request';
import './Discovery.css';

const { Title, Text } = Typography;
const { Option } = Select;

// 自定义图标组件
const CiscoIcon = () => (
  <div className="custom-icon cisco-icon">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12,2C6.5,2,2,6.5,2,12s4.5,10,10,10s10-4.5,10-10S17.5,2,12,2z M12,20c-4.4,0-8-3.6-8-8s3.6-8,8-8s8,3.6,8,8 S16.4,20,12,20z M16,11h-3V8c0-0.6-0.4-1-1-1s-1,0.4-1,1v3H8c-0.6,0-1,0.4-1,1s0.4,1,1,1h3v3c0,0.6,0.4,1,1,1s1-0.4,1-1v-3h3 c0.6,0,1-0.4,1-1S16.6,11,16,11z"/>
    </svg>
  </div>
);

const HuaweiIcon = () => (
  <div className="custom-icon huawei-icon">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12,2C6.5,2,2,6.5,2,12s4.5,10,10,10s10-4.5,10-10S17.5,2,12,2z M12,20c-4.4,0-8-3.6-8-8s3.6-8,8-8s8,3.6,8,8 S16.4,20,12,20z M15.5,8.5c-0.4-0.4-1-0.4-1.4,0L12,10.6L9.9,8.5c-0.4-0.4-1-0.4-1.4,0s-0.4,1,0,1.4l2.1,2.1l-2.1,2.1 c-0.4,0.4-0.4,1,0,1.4c0.2,0.2,0.5,0.3,0.7,0.3s0.5-0.1,0.7-0.3l2.1-2.1l2.1,2.1c0.2,0.2,0.5,0.3,0.7,0.3s0.5-0.1,0.7-0.3 c0.4-0.4,0.4-1,0-1.4L13.4,12l2.1-2.1C15.9,9.5,15.9,8.9,15.5,8.5z"/>
    </svg>
  </div>
);

const H3CIcon = () => (
  <div className="custom-icon h3c-icon">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M4,4h4v4H4V4z M4,10h4v4H4V10z M4,16h4v4H4V16z M10,4h4v4h-4V4z M10,10h4v4h-4V10z M10,16h4v4h-4V16z M16,4h4v4h-4V4z M16,10h4v4h-4V10z M16,16h4v4h-4V16z"/>
    </svg>
  </div>
);

const RuijieIcon = () => (
  <div className="custom-icon ruijie-icon">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12,2C6.5,2,2,6.5,2,12s4.5,10,10,10s10-4.5,10-10S17.5,2,12,2z M12,20c-4.4,0-8-3.6-8-8s3.6-8,8-8s8,3.6,8,8 S16.4,20,12,20z M8,13h8v-2H8V13z"/>
    </svg>
  </div>
);

const PaloAltoIcon = () => (
  <div className="custom-icon paloalto-icon">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12,2C6.5,2,2,6.5,2,12s4.5,10,10,10s10-4.5,10-10S17.5,2,12,2z M12,20c-4.4,0-8-3.6-8-8s3.6-8,8-8s8,3.6,8,8 S16.4,20,12,20z M12,7c-2.8,0-5,2.2-5,5s2.2,5,5,5s5-2.2,5-5S14.8,7,12,7z"/>
    </svg>
  </div>
);

const VMwareIcon = () => (
  <div className="custom-icon vmware-icon">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M2,17h4v4H2V17z M8,17h4v4H8V17z M14,17h4v4h-4V17z M20,17h2v4h-2V17z M2,11h4v4H2V11z M8,11h4v4H8V11z M14,11h4v4h-4V11z M20,11h2v4h-2V11z M2,3h4v6H2V3z M8,3h4v6H8V3z M14,3h4v6h-4V3z M20,3h2v6h-2V3z"/>
    </svg>
  </div>
);

/**
 * 设备发现组件
 */
const CMDBDiscovery: React.FC = () => {
  const [discoveryModalVisible, setDiscoveryModalVisible] = useState<boolean>(false);
  const [currentDiscoveryType, setCurrentDiscoveryType] = useState<string>('');
  const [discoveryForm] = Form.useForm();
  const [discovering, setDiscovering] = useState<boolean>(false);

  // 设备发现类型配置
  const discoveryTypes = [
    {
      key: 'cisco-campus',
      title: 'Cisco园区网络设备发现',
      icon: <CiscoIcon />,
      description: '发现Cisco园区网络设备，包括交换机、路由器等',
      color: '#049fd9'
    },
    {
      key: 'cisco-datacenter',
      title: 'Cisco数据中心网络设备发现',
      icon: <CiscoIcon />,
      description: '发现Cisco数据中心网络设备，包括Nexus系列交换机等',
      color: '#049fd9'
    },
    {
      key: 'huawei',
      title: '华为网络设备发现',
      icon: <HuaweiIcon />,
      description: '发现华为网络设备，包括交换机、路由器等',
      color: '#e60012'
    },
    {
      key: 'h3c',
      title: 'H3C网络设备发现',
      icon: <H3CIcon />,
      description: '发现H3C网络设备，包括交换机、路由器等',
      color: '#0066b3'
    },
    {
      key: 'ruijie',
      title: '锐捷网络设备发现',
      icon: <RuijieIcon />,
      description: '发现锐捷网络设备，包括交换机、路由器等',
      color: '#e60012'
    },
    {
      key: 'paloalto',
      title: 'PaloAlto安全设备发现',
      icon: <PaloAltoIcon />,
      description: '发现PaloAlto安全设备，包括防火墙等',
      color: '#fa582d'
    },
    {
      key: 'vmware',
      title: 'VMware设备发现',
      icon: <VMwareIcon />,
      description: '发现VMware虚拟化环境中的设备',
      color: '#607078'
    },
    {
      key: 'aws',
      title: 'AWS设备发现',
      icon: <AmazonOutlined />,
      description: '发现AWS云环境中的设备和资源',
      color: '#ff9900'
    },
    {
      key: 'aliyun',
      title: '阿里云设备发现',
      icon: <AliyunOutlined />,
      description: '发现阿里云环境中的设备和资源',
      color: '#ff6a00'
    }
  ];

  // 打开设备发现模态框
  const openDiscoveryModal = (type: string) => {
    setCurrentDiscoveryType(type);
    discoveryForm.resetFields();
    setDiscoveryModalVisible(true);
  };

  // 处理设备发现
  const handleDiscovery = async (values: any) => {
    setDiscovering(true);
    try {
      // 根据不同的发现类型构建不同的请求参数
      const discoveryParams = {
        ...values,
        discovery_type: currentDiscoveryType
      };
      
      // 发送设备发现请求
      const response = await request.post('/api/cmdb/discovery', discoveryParams);
      
      if (response.data.success) {
        message.success(`成功发现 ${response.data.discovered_count || 0} 台设备`);
        setDiscoveryModalVisible(false);
      } else {
        message.error(response.data.message || '设备发现失败');
      }
    } catch (error) {
      console.error('设备发现失败:', error);
      message.error('设备发现失败，请检查网络连接和参数设置');
    } finally {
      setDiscovering(false);
    }
  };

  // 获取当前发现类型的表单字段
  const getFormFields = () => {
    // 通用字段
    const commonFields = (
      <>
        <Form.Item
          name="ip_range"
          label="IP范围"
          rules={[{ required: true, message: '请输入IP范围' }]}
        >
          <Input placeholder="例如: 192.168.1.0/24 或 192.168.1.1-192.168.1.254" />
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
          name="port"
          label="端口"
          initialValue={22}
        >
          <InputNumber min={1} max={65535} style={{ width: '100%' }} />
        </Form.Item>
        
        <Form.Item
          name="timeout"
          label="超时时间(秒)"
          initialValue={30}
        >
          <InputNumber min={5} max={300} style={{ width: '100%' }} />
        </Form.Item>
        
        <Form.Item
          name="threads"
          label="并发线程数"
          initialValue={10}
        >
          <InputNumber min={1} max={50} style={{ width: '100%' }} />
        </Form.Item>
      </>
    );

    // 根据不同的发现类型返回不同的表单字段
    switch (currentDiscoveryType) {
      case 'aws':
        return (
          <>
            <Form.Item
              name="access_key"
              label="Access Key"
              rules={[{ required: true, message: '请输入Access Key' }]}
            >
              <Input placeholder="请输入AWS Access Key" />
            </Form.Item>
            
            <Form.Item
              name="secret_key"
              label="Secret Key"
              rules={[{ required: true, message: '请输入Secret Key' }]}
            >
              <Input.Password placeholder="请输入AWS Secret Key" />
            </Form.Item>
            
            <Form.Item
              name="region"
              label="区域"
              rules={[{ required: true, message: '请选择区域' }]}
            >
              <Select placeholder="请选择区域">
                <Option value="us-east-1">美国东部(弗吉尼亚北部)</Option>
                <Option value="us-east-2">美国东部(俄亥俄)</Option>
                <Option value="us-west-1">美国西部(加利福尼亚北部)</Option>
                <Option value="us-west-2">美国西部(俄勒冈)</Option>
                <Option value="ap-east-1">亚太地区(香港)</Option>
                <Option value="ap-south-1">亚太地区(孟买)</Option>
                <Option value="ap-northeast-1">亚太地区(东京)</Option>
                <Option value="ap-northeast-2">亚太地区(首尔)</Option>
                <Option value="ap-southeast-1">亚太地区(新加坡)</Option>
                <Option value="ap-southeast-2">亚太地区(悉尼)</Option>
                <Option value="ca-central-1">加拿大(中部)</Option>
                <Option value="eu-central-1">欧洲(法兰克福)</Option>
                <Option value="eu-west-1">欧洲(爱尔兰)</Option>
                <Option value="eu-west-2">欧洲(伦敦)</Option>
                <Option value="eu-west-3">欧洲(巴黎)</Option>
                <Option value="eu-north-1">欧洲(斯德哥尔摩)</Option>
                <Option value="sa-east-1">南美洲(圣保罗)</Option>
              </Select>
            </Form.Item>
          </>
        );
      case 'aliyun':
        return (
          <>
            <Form.Item
              name="access_key"
              label="Access Key"
              rules={[{ required: true, message: '请输入Access Key' }]}
            >
              <Input placeholder="请输入阿里云Access Key" />
            </Form.Item>
            
            <Form.Item
              name="secret_key"
              label="Secret Key"
              rules={[{ required: true, message: '请输入Secret Key' }]}
            >
              <Input.Password placeholder="请输入阿里云Secret Key" />
            </Form.Item>
            
            <Form.Item
              name="region"
              label="区域"
              rules={[{ required: true, message: '请选择区域' }]}
            >
              <Select placeholder="请选择区域">
                <Option value="cn-hangzhou">华东1(杭州)</Option>
                <Option value="cn-shanghai">华东2(上海)</Option>
                <Option value="cn-qingdao">华北1(青岛)</Option>
                <Option value="cn-beijing">华北2(北京)</Option>
                <Option value="cn-zhangjiakou">华北3(张家口)</Option>
                <Option value="cn-huhehaote">华北5(呼和浩特)</Option>
                <Option value="cn-wulanchabu">华北6(乌兰察布)</Option>
                <Option value="cn-shenzhen">华南1(深圳)</Option>
                <Option value="cn-heyuan">华南2(河源)</Option>
                <Option value="cn-guangzhou">华南3(广州)</Option>
                <Option value="cn-chengdu">西南1(成都)</Option>
                <Option value="cn-hongkong">中国香港</Option>
              </Select>
            </Form.Item>
          </>
        );
      case 'vmware':
        return (
          <>
            <Form.Item
              name="vcenter_host"
              label="vCenter主机"
              rules={[{ required: true, message: '请输入vCenter主机地址' }]}
            >
              <Input placeholder="例如: vcenter.example.com" />
            </Form.Item>
            
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input placeholder="请输入vCenter用户名" />
            </Form.Item>
            
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password placeholder="请输入vCenter密码" />
            </Form.Item>
            
            <Form.Item
              name="port"
              label="端口"
              initialValue={443}
            >
              <InputNumber min={1} max={65535} style={{ width: '100%' }} />
            </Form.Item>
            
            <Form.Item
              name="verify_ssl"
              label="验证SSL证书"
              initialValue={false}
            >
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

  // 获取模态框标题
  const getModalTitle = () => {
    const discoveryType = discoveryTypes.find(type => type.key === currentDiscoveryType);
    return discoveryType ? discoveryType.title : '设备发现';
  };

  return (
    <div className="cmdb-discovery-page">
      <Title level={2}>设备发现</Title>
      <Text type="secondary" style={{ marginBottom: 24, display: 'block' }}>
        选择设备类型，配置发现参数，自动发现网络中的设备并添加到CMDB资产库
      </Text>
      
      <Row gutter={[16, 16]}>
        {discoveryTypes.map(type => (
          <Col xs={24} sm={12} md={8} lg={8} xl={8} key={type.key}>
            <Card 
              hoverable 
              className="discovery-card"
              onClick={() => openDiscoveryModal(type.key)}
              style={{ borderTop: `2px solid ${type.color}` }}
            >
              <div className="discovery-card-content">
                <div className="discovery-card-icon" style={{ color: type.color }}>
                  {type.icon}
                </div>
                <div className="discovery-card-info">
                  <div className="discovery-card-title">{type.title}</div>
                  <div className="discovery-card-description">{type.description}</div>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 设备发现模态框 */}
      <Modal
        title={getModalTitle()}
        open={discoveryModalVisible}
        onCancel={() => setDiscoveryModalVisible(false)}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Spin spinning={discovering} indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />}>
          <Form
            form={discoveryForm}
            layout="vertical"
            onFinish={handleDiscovery}
          >
            {getFormFields()}
            
            <Form.Item>
              <Row justify="end">
                <Space>
                  <Button onClick={() => setDiscoveryModalVisible(false)}>
                    取消
                  </Button>
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