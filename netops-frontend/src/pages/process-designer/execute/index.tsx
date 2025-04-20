import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, message, Modal, Form, Input } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined, PauseCircleOutlined, StopOutlined } from '@ant-design/icons';
import { PDFlowDesigner } from '../../../components/process-designer';
import { processDefinitionApi, processInstanceApi } from '../../../api/process-designer';
import type { ProcessDefinition, ProcessInstance } from '../../../types/process-designer/pd-types';

const { TextArea } = Input;

export const ProcessExecute: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [processDefinition, setProcessDefinition] = useState<ProcessDefinition | null>(null);
  const [processInstance, setProcessInstance] = useState<ProcessInstance | null>(null);
  const [showVariableForm, setShowVariableForm] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    if (id) {
      fetchProcessDefinition();
    }
  }, [id]);

  const fetchProcessDefinition = async () => {
    if (!id) return;

    try {
      setLoading(true);
      const response = await processDefinitionApi.getDetail(id);
      setProcessDefinition(response.data.data);
    } catch (error) {
      message.error('获取流程定义失败');
      navigate('/process-designer');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    setShowVariableForm(true);
  };

  const handleVariableSubmit = async (values: { variables: string }) => {
    try {
      let variables: Record<string, any> = {};
      try {
        variables = JSON.parse(values.variables);
      } catch (error) {
        message.error('变量格式不正确，请使用JSON格式');
        return;
      }

      if (!processDefinition) return;

      const response = await processInstanceApi.create({
        processDefinitionId: id!,
        name: `${processDefinition.name} - ${new Date().toLocaleString()}`,
        variables,
        status: 'running',
        nodeStates: {},
        startedAt: new Date().toISOString(),
      });
      setProcessInstance(response.data.data);
      setShowVariableForm(false);
      message.success('流程已启动');
    } catch (error) {
      message.error('启动流程失败');
    }
  };

  const handleSuspend = async () => {
    if (!processInstance) return;

    try {
      await processInstanceApi.suspend(processInstance.id);
      setProcessInstance({
        ...processInstance,
        status: 'suspended',
      });
      message.success('流程已暂停');
    } catch (error) {
      message.error('暂停流程失败');
    }
  };

  const handleResume = async () => {
    if (!processInstance) return;

    try {
      await processInstanceApi.resume(processInstance.id);
      setProcessInstance({
        ...processInstance,
        status: 'running',
      });
      message.success('流程已恢复');
    } catch (error) {
      message.error('恢复流程失败');
    }
  };

  const handleTerminate = () => {
    if (!processInstance) return;

    Modal.confirm({
      title: '确认终止',
      content: '确定要终止当前流程吗？',
      onOk: async () => {
        try {
          await processInstanceApi.terminate(processInstance.id);
          setProcessInstance({
            ...processInstance,
            status: 'failed',
          });
          message.success('流程已终止');
        } catch (error) {
          message.error('终止流程失败');
        }
      },
    });
  };

  if (loading) {
    return <div>加载中...</div>;
  }

  if (!processDefinition) {
    return <div>流程定义不存在</div>;
  }

  return (
    <Card>
      <div className="process-execute-header">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/process-designer')}>
            返回
          </Button>
          {!processInstance ? (
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleStart}>
              开始执行
            </Button>
          ) : (
            <>
              {processInstance.status === 'running' && (
                <Button icon={<PauseCircleOutlined />} onClick={handleSuspend}>
                  暂停
                </Button>
              )}
              {processInstance.status === 'suspended' && (
                <Button icon={<PlayCircleOutlined />} onClick={handleResume}>
                  恢复
                </Button>
              )}
              <Button danger icon={<StopOutlined />} onClick={handleTerminate}>
                终止
              </Button>
            </>
          )}
        </Space>
      </div>

      <div className="process-execute-content">
        <PDFlowDesigner
          initialData={processDefinition}
          readOnly
          executionData={processInstance ? {
            nodeStates: processInstance.nodeStates,
            variables: processInstance.variables,
          } : undefined}
        />
      </div>

      <Modal
        title="设置流程变量"
        open={showVariableForm}
        onOk={() => form.submit()}
        onCancel={() => setShowVariableForm(false)}
      >
        <Form form={form} onFinish={handleVariableSubmit}>
          <Form.Item
            name="variables"
            label="流程变量"
            rules={[{ required: true, message: '请输入流程变量' }]}
          >
            <TextArea rows={4} placeholder="请输入JSON格式的流程变量" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}; 