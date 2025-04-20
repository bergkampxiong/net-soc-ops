import React from 'react';
import { Modal, Form, Input, Select, InputNumber, Row, Col, Tooltip } from 'antd';
import { createApiConfig, updateApiConfig, ApiConfig } from '../../../../services/apiConfig';

const { Option } = Select;
const { TextArea } = Input;

interface ApiConfigModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: () => void;
  initialValues?: ApiConfig;
}

const apiTypes = [
  { label: 'REST API', value: 'REST' },
  { label: 'NETCONF', value: 'NETCONF' },
  { label: 'YANG', value: 'YANG' },
  { label: 'gRPC', value: 'gRPC' },
];

const authTypes = [
  { label: 'Basic Auth', value: 'Basic' },
  { label: 'Token', value: 'Token' },
  { label: 'OAuth', value: 'OAuth' },
];

const ApiConfigModal: React.FC<ApiConfigModalProps> = ({
  visible,
  onCancel,
  onSuccess,
  initialValues,
}) => {
  const [form] = Form.useForm();

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // 处理请求头
      const headers = values.headers
        ? values.headers.split('\n').reduce((acc: Record<string, string>, line: string) => {
            const [key, value] = line.split(':').map(str => str.trim());
            if (key && value) {
              acc[key] = value;
            }
            return acc;
          }, {})
        : {};

      const apiConfig = {
        ...values,
        headers,
      };

      if (initialValues) {
        await updateApiConfig(initialValues.id, apiConfig);
      } else {
        await createApiConfig(apiConfig);
      }

      form.resetFields();
      onSuccess();
    } catch (error) {
      console.error('提交失败:', error);
    }
  };

  return (
    <Modal
      title={initialValues ? '编辑API配置' : '添加API配置'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={700}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={initialValues || {
          timeout: 30,
          headers: '',
        }}
      >
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item
              name="name"
              label="配置名称"
              rules={[{ required: true, message: '请输入配置名称' }]}
            >
              <Input placeholder="请输入配置名称" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="type"
              label="API类型"
              rules={[{ required: true, message: '请选择API类型' }]}
            >
              <Select placeholder="请选择API类型">
                {apiTypes.map(type => (
                  <Option key={type.value} value={type.value}>{type.label}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>
        <Form.Item
          name="endpoint"
          label="API端点"
          rules={[{ required: true, message: '请输入API端点' }]}
        >
          <Input placeholder="请输入API端点地址" />
        </Form.Item>
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item
              name="auth_type"
              label="认证方式"
              rules={[{ required: true, message: '请选择认证方式' }]}
            >
              <Select placeholder="请选择认证方式">
                {authTypes.map(type => (
                  <Option key={type.value} value={type.value}>{type.label}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="timeout"
              label="超时时间(秒)"
              rules={[{ required: true, message: '请输入超时时间' }]}
            >
              <InputNumber min={1} max={300} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item
          name="headers"
          label="请求头"
        >
          <Tooltip title="每行一个请求头，格式为 key: value">
            <TextArea
              placeholder="Content-Type: application/json&#13;Accept: application/json"
              autoSize={{ minRows: 3, maxRows: 6 }}
            />
          </Tooltip>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ApiConfigModal; 