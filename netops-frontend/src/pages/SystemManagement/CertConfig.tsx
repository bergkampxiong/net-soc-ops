import React, { useState, useEffect, useCallback } from 'react';
import {
  Card, Form, InputNumber, Switch, Button, message, Typography, Radio, Upload, Alert,
} from 'antd';
import { SafetyCertificateOutlined, UploadOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import request from '../../utils/request';

const { Title, Text } = Typography;

type CertMode = 'self_signed' | 'ca_import';

interface CertConfigData {
  cert_mode: CertMode;
  validity_days: number | null;
  enable_https: boolean;
  has_ca_cert: boolean;
}

const CertConfig: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [certMode, setCertMode] = useState<CertMode>('self_signed');
  const [certFileList, setCertFileList] = useState<UploadFile[]>([]);
  const [keyFileList, setKeyFileList] = useState<UploadFile[]>([]);
  const [certFileContent, setCertFileContent] = useState<string>('');
  const [keyFileContent, setKeyFileContent] = useState<string>('');

  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await request.get<CertConfigData>('/system/cert-config');
      const data = res.data as CertConfigData;
      form.setFieldsValue({
        cert_mode: data.cert_mode || 'self_signed',
        validity_days: data.validity_days ?? 3650,
        enable_https: data.enable_https ?? false,
      });
      setCertMode((data.cert_mode as CertMode) || 'self_signed');
    } catch {
      message.error('获取证书配置失败');
    } finally {
      setLoading(false);
    }
  }, [form]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const readFileAsText = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(String(r.result));
      r.onerror = () => reject(new Error('读取文件失败'));
      r.readAsText(file, 'utf-8');
    });

  const onFinish = async (values: Record<string, unknown>) => {
    setSaving(true);
    try {
      const mode = (values.cert_mode as CertMode) || 'self_signed';
      const payload: Record<string, unknown> = {
        cert_mode: mode,
        enable_https: !!values.enable_https,
      };
      if (mode === 'self_signed') {
        payload.validity_days = values.validity_days ?? 3650;
        const res = await request.put<{ ok: boolean; message?: string }>('/system/cert-config', payload);
        message.success(res.data?.message || '保存成功，请重启前端服务使 HTTPS 生效。');
      } else {
        if (!certFileContent.trim() || !keyFileContent.trim()) {
          message.error('请选择并读取证书文件与私钥文件');
          setSaving(false);
          return;
        }
        payload.cert_pem = certFileContent;
        payload.key_pem = keyFileContent;
        const res = await request.put<{ ok: boolean; message?: string }>('/system/cert-config', payload);
        message.success(res.data?.message || '保存成功，请重启前端服务使 HTTPS 生效。');
      }
      fetchConfig();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '保存失败';
      message.error(Array.isArray(msg) ? msg.join(' ') : msg);
    } finally {
      setSaving(false);
    }
  };

  const handleCertFile = async (file: File) => {
    const text = await readFileAsText(file);
    setCertFileContent(text);
    setCertFileList([{ uid: '-1', name: file.name, status: 'done', originFileObj: file as any }]);
    return false; // 阻止自动上传，仅本地读取
  };
  const handleKeyFile = async (file: File) => {
    const text = await readFileAsText(file);
    setKeyFileContent(text);
    setKeyFileList([{ uid: '-1', name: file.name, status: 'done', originFileObj: file as any }]);
    return false;
  };

  return (
    <div>
      <Title level={4}>
        <SafetyCertificateOutlined /> 前端证书配置
      </Title>
      <Card style={{ marginBottom: 16 }}>
        <Text type="secondary">
          自签名：由后端生成证书并写入前端证书目录，可配置有效期，保存后请重启前端服务生效。导入 CA：上传 CA 提供的证书与私钥（PEM），保存后请重启前端服务生效。生产环境 HTTPS 请在 Nginx 等反向代理配置。
        </Text>
      </Card>
      <Card loading={loading}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ cert_mode: 'self_signed', validity_days: 3650, enable_https: false }}
        >
          <Form.Item name="cert_mode" label="证书方式">
            <Radio.Group
              optionType="button"
              options={[
                { label: '自签名证书', value: 'self_signed' },
                { label: '导入 CA 证书', value: 'ca_import' },
              ]}
              onChange={(e) => setCertMode(e.target.value)}
            />
          </Form.Item>

          {certMode === 'self_signed' && (
            <Form.Item
              name="validity_days"
              label="证书有效期（天）"
              rules={[{ required: true }, { type: 'number', min: 1, max: 36500, message: '1～36500 天' }]}
              extra="保存后将由后端生成自签名证书并写入前端证书目录，重启前端后生效。"
            >
              <InputNumber min={1} max={36500} style={{ width: 160 }} />
            </Form.Item>
          )}

          {certMode === 'ca_import' && (
            <>
              <Form.Item
                label="证书文件（PEM）"
                required
                extra="上传 CA 签发的证书（.crt/.pem）。"
              >
                <Upload
                  accept=".pem,.crt,.cer"
                  fileList={certFileList}
                  beforeUpload={handleCertFile}
                  onRemove={() => { setCertFileList([]); setCertFileContent(''); }}
                  maxCount={1}
                >
                  <Button icon={<UploadOutlined />}>选择证书文件</Button>
                </Upload>
              </Form.Item>
              <Form.Item
                label="私钥文件（PEM）"
                required
                extra="上传对应私钥（.key/.pem），请妥善保管。"
              >
                <Upload
                  accept=".pem,.key"
                  fileList={keyFileList}
                  beforeUpload={handleKeyFile}
                  onRemove={() => { setKeyFileList([]); setKeyFileContent(''); }}
                  maxCount={1}
                >
                  <Button icon={<UploadOutlined />}>选择私钥文件</Button>
                </Upload>
              </Form.Item>
            </>
          )}

          <Form.Item
            name="enable_https"
            label="启用 HTTPS"
            valuePropName="checked"
            extra="启用后需使用 REACT_APP_DEV_HTTPS=true 启动前端。"
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存并{ certMode === 'self_signed' ? '生成证书' : '写入证书' }
            </Button>
            <Button style={{ marginLeft: 8 }} onClick={fetchConfig}>
              刷新
            </Button>
          </Form.Item>
        </Form>
        <Alert
          type="info"
          showIcon
          message="保存后请重启前端服务（如 npm run start）使证书生效；HTTPS 访问时使用 https://localhost:8080。"
          style={{ marginTop: 16 }}
        />
      </Card>
    </div>
  );
};

export default CertConfig;
