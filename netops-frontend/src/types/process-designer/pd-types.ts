import { Node, Edge } from 'reactflow';

// 节点类型定义
export enum PDNodeType {
  // 基础节点
  START = 'pd_start',
  END = 'pd_end',
  TASK = 'pd_task',
  CONDITION = 'pd_condition',
  LOOP = 'pd_loop',
  
  // 网络自动化节点
  DEVICE_CONNECT = 'pd_device_connect',
  CONFIG_DEPLOY = 'pd_config_deploy',
  COMMAND_EXECUTE = 'pd_command_execute',
  CONFIG_BACKUP = 'pd_config_backup',
  STATUS_CHECK = 'pd_status_check'
}

// 节点数据接口
export interface PDNodeData {
  type: PDNodeType;
  label: string;
  description?: string;
  config: {
    parameters?: Record<string, any>;
    conditions?: Record<string, any>;
    errorHandling?: {
      retryCount?: number;
      retryInterval?: number;
      onError?: string;
    };
    timeout?: number;
  };
}

// 自定义节点接口
export interface PDCustomNode extends Node {
  data: PDNodeData;
}

// 流程定义接口
export interface PDFlowDefinition {
  id: string;
  name: string;
  description?: string;
  nodes: PDCustomNode[];
  edges: Edge[];
  createdAt: Date;
  updatedAt: Date;
  version: number;
}

// 节点配置面板属性
export interface PDNodeConfigProps {
  node: PDCustomNode;
  onChange: (node: PDCustomNode) => void;
}

// 工具栏配置
export interface PDToolbarConfig {
  onSave: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onValidate: () => void;
  onExecute: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onToggleNodePanel?: () => void;
  onToggleConfigPanel?: () => void;
}

export interface PDFlowDesignerProps {
  initialData: ProcessDefinition;
  readOnly?: boolean;
  executionData?: {
    nodeStates: Record<string, any>;
    variables: Record<string, any>;
  };
  onSave?: (data: ProcessDefinition) => void;
  onCancel?: () => void;
}

export interface ProcessDefinition {
  id: string;
  name: string;
  description: string;
  version: number;
  status: 'draft' | 'published' | 'disabled';
  nodes: Node[];
  edges: Edge[];
  createdAt: string;
  updatedAt: string;
}

export interface ProcessInstance {
  id: string;
  processDefinitionId: string;
  name: string;
  variables: Record<string, any>;
  status: 'running' | 'suspended' | 'completed' | 'failed';
  nodeStates: Record<string, any>;
  startedAt: string;
  endedAt?: string;
}

export interface PDNodePanelProps {
  onDragStart: (event: React.DragEvent, nodeType: string) => void;
}

export interface PDValidationPanelProps {
  nodes: Node[];
  edges: Edge[];
  onClose: () => void;
}

export interface PDNodeConfigPanelProps {
  node: Node;
  onChange: (node: Node) => void;
  onClose: () => void;
} 