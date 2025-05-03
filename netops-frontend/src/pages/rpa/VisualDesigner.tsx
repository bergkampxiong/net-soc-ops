import React, { useState, useCallback, useEffect } from 'react';
import { Layout, Card } from 'antd';
import { useParams } from 'react-router-dom';
import PDFlowDesigner from '../../components/process-designer/pd-flow-designer';
import { processDefinitionApi } from '../../api/process-designer';
import type { ProcessDefinition } from '../../types/process-designer/pd-types';
import type { Node, Edge } from 'reactflow';
import '../../components/process-designer/styles/pd-flow-designer.css';
import '../../components/process-designer/styles/pd-process-manager.css';

const { Content } = Layout;

const VisualDesigner: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [isDirty, setIsDirty] = useState(false);
  const [processDefinition, setProcessDefinition] = useState<{ nodes: Node[]; edges: Edge[] } | undefined>(undefined);

  useEffect(() => {
    if (id) {
      const fetchProcessDefinition = async () => {
        try {
          const response = await processDefinitionApi.getDetail(id);
          // 使用response.data作为流程数据
          if (response?.data) {
            const processData = response.data as unknown as ProcessDefinition;
            // 确保节点和边的数据格式正确
            const nodes = processData.nodes?.map((node: any) => ({
              ...node,
              data: {
                ...node.data,
                label: node.data?.label || '未命名节点',
                isConfigured: node.data?.isConfigured || false,
                configured: node.data?.configured || false
              }
            })) || [];
            const edges = processData.edges?.map((edge: any) => ({
              ...edge,
              type: 'smoothstep',
              style: { strokeWidth: 1.5, stroke: '#1890ff' }
            })) || [];
            setProcessDefinition({
              nodes,
              edges
            });
          }
        } catch (error) {
          console.error('加载流程数据失败:', error);
        }
      };
      fetchProcessDefinition();
    }
  }, [id]);

  const handleDirtyChange = (newIsDirty: boolean) => {
    setIsDirty(newIsDirty);
  };

  return (
    <Layout className="pd-process-manager">
      <Content className="pd-process-manager-content">
        <div className="pd-process-manager-container">
          <Card className="pd-flow-designer-card" bordered={false}>
            <PDFlowDesigner 
              processId={id || null} 
              onDirtyChange={handleDirtyChange}
              initialData={processDefinition}
            />
          </Card>
        </div>
      </Content>
    </Layout>
  );
};

export default VisualDesigner; 