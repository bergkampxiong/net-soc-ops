import React, { useState, useCallback } from 'react';
import { Layout, Card, Tabs, Modal } from 'antd';
import PDProcessList from '../../components/process-designer/pd-process-list';
import PDFlowDesigner from '../../components/process-designer/pd-flow-designer';
import '../../components/process-designer/styles/pd-flow-designer.css';
import '../../components/process-designer/styles/pd-process-list.css';
import '../../components/process-designer/styles/pd-process-manager.css';

const { Content } = Layout;

const VisualDesigner: React.FC = () => {
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
  const [activeKey, setActiveKey] = useState('process-list');
  const [isDirty, setIsDirty] = useState(false);
  const [pendingProcessId, setPendingProcessId] = useState<string | null>(null);

  // 处理流程切换
  const handleProcessChange = useCallback((processId: string) => {
    if (isDirty) {
      setPendingProcessId(processId);
      Modal.confirm({
        title: '确认切换',
        content: '当前流程有未保存的更改，确定要切换到其他流程吗？',
        okText: '确认',
        cancelText: '取消',
        onOk: () => {
          setSelectedProcessId(processId);
          setActiveKey('flow-designer');
          setIsDirty(false);
          setPendingProcessId(null);
        },
        onCancel: () => {
          setPendingProcessId(null);
        },
      });
    } else {
      setSelectedProcessId(processId);
      setActiveKey('flow-designer');
    }
  }, [isDirty]);

  const handleSelectProcess = (processId: string) => {
    handleProcessChange(processId);
  };

  const handleCreateProcess = (processId: string) => {
    handleProcessChange(processId);
  };

  const handleDirtyChange = (newIsDirty: boolean) => {
    setIsDirty(newIsDirty);
  };

  const handleTabChange = (key: string) => {
    if (key === 'process-list' && isDirty) {
      Modal.confirm({
        title: '确认返回',
        content: '当前流程有未保存的更改，确定要返回流程列表吗？',
        okText: '确认',
        cancelText: '取消',
        onOk: () => {
          setActiveKey(key);
          setIsDirty(false);
        },
      });
    } else {
      setActiveKey(key);
    }
  };

  const items = [
    {
      key: 'process-list',
      label: '流程列表',
      children: (
        <Card className="pd-process-list-card" bordered={false}>
          <PDProcessList 
            onSelectProcess={handleSelectProcess}
            onCreateProcess={handleCreateProcess}
          />
        </Card>
      ),
    },
    {
      key: 'flow-designer',
      label: '流程设计器',
      children: (
        <Card className="pd-flow-designer-card" bordered={false}>
          <PDFlowDesigner 
            processId={selectedProcessId} 
            onDirtyChange={handleDirtyChange}
          />
        </Card>
      ),
    },
  ];

  return (
    <Layout className="pd-process-manager">
      <Content className="pd-process-manager-content">
        <Card bordered={false} className="pd-tabs-container">
          <Tabs
            type="card"
            items={items}
            className="pd-tabs"
            activeKey={activeKey}
            onChange={handleTabChange}
            destroyInactiveTabPane={false}
          />
        </Card>
      </Content>
    </Layout>
  );
};

export default VisualDesigner; 