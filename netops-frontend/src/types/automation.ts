export interface ConfigBackupNode {
  id: string;
  type: 'configBackup';
  /** 设备来源：关联的设备连接节点 id，备份使用该节点的设备列表 */
  useDeviceFromNodeId?: string;
  /** 写入配置管理模块时的备注 */
  remark?: string;
  /** 备份命令覆盖（为空则按设备类型使用默认命令） */
  backupCommand?: string;
  isConfigured?: boolean;
  configured?: boolean;
}

export interface TaskNode {
  id: string;
  type: 'task';
  name: string;
  description?: string;
  timeout: number;
  retryCount: number;
  retryInterval: number;
  isConfigured: boolean;
}

export interface ConditionNode {
  id: string;
  type: 'condition';
  name: string;
  description?: string;
  conditionType: 'device_status' | 'config_check' | 'performance' | 'custom_script';
  expression: string;
  isConfigured: boolean;
}

export interface ConfigDeployNode {
  id: string;
  type: 'configDeploy';
  name: string;
  description?: string;
  configType: 'template' | 'custom';
  configContent: string;
  timeout: number;
  isConfigured: boolean;
}

export interface DeviceConnectNode {
  id: string;
  type: 'deviceConnect';
  name: string;
  description?: string;
  deviceType: 'cisco' | 'huawei' | 'h3c';
  protocol: 'ssh' | 'telnet';
  timeout: number;
  isConfigured: boolean;
}

export interface StatusCheckNode {
  id: string;
  type: 'statusCheck';
  name: string;
  description?: string;
  isConfigured: boolean;
} 