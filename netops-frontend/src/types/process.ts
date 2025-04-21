import { Node } from 'reactflow';

// 基础节点属性
export interface BaseNodeData {
  label: string;
  isConfigured?: boolean;
}

// 设备连接节点数据
export interface DeviceConnectData extends BaseNodeData {
  label: string;
  sshConfigId?: number;
  deviceGroupId?: number;
  selectedDevices?: string[];
  isConfigured?: boolean;
  poolConfig?: {
    maxConnections: number;
    minIdle: number;
    idleTimeout: number;
    connectionTimeout: number;
    isActive: boolean;
  };
}

// 节点属性
export interface NodeProps<T = any> {
  id: string;
  data: T;
  selected: boolean;
  onClick?: () => void;
}

// 节点类型
export type ProcessNode = Node<NodeProps>; 