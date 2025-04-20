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
import { Button, Space, Divider } from 'antd';
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
import { PDDeviceConnectPanel } from './panels/pd-device-connect-panel';

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

  // 保存流程
  const handleSave = async () => {
    try {
      // TODO: 替换为实际的API调用
      // await saveProcess(processId, { nodes, edges });
      setIsDirty(false);
      onDirtyChange?.(false);
      message.success('保存成功');
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleValidate = () => {
    message.success('验证通过');
  };

  const handleExecute = () => {
    message.success('开始执行');
  };

  // 处理设备连接配置保存
  const handleDeviceConnectSave = useCallback((data: any) => {
    if (selectedDeviceNode) {
      const updatedNode = {
        ...selectedDeviceNode,
        data: {
          ...selectedDeviceNode.data,
          ...data
        }
      };
      setNodes((nds) =>
        nds.map((node) =>
          node.id === selectedDeviceNode.id ? updatedNode : node
        )
      );
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedDeviceNode, setNodes, onDirtyChange]);

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
          <Button icon={<PlayCircleOutlined />} onClick={handleExecute}>
            执行
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