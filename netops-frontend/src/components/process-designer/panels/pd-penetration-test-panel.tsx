import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Button, Space, Select, message, Alert, Typography } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';

export interface ScanTargetNodeOption {
  id: string;
  label?: string;
  targetType?: string;
  /** 仅静态代码审计时为 true */
  staticOnly?: boolean;
}

export interface PenetrationTestNodeData {
  /** 渗透测试目标只能从扫描目标节点获取 */
  targetSource?: 'targetNode' | 'inline';
  targetNodeId?: string;
  targetType?: string;
  targets?: string[];
  targetValue?: string;
  instruction?: string;
  scanMode?: string;
  presetId?: string;
  label?: string;
  configured?: boolean;
  /** 非静态测试时可选：测试账号，用于已认证扫描 */
  testUsername?: string;
  /** 非静态测试时可选：测试密码，仅内存拼入 instruction，不落库 */
  testPassword?: string;
}

interface PDPenetrationTestPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: PenetrationTestNodeData;
  onSave: (data: PenetrationTestNodeData) => void;
  scanTargetNodes?: ScanTargetNodeOption[];
}

const SCAN_MODES = [
  { value: 'quick', label: 'quick（快速）' },
  { value: 'standard', label: 'standard（常规）' },
  { value: 'deep', label: 'deep（深度）' },
];

/** 测试类型选择后预填的 instruction 默认内容（与文档「指令模板与渗透测试节点配置规范」一致） */
const DEFAULT_INSTRUCTION = {
  dynamic: `执行全面的外部渗透测试，重点关注：

认证和访问控制：
- 使用提供的凭证进行认证测试
  URL"XXXX"
  USER"XXXX"
  PASSWORD"XXXX"
- 测试普通用户和管理员权限
- 重点检查水平/垂直权限越界

关键漏洞类型（按优先级）：
1. IDOR - 检查所有对象引用的访问控制
2. SQL注入 - 所有输入点和API参数
3. SSRF - 特别是文件上传和URL处理功能
4. XSS - 存储型和反射型，包括DOM XSS
5. 认证绕过 - JWT操作、会话管理

业务逻辑测试：
- 工作流程操作和状态转换
- 并发操作和竞态条件
- 价格操作和权限提升

测试要求：
- 遵循完整的发现→验证→报告工作流程
- 每个漏洞都必须有独立的验证智能体
- 提供可复现的PoC和详细的影响分析
- 生成专业的客户报告

排除范围：
- 不进行拒绝服务测试`,
  whitebox: `代码分析（/workspace/repo）：
- 静态分析认证和授权逻辑
- 检查SQL查询和输入验证
- 审查依赖项和配置文件

动态测试（staging.app.com）：
- 使用管理员凭证：admin:AdminPass123!
- 验证代码中发现的问题
- 测试运行时配置漏洞

重点领域：
- 认证系统（JWT实现、会话管理）
- 数据库操作（SQL注入、数据泄露）
- 文件处理（上传漏洞、路径遍历）
- API端点（IDOR、业务逻辑）

工作流程：
1. 代码分析智能体识别潜在问题
2. 验证智能体动态确认漏洞
3. 报告智能体记录详细发现
4. 修复智能体实施代码补丁
5. 测试补丁有效性

报告要求：
- 包含代码位置和修复建议
- 提供前后代码对比
- 验证修复后的安全性`,
  static: `执行深度静态代码安全评估：

第一阶段：代码架构理解
- 构建完整的调用图和数据流图
- 识别信任边界和攻击面
- 分析框架和中间件的安全配置
- 审查依赖项版本和已知漏洞

第二阶段：漏洞模式匹配
- 注入攻击：SQL、NoSQL、LDAP、命令注入
- 认证授权：JWT实现、OAuth流程、会话管理
- 数据处理：序列化、反序列化、XML/JSON解析
- 文件操作：上传、下载、路径处理、临时文件
- 加密实现：密钥管理、随机数生成、哈希算法

第三阶段：业务逻辑审查
- 状态机分析和竞态条件
- 权限提升和水平越权
- 工作流程绕过和异常处理
- 并发操作和原子性保证

工具链集成：
- semgrep自定义规则集
- 静态数据流分析
- 污点追踪和传播分析
- 跨语言漏洞关联

报告要求：
- 按CVSS评分排序漏洞
- 提供可复现的测试用例
- 包含修复前后的代码对比
- 建议安全重构方案

质量保证：
- 验证所有发现的准确性
- 排除误报和低风险问题
- 确保修复方案的可行性
- 提供持续改进建议`,
};

function getTestTypeLabel(targetType?: string, staticOnly?: boolean): string {
  if (staticOnly) return '仅静态（代码审计）';
  if (targetType === 'web_url') return '动态（黑盒）';
  if (targetType === 'git_url') return '白盒（Git）';
  if (targetType === 'local_path') return '白盒（本地路径）';
  return '—';
}

export const PDPenetrationTestPanel: React.FC<PDPenetrationTestPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
  scanTargetNodes = [],
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      form.setFieldsValue({
        targetNodeId: initialData?.targetNodeId,
        instruction: initialData?.instruction,
        scanMode: initialData?.scanMode ?? 'deep',
        testUsername: initialData?.testUsername,
        testPassword: initialData?.testPassword,
        testTypePreset: undefined,
      });
    }
  }, [visible, initialData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const targetNodeId = values.targetNodeId as string;
      if (!targetNodeId) {
        message.error('请选择扫描目标节点');
        return;
      }
      onSave({
        targetSource: 'targetNode',
        targetNodeId,
        instruction: values.instruction || undefined,
        scanMode: values.scanMode ?? 'deep',
        testUsername: values.testUsername || undefined,
        testPassword: values.testPassword || undefined,
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
          <SafetyCertificateOutlined />
          <span>渗透测试节点配置</span>
        </Space>
      }
      width={440}
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
      <Typography.Paragraph type="secondary" style={{ marginBottom: 16, fontSize: 12 }}>
        <strong>扫描模式说明</strong>：quick 快速检查（分钟级，CI/PR 冒烟）；standard 常规评估（约 30 分钟～1 小时）；deep 深度渗透（约 1～4 小时，全面审计）。
      </Typography.Paragraph>
      <Form form={form} layout="vertical">
        {scanTargetNodes.length === 0 ? (
          <Alert
            type="warning"
            showIcon
            message="请先在流程中添加「扫描目标」节点"
            description="渗透测试的目标只能从流程中的扫描目标节点获取，不能在本节点内填写。请添加扫描目标节点并配置目标后再选择。"
            style={{ marginBottom: 16 }}
          />
        ) : null}
        <Form.Item
          name="targetNodeId"
          label="选择扫描目标节点"
          rules={[{ required: true, message: '请选择扫描目标节点' }]}
          extra="渗透测试目标只能从扫描目标节点获取，将使用所选节点中配置的目标执行扫描（单目标）。"
        >
          <Select
            placeholder="选择流程中的扫描目标节点"
            disabled={scanTargetNodes.length === 0}
            options={scanTargetNodes.map((n) => ({
              value: n.id,
              label: n.label || `扫描目标 (${n.id})`,
            }))}
          />
        </Form.Item>
        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.targetNodeId !== curr.targetNodeId}>
          {({ getFieldValue }) => {
            const id = getFieldValue('targetNodeId');
            const node = id ? scanTargetNodes.find((n) => n.id === id) : null;
            const testTypeLabel = node ? getTestTypeLabel(node.targetType, node.staticOnly) : null;
            if (!testTypeLabel || testTypeLabel === '—') return null;
            return (
              <Typography.Paragraph type="secondary" style={{ marginTop: -8, marginBottom: 16, fontSize: 12 }}>
                当前目标测试类型：<strong>{testTypeLabel}</strong>
              </Typography.Paragraph>
            );
          }}
        </Form.Item>
        <Form.Item
          name="scanMode"
          label="扫描模式"
          rules={[{ required: true }]}
        >
          <Select options={SCAN_MODES} />
        </Form.Item>
        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.targetNodeId !== curr.targetNodeId}>
          {({ getFieldValue }) => {
            const id = getFieldValue('targetNodeId');
            const node = id ? scanTargetNodes.find((n) => n.id === id) : null;
            const staticOnly = node?.staticOnly === true;
            return (
              <div style={{ display: 'none' }}>
                {!staticOnly && (
                  <Alert
                    type="info"
                    showIcon
                    message="测试账号与密码（可选）"
                    description="非静态测试时，可填写被测系统的测试账号与密码，以便进行已认证扫描，提高漏洞发现率；仅用于您已授权的测试环境。"
                    style={{ marginBottom: 16 }}
                  />
                )}
                <Form.Item name="testUsername" label="测试账号">
                  <Input placeholder="登录用户名" disabled={staticOnly} />
                </Form.Item>
                <Form.Item name="testPassword" label="测试密码">
                  <Input.Password placeholder="登录密码" disabled={staticOnly} autoComplete="off" />
                </Form.Item>
              </div>
            );
          }}
        </Form.Item>
        <Form.Item
          name="testTypePreset"
          label="测试类型"
          extra="选择后下方 instruction 将预填默认内容，可编辑。"
        >
          <Select
            placeholder="选择类型以预填 instruction"
            allowClear
            options={[
              { value: 'dynamic', label: '动态测试' },
              { value: 'whitebox', label: '白盒测试' },
              { value: 'static', label: '静态测试' },
            ]}
            onChange={(value) => {
              if (value && DEFAULT_INSTRUCTION[value as keyof typeof DEFAULT_INSTRUCTION]) {
                form.setFieldValue('instruction', DEFAULT_INSTRUCTION[value as keyof typeof DEFAULT_INSTRUCTION]);
              }
            }}
          />
        </Form.Item>
        <Form.Item name="instruction" label="instruction">
          <Input.TextArea rows={8} placeholder="如：仅测认证与越权；或先选测试类型预填默认内容" />
        </Form.Item>
      </Form>
    </Drawer>
  );
};
