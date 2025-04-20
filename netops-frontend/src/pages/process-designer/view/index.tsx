import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Button, Space, message, Modal } from 'antd';
import { ArrowLeftOutlined, EditOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { PDFlowDesigner } from '../../../components/process-designer';
import { processDefinitionApi } from '../../../api/process-designer';
import type { ProcessDefinition } from '../../../types/process-designer/pd-types';

export const ProcessView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [processDefinition, setProcessDefinition] = useState<ProcessDefinition | null>(null);
  const [isEditing, setIsEditing] = useState(false);

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

  const handleSave = async (data: ProcessDefinition) => {
    if (!id) return;

    try {
      await processDefinitionApi.update(id, data);
      message.success('保存成功');
      setIsEditing(false);
      fetchProcessDefinition();
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleCancel = () => {
    Modal.confirm({
      title: '确认取消',
      content: '取消编辑将丢失所有未保存的更改，是否继续？',
      onOk: () => setIsEditing(false),
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
      <div className="process-view-header">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/process-designer')}>
            返回
          </Button>
          {!isEditing ? (
            <>
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setIsEditing(true)}
              >
                编辑
              </Button>
              <Button
                icon={<PlayCircleOutlined />}
                onClick={() => navigate(`/process-designer/execute/${id}`)}
              >
                执行
              </Button>
            </>
          ) : (
            <>
              <Button type="primary" onClick={() => {}}>
                保存
              </Button>
              <Button onClick={handleCancel}>
                取消
              </Button>
            </>
          )}
        </Space>
      </div>

      {!isEditing ? (
        <>
          <Descriptions title="流程信息" bordered>
            <Descriptions.Item label="名称">{processDefinition.name}</Descriptions.Item>
            <Descriptions.Item label="描述">{processDefinition.description}</Descriptions.Item>
            <Descriptions.Item label="版本">{processDefinition.version}</Descriptions.Item>
            <Descriptions.Item label="状态">
              {processDefinition.status === 'draft' && '草稿'}
              {processDefinition.status === 'published' && '已发布'}
              {processDefinition.status === 'disabled' && '已停用'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(processDefinition.createdAt).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {new Date(processDefinition.updatedAt).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>

          <div className="process-view-flow">
            <PDFlowDesigner
              initialData={processDefinition}
              readOnly
            />
          </div>
        </>
      ) : (
        <PDFlowDesigner
          initialData={processDefinition}
          onSave={handleSave}
          onCancel={handleCancel}
        />
      )}
    </Card>
  );
}; 