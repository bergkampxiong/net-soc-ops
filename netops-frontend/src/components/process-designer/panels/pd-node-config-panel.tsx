import React from 'react';
import { Card, Form, Input, Select, InputNumber, Switch, Button, Space } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { PDCustomNode, PDNodeType } from '../../../types/process-designer/pd-types';

const { Option } = Select;

interface PDNodeConfigPanelProps {
  node: PDCustomNode;
  onChange: (node: PDCustomNode) => void;
  onClose?: () => void;
}

export const PDNodeConfigPanel: React.FC<PDNodeConfigPanelProps> = ({
  node,
  onChange,
  onClose,
}) => {
  const [form] = Form.useForm();

  // 根据节点类型获取配置项
  const getConfigFields = () => {
    switch (node.type) {
      case PDNodeType.START:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.END:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.TASK:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="任务类型"
              name="taskType"
              rules={[{ required: true, message: '请选择任务类型' }]}
            >
              <Select>
                <Option value="manual">手动任务</Option>
                <Option value="auto">自动任务</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.CONDITION:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="条件表达式"
              name="condition"
              rules={[{ required: true, message: '请输入条件表达式' }]}
            >
              <Input.TextArea />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.LOOP:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="循环类型"
              name="loopType"
              rules={[{ required: true, message: '请选择循环类型' }]}
            >
              <Select>
                <Option value="for">For循环</Option>
                <Option value="while">While循环</Option>
                <Option value="foreach">ForEach循环</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="循环条件"
              name="loopCondition"
              rules={[{ required: true, message: '请输入循环条件' }]}
            >
              <Input.TextArea />
            </Form.Item>
            <Form.Item
              label="最大循环次数"
              name="maxIterations"
            >
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.DEVICE_CONNECT:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="设备类型"
              name="deviceType"
              rules={[{ required: true, message: '请选择设备类型' }]}
            >
              <Select>
                <Option value="cisco">Cisco</Option>
                <Option value="huawei">Huawei</Option>
                <Option value="h3c">H3C</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="连接协议"
              name="protocol"
              rules={[{ required: true, message: '请选择连接协议' }]}
            >
              <Select>
                <Option value="ssh">SSH</Option>
                <Option value="telnet">Telnet</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="超时时间(秒)"
              name="timeout"
            >
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.CONFIG_DEPLOY:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="配置内容"
              name="config"
              rules={[{ required: true, message: '请输入配置内容' }]}
            >
              <Input.TextArea rows={6} />
            </Form.Item>
            <Form.Item
              label="配置模式"
              name="configMode"
            >
              <Select>
                <Option value="merge">合并模式</Option>
                <Option value="replace">替换模式</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.COMMAND_EXECUTE:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="命令"
              name="command"
              rules={[{ required: true, message: '请输入命令' }]}
            >
              <Input.TextArea rows={4} />
            </Form.Item>
            <Form.Item
              label="超时时间(秒)"
              name="timeout"
            >
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.CONFIG_BACKUP:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="备份路径"
              name="backupPath"
              rules={[{ required: true, message: '请输入备份路径' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="备份文件名"
              name="backupFileName"
              rules={[{ required: true, message: '请输入备份文件名' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      case PDNodeType.STATUS_CHECK:
        return (
          <>
            <Form.Item
              label="节点名称"
              name="label"
              rules={[{ required: true, message: '请输入节点名称' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="检查项"
              name="checkItems"
              rules={[{ required: true, message: '请选择检查项' }]}
            >
              <Select mode="multiple">
                <Option value="cpu">CPU使用率</Option>
                <Option value="memory">内存使用率</Option>
                <Option value="interface">接口状态</Option>
                <Option value="bgp">BGP状态</Option>
                <Option value="ospf">OSPF状态</Option>
              </Select>
            </Form.Item>
            <Form.Item
              label="阈值"
              name="threshold"
            >
              <InputNumber min={0} max={100} />
            </Form.Item>
            <Form.Item
              label="描述"
              name="description"
            >
              <Input.TextArea />
            </Form.Item>
          </>
        );

      default:
        return null;
    }
  };

  // 处理表单提交
  const handleSubmit = (values: any) => {
    onChange({
      ...node,
      ...values,
    });
  };

  return (
    <Card
      title="节点配置"
      extra={
        onClose && (
          <Button type="text" icon={<CloseOutlined />} onClick={onClose} />
        )
      }
      className="pd-node-config-panel"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={node}
        onFinish={handleSubmit}
      >
        {getConfigFields()}
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              保存
            </Button>
            <Button onClick={() => form.resetFields()}>
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
}; 