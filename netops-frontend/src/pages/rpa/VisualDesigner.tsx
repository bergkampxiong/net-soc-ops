import React, { useState, useCallback, useEffect } from 'react';
import { Layout, Card } from 'antd';
import { useParams } from 'react-router-dom';
import PDFlowDesigner from '../../components/process-designer/pd-flow-designer';
import '../../components/process-designer/styles/pd-flow-designer.css';
import '../../components/process-designer/styles/pd-process-manager.css';

const { Content } = Layout;

const VisualDesigner: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [isDirty, setIsDirty] = useState(false);

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
            />
          </Card>
        </div>
      </Content>
    </Layout>
  );
};

export default VisualDesigner; 