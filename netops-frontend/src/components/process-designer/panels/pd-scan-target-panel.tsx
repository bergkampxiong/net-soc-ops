import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, Select, message, Typography } from 'antd';
import { AimOutlined } from '@ant-design/icons';

export interface ScanTargetNodeData {
  targetType?: string;
  targets?: string[];
  targetValue?: string;
  /** 仅静态代码审计，不尝试运行应用（仅对 git_url / local_path 有效） */
  staticOnly?: boolean;
  useBackupOutput?: boolean;
  label?: string;
  configured?: boolean;
}

interface PDScanTargetPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: ScanTargetNodeData;
  onSave: (data: ScanTargetNodeData) => void;
}

/** 测试类型：动态/白盒/仅静态 */
const TEST_TYPE_OPTIONS = [
  { value: 'dynamic', label: '动态（黑盒）' },
  { value: 'whitebox', label: '白盒（静态+动态）' },
  { value: 'static', label: '仅静态（代码审计）' },
];

/** 白盒子类型 */
const WHITEBOX_KIND_OPTIONS = [
  { value: 'git_url', label: 'Git 仓库' },
  { value: 'local_path', label: '本地路径' },
];

export const PDScanTargetPanel: React.FC<PDScanTargetPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      const targets = initialData?.targets ?? (initialData?.targetValue ? [initialData.targetValue] : []);
      const t = initialData?.targetType ?? 'web_url';
      const staticOnly = initialData?.staticOnly === true;
      const testType = staticOnly ? 'static' : (t === 'web_url' ? 'dynamic' : 'whitebox');
      const whiteboxKind = t === 'git_url' ? 'git_url' : t === 'local_path' ? 'local_path' : 'git_url';
      form.setFieldsValue({
        testType,
        whiteboxKind: t === 'git_url' || t === 'local_path' ? whiteboxKind : 'git_url',
        targetType: t,
        targetValue: targets.length ? targets[0] : '',
      });
    }
  }, [visible, initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const testType = values.testType as string;
      const targetType = testType === 'dynamic' ? 'web_url' : (values.whiteboxKind || 'git_url');
      const targetValue = (values.targetValue || '').trim();
      if (!targetValue) {
        message.error('请填写目标');
        return;
      }
      const staticOnly = testType === 'static';
      onSave({
        targetType,
        targets: [targetValue],
        targetValue,
        staticOnly: staticOnly || undefined,
        configured: true,
      });
      onClose();
      message.success('配置已保存');
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error('请检查配置信息');
    }
  };

  return (
    <Drawer
      title={
        <Space>
          <AimOutlined />
          <span>扫描目标节点配置</span>
        </Space>
      }
      width={480}
      open={visible}
      onClose={onClose}
      extra={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSave} loading={loading}>
            保存
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" initialValues={{ testType: 'dynamic', whiteboxKind: 'git_url' }}>
        <Form.Item
          name="testType"
          label="测试类型"
          rules={[{ required: true, message: '请选择测试类型' }]}
          extra="选择后下方将显示对应的目标输入框。渗透测试将根据此处类型进行黑盒或白盒测试。"
        >
          <Select
            placeholder="选择测试类型"
            options={TEST_TYPE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
            onChange={(v) => {
              if (v === 'dynamic') form.setFieldsValue({ targetType: 'web_url' });
              else if (v === 'whitebox' || v === 'static') form.setFieldsValue({ whiteboxKind: 'git_url', targetType: 'git_url' });
            }}
          />
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.testType !== curr.testType}>
          {({ getFieldValue }) => {
            const testType = getFieldValue('testType');
            if (testType === 'dynamic') {
              return (
                <Form.Item
                  name="targetValue"
                  label="目标 URL / 域名或 IP"
                  rules={[{ required: true, message: '请填写目标 URL、域名或 IP' }]}
                  extra="无源码，仅对已部署的 Web/API 做黑盒渗透测试。"
                >
                  <Input placeholder="如 https://example.com、http://192.168.1.1:8080、api.example.com" />
                </Form.Item>
              );
            }
            if (testType === 'whitebox' || testType === 'static') {
              const isStatic = testType === 'static';
              return (
                <>
                  <Form.Item
                    name="whiteboxKind"
                    label={isStatic ? '目标来源' : '白盒目标来源'}
                    rules={[{ required: true }]}
                  >
                    <Select
                      options={WHITEBOX_KIND_OPTIONS}
                      onChange={(v) => form.setFieldsValue({ targetType: v })}
                    />
                  </Form.Item>
                  <Form.Item noStyle shouldUpdate={(prev, curr) => prev.whiteboxKind !== curr.whiteboxKind}>
                    {({ getFieldValue: gfv }) => {
                      const kind = gfv('whiteboxKind');
                      if (kind === 'git_url') {
                        return (
                          <Form.Item
                            name="targetValue"
                            label="Git 仓库地址"
                            rules={[{ required: true, message: '请填写 Git 仓库地址' }]}
                            extra={isStatic ? '仅对仓库代码做静态审计，不尝试运行应用。' : '对仓库代码做静态审计，并尽可能运行应用做动态验证。'}
                          >
                            <Input placeholder="如 https://github.com/org/repo.git 或 git@github.com:org/repo.git" />
                          </Form.Item>
                        );
                      }
                      return (
                        <Form.Item
                          name="targetValue"
                          label="本地代码路径"
                          rules={[{ required: true, message: '请填写本地代码路径' }]}
                          extra={isStatic ? '仅对指定目录做静态代码审计，不尝试运行应用。' : '对指定目录下的代码做静态+动态安全扫描。执行时路径相对于 Strix 运行环境。'}
                        >
                          <Input placeholder="如 ./app 或 /var/www/myapp" />
                        </Form.Item>
                      );
                    }}
                  </Form.Item>
                </>
              );
            }
            return null;
          }}
        </Form.Item>
      </Form>

      <Typography.Paragraph type="secondary" style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #f0f0f0', fontSize: 12 }}>
        <strong>配置提示</strong>
      </Typography.Paragraph>
      <Typography.Paragraph type="secondary" style={{ marginTop: 6, fontSize: 12 }}>
        <strong>动态（黑盒）</strong>：填写 URL、域名或 IP，无源码，仅对已部署目标做黑盒渗透测试。
      </Typography.Paragraph>
      <Typography.Paragraph type="secondary" style={{ marginTop: 8, fontSize: 12 }}>
        <strong>白盒（静态+动态）</strong>：填写 Git 仓库地址或本地路径，将进行代码审计并尽可能运行后做动态验证。
      </Typography.Paragraph>
      <Typography.Paragraph type="secondary" style={{ marginTop: 8, fontSize: 12 }}>
        <strong>仅静态（代码审计）</strong>：仅对源码做静态分析，不尝试在沙箱中运行应用；适合依赖数据库等难以在沙箱跑起来的项目。
      </Typography.Paragraph>
    </Drawer>
  );
};
