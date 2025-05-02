import React, { useCallback, useState, useRef, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  NodeChange,
  EdgeChange,
  Panel,
  useReactFlow,
  ReactFlowProvider,
  MarkerType,
  ConnectionMode,
} from 'reactflow';
import { Button, Space, Divider, Modal, Form, Input } from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  CloseOutlined,
  UndoOutlined,
  RedoOutlined,
  CheckOutlined,
  PlayCircleOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  ApiOutlined,
  BranchesOutlined,
  SyncOutlined,
  CloudServerOutlined,
  DeploymentUnitOutlined,
  CodeOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import 'reactflow/dist/style.css';
import './styles/pd-flow-designer.css';
import { processCodeGeneratorApi } from '../../api/process-code-generator';
import { saveProcessDesign, updateProcessDesign, ProcessDesignerSaveRequest } from '../../api/process-designer';

// 导入所有节点组件
import { PDStartNode } from './nodes/pd-start-node';
import { PDEndNode } from './nodes/pd-end-node';
import { PDTaskNode } from './nodes/pd-task-node';
import { PDConditionNode } from './nodes/pd-condition-node';
import { PDLoopNode } from './nodes/pd-loop-node';
import { PDDeviceConnectNode } from './nodes/pd-device-connect-node';
import { PDConfigDeployNode } from './nodes/pd-config-deploy-node';
import { PDCommandExecuteNode } from './nodes/pd-command-execute-node';
import { PDConfigBackupNode } from './nodes/pd-config-backup-node';
import { PDStatusCheckNode } from './nodes/pd-status-check-node';

// 导入所有配置面板组件
import { PDDeviceConnectPanel } from './panels/pd-device-connect-panel';
import { PDTaskPanel } from './panels/pd-task-panel';
import { PDConditionPanel } from './panels/pd-condition-panel';
import { PDConfigDeployPanel } from './panels/pd-config-deploy-panel';
import { PDCommandExecutePanel } from './panels/pd-command-execute-panel';
import { PDConfigBackupPanel } from './panels/pd-config-backup-panel';
import { PDStatusCheckPanel } from './panels/pd-status-check-panel';

// 节点类型映射
const nodeTypes = {
  start: PDStartNode,
  end: PDEndNode,
  task: PDTaskNode,
  condition: PDConditionNode,
  loop: PDLoopNode,
  deviceConnect: PDDeviceConnectNode,
  configDeploy: PDConfigDeployNode,
  commandExecute: PDCommandExecuteNode,
  configBackup: PDConfigBackupNode,
  statusCheck: PDStatusCheckNode,
};

// 节点配置
const nodeConfigs = [
  {
    type: 'start',
    title: '开始节点',
    icon: <PlayCircleOutlined style={{ fontSize: 26, color: '#1890ff' }} />,
  },
  {
    type: 'end',
    title: '结束节点',
    icon: <CloseOutlined style={{ fontSize: 26, color: '#ff4d4f' }} />,
  },
  {
    type: 'task',
    title: '任务节点',
    icon: <CheckOutlined style={{ fontSize: 26, color: '#1890ff' }} />,
  },
  {
    type: 'condition',
    title: '条件节点',
    icon: <BranchesOutlined style={{ fontSize: 26, color: '#faad14' }} />,
  },
  {
    type: 'deviceConnect',
    title: '设备连接',
    icon: <CloudServerOutlined style={{ fontSize: 26, color: '#13c2c2' }} />,
  },
  {
    type: 'configDeploy',
    title: '配置下发',
    icon: <DeploymentUnitOutlined style={{ fontSize: 26, color: '#eb2f96' }} />,
  },
  {
    type: 'commandExecute',
    title: '命令执行',
    icon: <CodeOutlined style={{ fontSize: 26, color: '#fa8c16' }} />,
  },
  {
    type: 'configBackup',
    title: '配置备份',
    icon: <SaveOutlined style={{ fontSize: 26, color: '#2f54eb' }} />,
  },
  {
    type: 'statusCheck',
    title: '状态检查',
    icon: <CheckCircleOutlined style={{ fontSize: 26, color: '#52c41a' }} />,
  },
];

const initialNodes = [
  {
    id: 'start-1',
    type: 'start',
    position: { x: 100, y: 100 },
    data: { 
      label: '开始节点',
      icon: <PlayCircleOutlined style={{ fontSize: 16, color: '#1890ff' }} />
    }
  }
];

interface NodeData {
  label: string;
  icon: React.ReactNode;
  configured?: boolean;
}

interface CustomNode extends Node {
  data: NodeData;
}

interface PDFlowDesignerProps {
  processId: string | null;
  onDirtyChange?: (isDirty: boolean) => void;
}

const FlowDesigner: React.FC<PDFlowDesignerProps> = ({ processId, onDirtyChange }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const navigate = useNavigate();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useReactFlow();
  const [isDirty, setIsDirty] = useState(false);
  const previousProcessId = useRef(processId);
  const [showDeviceConnectPanel, setShowDeviceConnectPanel] = useState(false);
  const [selectedDeviceNode, setSelectedDeviceNode] = useState<Node | null>(null);
  const [showTaskPanel, setShowTaskPanel] = useState(false);
  const [showConditionPanel, setShowConditionPanel] = useState(false);
  const [showConfigDeployPanel, setShowConfigDeployPanel] = useState(false);
  const [showCommandExecutePanel, setShowCommandExecutePanel] = useState(false);
  const [showConfigBackupPanel, setShowConfigBackupPanel] = useState(false);
  const [showStatusCheckPanel, setShowStatusCheckPanel] = useState(false);
  const [selectedTaskNode, setSelectedTaskNode] = useState<Node | null>(null);
  const [selectedConditionNode, setSelectedConditionNode] = useState<Node | null>(null);
  const [selectedConfigDeployNode, setSelectedConfigDeployNode] = useState<Node | null>(null);
  const [selectedCommandExecuteNode, setSelectedCommandExecuteNode] = useState<Node | null>(null);
  const [selectedConfigBackupNode, setSelectedConfigBackupNode] = useState<Node | null>(null);
  const [selectedStatusCheckNode, setSelectedStatusCheckNode] = useState<Node | null>(null);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveForm] = Form.useForm();
  const [isSaving, setIsSaving] = useState(false);

  // 处理键盘删除事件
  const onKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Delete' || event.key === 'Backspace') {
      setNodes((nodes) => nodes.filter((node) => !node.selected));
      setEdges((edges) => edges.filter((edge) => !edge.selected));
    }
  }, [setNodes, setEdges]);

  // 添加键盘事件监听
  useEffect(() => {
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [onKeyDown]);

  // 处理流程数据变化
  const handleNodesChange = (changes: NodeChange[]) => {
    onNodesChange(changes);
    setIsDirty(true);
    onDirtyChange?.(true);
  };

  const handleEdgesChange = (changes: EdgeChange[]) => {
    onEdgesChange(changes);
    setIsDirty(true);
    onDirtyChange?.(true);
  };

  const handleConnect = useCallback(
    (params: Connection) => {
      // 验证连线
      const sourceNode = nodes.find(node => node.id === params.source);
      const targetNode = nodes.find(node => node.id === params.target);

      if (!sourceNode || !targetNode) {
        return;
      }

      // 验证连线规则
      if (sourceNode.type === 'end') {
        message.error('结束节点不能作为连线起点');
        return;
      }

      // 检查是否已存在相同连线
      const existingEdge = edges.find(
        edge => edge.source === params.source && edge.target === params.target
      );

      if (existingEdge) {
        message.error('该连线已存在');
        return;
      }

      // 创建新连线
      const edge = {
        ...params,
        id: `edge-${params.source}-${params.target}`,
        style: { 
          strokeWidth: 1.5,
          stroke: '#1890ff'
        },
        type: 'smoothstep',
        animated: false,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#1890ff',
          width: 20,
          height: 20
        }
      };

      setEdges((eds) => {
        const newEdges = addEdge(edge, eds);
        setIsDirty(true);
        onDirtyChange?.(true);
        return newEdges;
      });
    },
    [nodes, edges, setEdges, onDirtyChange]
  );

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === 'deviceConnect') {
      setSelectedDeviceNode(node);
      setShowDeviceConnectPanel(true);
    } else if (node.type === 'task') {
      setSelectedTaskNode(node);
      setShowTaskPanel(true);
    } else if (node.type === 'condition') {
      setSelectedConditionNode(node);
      setShowConditionPanel(true);
    } else if (node.type === 'configDeploy') {
      setSelectedConfigDeployNode(node);
      setShowConfigDeployPanel(true);
    } else if (node.type === 'commandExecute') {
      setSelectedCommandExecuteNode(node);
      setShowCommandExecutePanel(true);
    } else if (node.type === 'configBackup') {
      setSelectedConfigBackupNode(node);
      setShowConfigBackupPanel(true);
    } else if (node.type === 'statusCheck') {
      setSelectedStatusCheckNode(node);
      setShowStatusCheckPanel(true);
    }
    setSelectedNode(node);
  }, []);

  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');
      
      if (!type || !reactFlowBounds || !reactFlowInstance) {
        return;
      }

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top
      });

      const config = nodeConfigs.find(config => config.type === type);
      if (!config) return;

      const newNode = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: { 
          label: config.title,
          icon: config.icon
        }
      };

      setNodes((nds) => nds.concat(newNode));
      setIsDirty(true);
      onDirtyChange?.(true);
    },
    [reactFlowInstance, setNodes, onDirtyChange]
  );

  // 验证流程完整性
  const validateProcess = () => {
    // 检查是否有开始节点
    const hasStartNode = nodes.some(node => node.type === 'start');
    if (!hasStartNode) {
      message.error('流程必须包含开始节点');
      return false;
    }

    // 检查是否有结束节点
    const hasEndNode = nodes.some(node => node.type === 'end');
    if (!hasEndNode) {
      message.error('流程必须包含结束节点');
      return false;
    }

    // 检查所有节点是否配置完整
    const unconfiguredNodes = nodes.filter(node => {
      if (node.type === 'start' || node.type === 'end') return false;
      return !(node as CustomNode).data?.configured;
    });

    if (unconfiguredNodes.length > 0) {
      message.error(`以下节点未完成配置：${unconfiguredNodes.map(n => n.data?.label).join(', ')}`);
      return false;
    }

    return true;
  };

  // 处理保存
  const handleSave = async () => {
    if (!validateProcess()) {
      return;
    }

    setSaveModalVisible(true);
    saveForm.resetFields();
  };

  // 处理保存确认
  const handleSaveConfirm = async () => {
    try {
      const values = await saveForm.validateFields();
      setIsSaving(true);

      const saveData: ProcessDesignerSaveRequest = {
        name: values.name,
        description: values.description,
        nodes,
        edges,
        variables: {}, // TODO: 从节点配置中收集变量
      };

      if (processId) {
        await updateProcessDesign(processId, saveData);
        message.success('更新成功');
      } else {
        await saveProcessDesign(saveData);
        message.success('保存成功');
      }

      setIsDirty(false);
      onDirtyChange?.(false);
      setSaveModalVisible(false);
    } catch (error) {
      message.error('保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  const handleValidate = () => {
    message.success('验证通过');
  };

  const handleExecute = async () => {
    try {
      const response = await processCodeGeneratorApi.generate(processId || '');
      const code = response.data.data;
      
      // 创建下载链接
      const blob = new Blob([code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `process_${processId}_generated.py`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      message.success('代码生成成功');
    } catch (error) {
      message.error('代码生成失败');
    }
  };

  // 处理设备连接配置保存
  const handleDeviceConnectSave = useCallback((data: any) => {
    if (selectedDeviceNode) {
      const updatedNode = {
        ...selectedDeviceNode,
        data: {
          ...selectedDeviceNode.data,
          ...data,
          configured: true
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedDeviceNode.id ? updatedNode : node
        )
      );
      setShowDeviceConnectPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedDeviceNode, setNodes, onDirtyChange]);

  // 处理任务节点配置保存
  const handleTaskSave = useCallback((data: any) => {
    if (selectedTaskNode) {
      const updatedNode = {
        ...selectedTaskNode,
        data: {
          ...selectedTaskNode.data,
          ...data,
          configured: true
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedTaskNode.id ? updatedNode : node
        )
      );
      setShowTaskPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedTaskNode, setNodes, onDirtyChange]);

  // 处理条件节点配置保存
  const handleConditionSave = useCallback((data: any) => {
    if (selectedConditionNode) {
      const updatedNode = {
        ...selectedConditionNode,
        data: {
          ...selectedConditionNode.data,
          ...data,
          configured: true
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedConditionNode.id ? updatedNode : node
        )
      );
      setShowConditionPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedConditionNode, setNodes, onDirtyChange]);

  // 处理配置下发节点配置保存
  const handleConfigDeploySave = useCallback((data: any) => {
    if (selectedConfigDeployNode) {
      const updatedNode = {
        ...selectedConfigDeployNode,
        data: {
          ...selectedConfigDeployNode.data,
          ...data,
          configured: true
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedConfigDeployNode.id ? updatedNode : node
        )
      );
      setShowConfigDeployPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedConfigDeployNode, setNodes, onDirtyChange]);

  // 处理命令执行节点配置保存
  const handleCommandExecuteSave = useCallback((data: any) => {
    if (selectedCommandExecuteNode) {
      const updatedNode = {
        ...selectedCommandExecuteNode,
        data: {
          ...selectedCommandExecuteNode.data,
          ...data,
          configured: true
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedCommandExecuteNode.id ? updatedNode : node
        )
      );
      setShowCommandExecutePanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedCommandExecuteNode, setNodes, onDirtyChange]);

  // 处理配置备份节点配置保存
  const handleConfigBackupSave = useCallback((data: any) => {
    if (selectedConfigBackupNode) {
      const updatedNode = {
        ...selectedConfigBackupNode,
        data: {
          ...selectedConfigBackupNode.data,
          ...data,
          configured: true
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedConfigBackupNode.id ? updatedNode : node
        )
      );
      setShowConfigBackupPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedConfigBackupNode, setNodes, onDirtyChange]);

  // 处理状态检查节点配置保存
  const handleStatusCheckSave = useCallback((data: any) => {
    if (selectedStatusCheckNode) {
      const updatedNode = {
        ...selectedStatusCheckNode,
        data: {
          ...selectedStatusCheckNode.data,
          ...data,
          configured: true
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedStatusCheckNode.id ? updatedNode : node
        )
      );
      setShowStatusCheckPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedStatusCheckNode, setNodes, onDirtyChange]);

  // 加载流程数据
  useEffect(() => {
    if (processId && processId !== previousProcessId.current) {
      // TODO: 替换为实际的API调用
      // 模拟加载流程数据
      setNodes(initialNodes);
      setEdges([]);
      setIsDirty(false);
      onDirtyChange?.(false);
      previousProcessId.current = processId;
    }
  }, [processId, setNodes, setEdges, onDirtyChange]);

  // 监听页面刷新或关闭
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [isDirty]);

  return (
    <div className="pd-flow-designer">
      <div className="pd-toolbar">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/process-designer')}>
            返回
          </Button>
          <Divider type="vertical" />
          <Button
            type="primary"
            onClick={handleSave}
            disabled={!isDirty}
          >
            保存
          </Button>
          <Button
            onClick={() => {
              if (processId) {
                // TODO: 替换为实际的API调用
                // 重新加载流程数据
                setNodes(initialNodes);
                setEdges([]);
                setIsDirty(false);
                onDirtyChange?.(false);
              }
            }}
            disabled={!isDirty}
          >
            重置
          </Button>
          <Button icon={<CheckOutlined />} onClick={handleValidate}>
            验证
          </Button>
          <Button icon={<CodeOutlined />} onClick={handleExecute}>
            代码生成
          </Button>
        </Space>
      </div>

      <div className="pd-flow-container">
        <div className="pd-node-panel">
          {nodeConfigs.map((config) => (
            <div
              key={config.type}
              className="node-item"
              draggable
              onDragStart={(e) => onDragStart(e, config.type)}
            >
              {config.icon}
              <div className="node-info">
                <div className="node-title">{config.title}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="react-flow-wrapper" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            onDrop={onDrop}
            onDragOver={onDragOver}
            fitView
            deleteKeyCode="Delete"
            selectionKeyCode="Shift"
            multiSelectionKeyCode="Control"
            defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
            minZoom={0.1}
            maxZoom={1.5}
            defaultEdgeOptions={{
              type: 'smoothstep',
              style: { stroke: '#1890ff', strokeWidth: 1.5 },
              animated: false,
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#1890ff',
                width: 20,
                height: 20
              }
            }}
            connectionMode={ConnectionMode.Loose}
            snapToGrid
            snapGrid={[15, 15]}
            connectOnClick={false}
            nodesDraggable={true}
            nodesConnectable={true}
            elementsSelectable={true}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#e5e5e5" gap={20} size={1} />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </div>

      <PDDeviceConnectPanel
        visible={showDeviceConnectPanel}
        onClose={() => setShowDeviceConnectPanel(false)}
        initialData={selectedDeviceNode?.data}
        onSave={handleDeviceConnectSave}
      />

      <PDTaskPanel
        visible={showTaskPanel}
        onClose={() => setShowTaskPanel(false)}
        initialData={selectedTaskNode?.data}
        onSave={handleTaskSave}
      />

      <PDConditionPanel
        visible={showConditionPanel}
        onClose={() => setShowConditionPanel(false)}
        initialData={selectedConditionNode?.data}
        onSave={handleConditionSave}
      />

      <PDConfigDeployPanel
        visible={showConfigDeployPanel}
        onClose={() => setShowConfigDeployPanel(false)}
        initialData={selectedConfigDeployNode?.data}
        onSave={handleConfigDeploySave}
      />

      <PDCommandExecutePanel
        visible={showCommandExecutePanel}
        onClose={() => setShowCommandExecutePanel(false)}
        initialData={selectedCommandExecuteNode?.data}
        onSave={handleCommandExecuteSave}
      />

      <PDConfigBackupPanel
        visible={showConfigBackupPanel}
        onClose={() => setShowConfigBackupPanel(false)}
        initialData={selectedConfigBackupNode?.data}
        onSave={handleConfigBackupSave}
      />

      <PDStatusCheckPanel
        visible={showStatusCheckPanel}
        onClose={() => setShowStatusCheckPanel(false)}
        initialData={selectedStatusCheckNode?.data}
        onSave={handleStatusCheckSave}
      />

      {/* 保存对话框 */}
      <Modal
        title={processId ? '更新流程' : '保存流程'}
        open={saveModalVisible}
        onOk={handleSaveConfirm}
        onCancel={() => setSaveModalVisible(false)}
        confirmLoading={isSaving}
      >
        <Form form={saveForm} layout="vertical">
          <Form.Item
            name="name"
            label="流程名称"
            rules={[{ required: true, message: '请输入流程名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="description"
            label="流程描述"
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

// 导出包装后的组件
const PDFlowDesigner: React.FC<PDFlowDesignerProps> = ({ processId, onDirtyChange }) => {
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlowProvider>
        <FlowDesigner processId={processId} onDirtyChange={onDirtyChange} />
      </ReactFlowProvider>
    </div>
  );
};

export default PDFlowDesigner; 