import React, { useState, useEffect, useCallback } from 'react';
import { Card, Form, Input, Button, message, Typography } from 'antd';
import { ApiOutlined } from '@ant-design/icons';
import request from '../../utils/request';

const { Title, Text } = Typography;

interface ConfigItem {
  config_key: string;
  config_value: string;
  updated_at?: string;
}

const GlobalConfig: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await request.get<ConfigItem[]>('/system/global-config');
      const data = Array.isArray(res.data) ? res.data : [];
      const initial: Record<string, string> = {};
      data.forEach((item: ConfigItem) => {
        initial[item.config_key] = item.config_value;
      });
      form.setFieldsValue(initial);
    } catch {
      message.error('获取配置失败');
    } finally {
      setLoading(false);
    }
  }, [form]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const onFinish = async (values: Record<string, string>) => {
    setSaving(true);
    try {
      await request.put('/system/global-config', values);
      message.success('保存成功');
      fetchConfig();
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Title level={4}>
        <ApiOutlined /> OpenAPI-Key 配置
      </Title>
      <Card style={{ marginBottom: 16 }}>
        <Text type="secondary">
          统一格式：模型名称、API Key、API Base。兼容 OpenAI、Minimax、DeepSeek、Claude 等（填写对应厂商的 Key 与 Base 即可）。Base 留空时默认使用 OpenAI 官方地址。
        </Text>
      </Card>
      <Card loading={loading}>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="GLOBAL_LLM_MODEL" label="模型名称" extra="如 gpt-4o-mini、gpt-4o、deepseek-chat、claude-3-5-sonnet 等，按厂商文档填写">
            <Input placeholder="gpt-4o-mini" />
          </Form.Item>
          <Form.Item name="GLOBAL_LLM_API_KEY" label="API Key" extra="保存后脱敏展示，仅后端使用">
            <Input.Password
              placeholder="sk-..."
              autoComplete="off"
              onCopy={(e) => e.preventDefault()}
              style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
            />
          </Form.Item>
          <Form.Item name="GLOBAL_LLM_API_BASE" label="API Base（可选）" extra="留空默认 https://api.openai.com/v1；自建或 Minimax/DeepSeek 等填厂商地址">
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存
            </Button>
            <Button style={{ marginLeft: 8 }} onClick={fetchConfig}>
              刷新
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default GlobalConfig;
