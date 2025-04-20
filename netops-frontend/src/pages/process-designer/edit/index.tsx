import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, message, Modal } from 'antd';
import { PDFlowDesigner } from '../../../components/process-designer';
import { processDefinitionApi } from '../../../api/process-designer';
import type { ProcessDefinition } from '../../../types/process-designer/pd-types';

export const ProcessEdit: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [processDefinition, setProcessDefinition] = useState<ProcessDefinition | null>(null);

  useEffect(() => {
    fetchProcessDefinition();
  }, [id]);

  const fetchProcessDefinition = async () => {
    if (!id) {
      setProcessDefinition({
        id: '',
        name: '新建流程',
        description: '',
        version: 1,
        status: 'draft',
        nodes: [],
        edges: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
      return;
    }

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

  const handleSave = async (data: ProcessDefinition) => {
    try {
      if (!id) {
        await processDefinitionApi.create(data);
        message.success('创建成功');
      } else {
        await processDefinitionApi.update(id, data);
        message.success('保存成功');
      }
      navigate('/process-designer');
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleCancel = () => {
    Modal.confirm({
      title: '确认取消',
      content: '取消编辑将丢失所有未保存的更改，是否继续？',
      onOk: () => navigate('/process-designer'),
    });
  };

  if (loading) {
    return <div>加载中...</div>;
  }

  if (!processDefinition) {
    return <div>流程定义不存在</div>;
  }

  return (
    <Card title={id ? '编辑流程' : '新建流程'}>
      <PDFlowDesigner
        initialData={processDefinition}
        onSave={handleSave}
        onCancel={handleCancel}
      />
    </Card>
  );
}; 