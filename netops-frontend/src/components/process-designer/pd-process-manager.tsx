import React, { useState } from 'react';
import { Layout, Card } from 'antd';
import PDProcessList from './pd-process-list';
import PDFlowDesigner from './pd-flow-designer';
import './styles/pd-process-manager.css';

const { Content } = Layout;

const PDProcessManager: React.FC = () => {
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);

  const handleSelectProcess = (processId: string) => {
    setSelectedProcessId(processId);
  };

  const handleCreateProcess = (processId: string) => {
    setSelectedProcessId(processId);
  };

  return (
    <Layout className="pd-process-manager">
      <Content className="pd-process-manager-content">
        <div className="pd-process-manager-container">
          <Card className="pd-process-list-card">
            <PDProcessList 
              onSelectProcess={handleSelectProcess}
              onCreateProcess={handleCreateProcess}
            />
          </Card>
          <Card className="pd-flow-designer-card">
            <PDFlowDesigner processId={selectedProcessId} />
          </Card>
        </div>
      </Content>
    </Layout>
  );
};

export default PDProcessManager; 