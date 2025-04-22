export interface ConfigBackupNode {
  id: string;
  type: 'configBackup';
  name: string;
  description?: string;
  backupType: 'full' | 'incremental';
  backupPath: string;
  compress: boolean;
  retentionDays: number;
  isConfigured: boolean;
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

export interface CommandExecuteNode {
  id: string;
  type: 'commandExecute';
  name: string;
  description?: string;
  commandType: 'cli' | 'script';
  commandContent: string;
  timeout: number;
  expectedOutput?: string;
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