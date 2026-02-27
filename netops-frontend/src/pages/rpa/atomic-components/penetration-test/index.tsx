import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Space,
  Typography,
  Row,
  Col,
} from 'antd';
import { ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import request from '@/utils/request';
import styles from './index.module.less';

const { Title } = Typography;
const STRIX_BASE = '/config-module/strix';

const PenetrationTest: React.FC = () => {
  const [configForm] = Form.useForm();
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);

  const fetchConfig = useCallback(async () => {
    setConfigLoading(true);
    try {
      const res = await request.get<{ config_key: string; config_value: string }[]>(
        `${STRIX_BASE}/config`
      );
      const data = res.data ?? res;
      const initial: Record<string, string> = {};
      (Array.isArray(data) ? data : []).forEach((item: { config_key: string; config_value: string }) => {
        initial[item.config_key] = item.config_value;
      });
      configForm.setFieldsValue(initial);
    } catch {
      message.error('获取配置失败');
    } finally {
      setConfigLoading(false);
    }
  }, [configForm]);

  const saveConfig = async () => {
    try {
      const values = await configForm.validateFields();
      setConfigSaving(true);
      await request.put(`${STRIX_BASE}/config`, values);
      message.success('配置已保存');
      fetchConfig();
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) message.error('请填写必填项');
      else message.error('保存失败');
    } finally {
      setConfigSaving(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <SafetyCertificateOutlined style={{ fontSize: 22, color: '#1677ff' }} />
        <Title level={4} className={styles.title}>渗透测试 token 配置</Title>
      </div>
      <Row gutter={24}>
        <Col xs={24} md={10} lg={8}>
          <Card
            loading={configLoading}
            className={styles.cardConfig}
            title="API 配置"
          >
            <Form form={configForm} layout="vertical">
              <Form.Item name="STRIX_LLM" label="LLM 模型" rules={[{ required: true }]}>
                <Input placeholder="如 openai/gpt-4、openai/gpt-4o（按实际模型填写）" />
              </Form.Item>
              <Form.Item name="LLM_API_KEY" label="API Key" rules={[{ required: true }]}>
                <Input.Password
                  placeholder="保存后脱敏展示，不可复制"
                  autoComplete="off"
                  onCopy={(e) => e.preventDefault()}
                  style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
                />
              </Form.Item>
              <Form.Item name="LLM_API_BASE" label="API 地址（可选）">
                <Input placeholder="自建/本地模型 base URL" />
              </Form.Item>
              <div className={styles.actions}>
                <Space>
                  <Button type="primary" loading={configSaving} onClick={saveConfig}>
                    保存配置
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={fetchConfig}>
                    刷新
                  </Button>
                </Space>
              </div>
            </Form>
          </Card>
        </Col>
        <Col xs={24} md={14} lg={16}>
          <Card
            className={styles.cardHelp}
            title={
              <Space>
                <span style={{ color: '#52c41a' }}>●</span>
                <span>配置说明</span>
              </Space>
            }
          >
            <Typography.Title level={5} className={styles.exampleTitle}>示例一：OpenAI GPT</Typography.Title>
            <ul className={styles.helpList}>
              <li><strong>LLM 模型</strong>：<code>openai/gpt-4</code> 或 <code>openai/gpt-4o</code>（按实际模型名填写）</li>
              <li><strong>API Key</strong>：OpenAI API Key（在 OpenAI 控制台创建）</li>
              <li><strong>LLM_API_BASE</strong>：留空（使用官方）；若走代理或自建兼容接口可填 <code>https://your-proxy/v1</code></li>
            </ul>
            <Typography.Title level={5} className={`${styles.exampleTitle} ${styles.exampleTitleMinimax}`}>示例二：Minimax</Typography.Title>
            <ul className={styles.helpList} style={{ marginBottom: 0 }}>
              <li><strong>LLM 模型</strong>：填写 Minimax 模型标识，如 <code>minimax/abab6.5s</code>（以厂商文档为准）</li>
              <li><strong>API Key</strong>：Minimax API Key（在 Minimax 开放平台申请）</li>
              <li><strong>LLM_API_BASE</strong>：Minimax API 地址，如 <code>https://api.minimax.chat/v1</code></li>
            </ul>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PenetrationTest;
