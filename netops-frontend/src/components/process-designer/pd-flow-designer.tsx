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
import { Button, Space, Divider, Modal, Form, Input, message } from 'antd';
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
  AimOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import 'reactflow/dist/style.css';
import './styles/pd-flow-designer.css';
import request from '../../utils/request';
import { processCodeGeneratorApi, processDefinitionApi } from '../../api/process-designer';
import { saveProcessDesign, updateProcessDesign, ProcessDesignerSaveRequest } from '../../api/process-designer';

// 导入所有节点组件
import { PDStartNode } from './nodes/pd-start-node';
import { PDEndNode } from './nodes/pd-end-node';
import { PDTaskNode } from './nodes/pd-task-node';
import { PDConditionNode } from './nodes/pd-condition-node';
import { PDLoopNode } from './nodes/pd-loop-node';
import { PDDeviceConnectNode } from './nodes/pd-device-connect-node';
import { PDConfigDeployNode } from './nodes/pd-config-deploy-node';
import { PDConfigBackupNode } from './nodes/pd-config-backup-node';
import { PDStatusCheckNode } from './nodes/pd-status-check-node';

// 导入所有配置面板组件
import { PDDeviceConnectPanel } from './panels/pd-device-connect-panel';
import { PDTaskPanel } from './panels/pd-task-panel';
import { PDConditionPanel } from './panels/pd-condition-panel';
import { PDConfigDeployPanel } from './panels/pd-config-deploy-panel';
import { PDConfigBackupPanel } from './panels/pd-config-backup-panel';
import { PDStatusCheckPanel } from './panels/pd-status-check-panel';
import { PDScanTargetPanel } from './panels/pd-scan-target-panel';
import { PDPenetrationTestPanel } from './panels/pd-penetration-test-panel';
import { PDScanTargetNode } from './nodes/pd-scan-target-node';
import { PDPenetrationTestNode } from './nodes/pd-penetration-test-node';

// 节点类型映射
const nodeTypes = {
  start: PDStartNode,
  end: PDEndNode,
  task: PDTaskNode,
  condition: PDConditionNode,
  loop: PDLoopNode,
  deviceConnect: PDDeviceConnectNode,
  configDeploy: PDConfigDeployNode,
  configBackup: PDConfigBackupNode,
  statusCheck: PDStatusCheckNode,
  scanTarget: PDScanTargetNode,
  penetrationTest: PDPenetrationTestNode,
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
    type: 'configBackup',
    title: '配置备份',
    icon: <SaveOutlined style={{ fontSize: 26, color: '#2f54eb' }} />,
  },
  {
    type: 'statusCheck',
    title: '状态检查',
    icon: <CheckCircleOutlined style={{ fontSize: 26, color: '#52c41a' }} />,
  },
  {
    type: 'scanTarget',
    title: '扫描目标',
    icon: <AimOutlined style={{ fontSize: 26, color: '#722ed1' }} />,
  },
  {
    type: 'penetrationTest',
    title: '渗透测试',
    icon: <SafetyCertificateOutlined style={{ fontSize: 26, color: '#cf1322' }} />,
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
  },
  {
    id: 'end-1',
    type: 'end',
    position: { x: 100, y: 220 },
    data: {
      label: '结束节点',
      icon: <CloseOutlined style={{ fontSize: 16, color: '#ff4d4f' }} />
    }
  }
];

interface NodeData {
  label: string;
  isConfigured?: boolean;
  configured?: boolean;
  [key: string]: any;
}

interface CustomNode extends Node {
  data: NodeData;
}

interface PDFlowDesignerProps {
  processId?: string | null;
  onDirtyChange?: (isDirty: boolean) => void;
  initialData?: {
    nodes: Node[];
    edges: Edge[];
  };
}

const FlowDesigner: React.FC<PDFlowDesignerProps> = ({ processId, onDirtyChange, initialData }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialData?.nodes || initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialData?.edges || []);
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
  const [showConfigBackupPanel, setShowConfigBackupPanel] = useState(false);
  const [showStatusCheckPanel, setShowStatusCheckPanel] = useState(false);
  const [selectedTaskNode, setSelectedTaskNode] = useState<Node | null>(null);
  const [selectedConditionNode, setSelectedConditionNode] = useState<Node | null>(null);
  const [selectedConfigDeployNode, setSelectedConfigDeployNode] = useState<Node | null>(null);
  const [selectedConfigBackupNode, setSelectedConfigBackupNode] = useState<Node | null>(null);
  const [selectedStatusCheckNode, setSelectedStatusCheckNode] = useState<Node | null>(null);
  const [showScanTargetPanel, setShowScanTargetPanel] = useState(false);
  const [selectedScanTargetNode, setSelectedScanTargetNode] = useState<Node | null>(null);
  const [showPenetrationTestPanel, setShowPenetrationTestPanel] = useState(false);
  const [selectedPenetrationTestNode, setSelectedPenetrationTestNode] = useState<Node | null>(null);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveForm] = Form.useForm();
  const [isSaving, setIsSaving] = useState(false);

  // 保存时用 ref 读取最新 nodes/edges，避免闭包拿到旧状态导致渗透测试等节点未被保存
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  nodesRef.current = nodes;
  edgesRef.current = edges;

  // 任一配置抽屉打开时禁用键盘删除，避免配置过程中节点被误删
  const isAnyConfigPanelOpen =
    showDeviceConnectPanel ||
    showTaskPanel ||
    showConditionPanel ||
    showConfigDeployPanel ||
    showConfigBackupPanel ||
    showStatusCheckPanel ||
    showScanTargetPanel ||
    showPenetrationTestPanel;

  // 处理键盘删除事件：仅在焦点在画布上且未打开配置面板时删除节点
  const onKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key !== 'Delete' && event.key !== 'Backspace') return;
      if (isAnyConfigPanelOpen) return;
      const target = event.target as HTMLElement;
      if (!target) return;
      const tagName = target.tagName?.toUpperCase();
      const isInputLike =
        tagName === 'INPUT' ||
        tagName === 'TEXTAREA' ||
        tagName === 'SELECT' ||
        target.isContentEditable;
      if (isInputLike) return;
      setNodes((nodes) => nodes.filter((node) => !node.selected));
      setEdges((edges) => edges.filter((edge) => !edge.selected));
    },
    [
      setNodes,
      setEdges,
      isAnyConfigPanelOpen,
    ]
  );

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
    } else if (node.type === 'configBackup') {
      setSelectedConfigBackupNode(node);
      setShowConfigBackupPanel(true);
    } else if (node.type === 'statusCheck') {
      setSelectedStatusCheckNode(node);
      setShowStatusCheckPanel(true);
    } else if (node.type === 'scanTarget') {
      setSelectedScanTargetNode(node);
      setShowScanTargetPanel(true);
    } else if (node.type === 'penetrationTest') {
      setSelectedPenetrationTestNode(node);
      setShowPenetrationTestPanel(true);
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

  // 验证流程完整性（若存在渗透测试节点则不强制要求设备连接与配置下发/备份）
  const validateProcess = () => {
    const hasStartNode = nodes.some(node => node.type === 'start');
    if (!hasStartNode) {
      message.error('流程必须包含开始节点');
      return false;
    }
    const hasEndNode = nodes.some(node => node.type === 'end');
    if (!hasEndNode) {
      message.error('流程必须包含结束节点');
      return false;
    }
    const hasPenetrationTest = nodes.some(node => node.type === 'penetrationTest');
    if (!hasPenetrationTest) {
      const hasDeviceConnect = nodes.some(node => node.type === 'deviceConnect');
      if (!hasDeviceConnect) {
        message.error('流程必须包含至少一个设备连接节点');
        return false;
      }
      const hasConfigDeploy = nodes.some(node => node.type === 'configDeploy');
      const hasConfigBackup = nodes.some(node => node.type === 'configBackup');
      if (!hasConfigDeploy && !hasConfigBackup) {
        message.error('流程必须包含至少一个配置下发节点或配置备份节点');
        return false;
      }
    }
    const unconfiguredNodes = nodes.filter(node => {
      if (node.type === 'start' || node.type === 'end') return false;
      if (node.type === 'scanTarget' || node.type === 'penetrationTest') return false;
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

  // 处理保存确认（使用 ref 中的最新 nodes/edges，避免闭包陈旧导致刚添加的节点未写入）
  const handleSaveConfirm = async () => {
    try {
      const values = await saveForm.validateFields();
      setIsSaving(true);

      const currentNodes = nodesRef.current;
      const currentEdges = edgesRef.current;

      // 确保节点的数据被正确保存
      const nodesWithData = currentNodes.map(node => {
        const nodeData = (node as CustomNode).data || {};
        const config = {
          ...nodeData,
          isConfigured: (nodeData as any).isConfigured || false,
          configured: (nodeData as any).configured || false
        };
        return {
          ...node,
          data: config
        };
      });

      const saveData: ProcessDesignerSaveRequest = {
        name: values.name,
        description: values.description,
        nodes: nodesWithData,
        edges: currentEdges,
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
      console.error('保存失败:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleValidate = () => {
    message.success('验证通过');
  };

  const handleExecute = async () => {
    if (!processId) {
      message.warning('请先保存流程后再生成代码');
      return;
    }
    try {
      const response = await processCodeGeneratorApi.generate(processId);
      const blob = response.data instanceof Blob ? response.data : new Blob([String(response.data)], { type: 'text/plain;charset=utf-8' });
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
          configured: true,
          isConfigured: true
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

  // 处理扫描目标节点配置保存
  const handleScanTargetSave = useCallback((data: any) => {
    if (selectedScanTargetNode) {
      const updatedNode = {
        ...selectedScanTargetNode,
        data: { ...selectedScanTargetNode.data, ...data, configured: true },
      };
      setNodes((nds) =>
        nds.map((node) => (node.id === selectedScanTargetNode.id ? updatedNode : node))
      );
      setShowScanTargetPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedScanTargetNode, setNodes, onDirtyChange]);

  // 处理渗透测试节点配置保存
  const handlePenetrationTestSave = useCallback((data: any) => {
    if (selectedPenetrationTestNode) {
      const updatedNode = {
        ...selectedPenetrationTestNode,
        data: { ...selectedPenetrationTestNode.data, ...data, configured: true },
      };
      setNodes((nds) =>
        nds.map((node) => (node.id === selectedPenetrationTestNode.id ? updatedNode : node))
      );
      setShowPenetrationTestPanel(false);
      setIsDirty(true);
      onDirtyChange?.(true);
    }
  }, [selectedPenetrationTestNode, setNodes, onDirtyChange]);

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
      const loadProcessData = async () => {
        try {
          const response = await processDefinitionApi.getDetail(processId);
          const processDefinition = response.data.data;
          
          if (processDefinition.nodes && processDefinition.edges) {
            // 确保节点数据被正确加载
            const nodesWithData = processDefinition.nodes.map((node: any) => {
              // 保持原始节点类型
              const nodeType = node.type;
              const nodeData = node.data || {};
              
              return {
                id: node.id,
                type: nodeType,
                position: node.position || { x: 0, y: 0 },
                data: {
                  ...nodeData,
                  label: nodeData.label || '未命名节点',
                  isConfigured: nodeData.isConfigured || false,
                  configured: nodeData.configured || false,
                  // 保留原始配置数据
                  ...(nodeData.sshConfig && { sshConfig: nodeData.sshConfig }),
                  ...(nodeData.deviceGroup && { deviceGroup: nodeData.deviceGroup }),
                  ...(nodeData.selectedDevices && { selectedDevices: nodeData.selectedDevices }),
                  ...(nodeData.configName && { configName: nodeData.configName }),
                  ...(nodeData.configContent && { configContent: nodeData.configContent })
                }
              };
            });
            
            // 确保边数据正确
            const edgesWithData = processDefinition.edges.map((edge: any) => ({
              id: edge.id,
              source: edge.source,
              target: edge.target,
              type: 'smoothstep',
              style: { strokeWidth: 1.5, stroke: '#1890ff' },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#1890ff',
                width: 20,
                height: 20
              }
            }));
            
            setNodes(nodesWithData);
            setEdges(edgesWithData);
          }
          
          setIsDirty(false);
          onDirtyChange?.(false);
          previousProcessId.current = processId;
        } catch (error) {
          console.error('加载流程数据失败:', error);
          message.error('加载流程数据失败');
        }
      };

      loadProcessData();
    } else if (initialData) {
      // 如果提供了initialData，直接使用它来初始化节点和边
      setNodes(initialData.nodes);
      setEdges(initialData.edges);
      setIsDirty(false);
      onDirtyChange?.(false);
    }
  }, [processId, initialData, setNodes, setEdges, onDirtyChange]);

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
            onClick={async () => {
              if (processId && isDirty) {
                try {
                  const response = await processDefinitionApi.getDetail(processId);
                  const pd = response.data.data;
                  if (pd?.nodes?.length && pd?.edges) {
                    const loadedNodes = pd.nodes.map((node: any) => ({
                      id: node.id,
                      type: node.type,
                      position: node.position || { x: 0, y: 0 },
                      data: { ...(node.data || {}), label: node.data?.label || '未命名节点' }
                    }));
                    const loadedEdges = pd.edges.map((edge: any) => ({
                      id: edge.id,
                      source: edge.source,
                      target: edge.target,
                      type: 'smoothstep',
                      style: { strokeWidth: 1.5, stroke: '#1890ff' },
                      markerEnd: { type: MarkerType.ArrowClosed, color: '#1890ff', width: 20, height: 20 }
                    }));
                    setNodes(loadedNodes);
                    setEdges(loadedEdges);
                  }
                  setIsDirty(false);
                  onDirtyChange?.(false);
                  message.success('已从服务器重新加载');
                } catch {
                  message.error('重新加载失败');
                }
              }
            }}
            disabled={!isDirty}
          >
            重置
          </Button>
          <Button icon={<CheckOutlined />} onClick={handleValidate}>
            验证
          </Button>
          <Button icon={<CodeOutlined />} onClick={handleExecute} disabled={!processId} title={!processId ? '请先保存流程' : undefined}>
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

      <PDConfigBackupPanel
        visible={showConfigBackupPanel}
        onClose={() => setShowConfigBackupPanel(false)}
        initialData={selectedConfigBackupNode?.data}
        onSave={handleConfigBackupSave}
        deviceConnectNodes={nodes.filter((n) => n.type === 'deviceConnect').map((n) => ({ id: n.id, label: (n as CustomNode).data?.label || n.id }))}
      />

      <PDStatusCheckPanel
        visible={showStatusCheckPanel}
        onClose={() => setShowStatusCheckPanel(false)}
        initialData={selectedStatusCheckNode?.data}
        onSave={handleStatusCheckSave}
      />

      <PDScanTargetPanel
        visible={showScanTargetPanel}
        onClose={() => setShowScanTargetPanel(false)}
        initialData={selectedScanTargetNode?.data}
        onSave={handleScanTargetSave}
      />

      <PDPenetrationTestPanel
        visible={showPenetrationTestPanel}
        onClose={() => setShowPenetrationTestPanel(false)}
        initialData={selectedPenetrationTestNode?.data}
        onSave={handlePenetrationTestSave}
        scanTargetNodes={nodes.filter((n) => n.type === 'scanTarget').map((n) => ({ id: n.id, label: (n as CustomNode).data?.label || n.id, targetType: (n as CustomNode).data?.targetType, staticOnly: (n as CustomNode).data?.staticOnly }))}
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
const PDFlowDesigner: React.FC<PDFlowDesignerProps> = ({ processId, onDirtyChange, initialData }) => {
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlowProvider>
        <FlowDesigner processId={processId} onDirtyChange={onDirtyChange} initialData={initialData} />
      </ReactFlowProvider>
    </div>
  );
};

export default PDFlowDesigner; 