// SSH配置
export interface SSHConfig {
  id: string;
  name: string;
  deviceType: string;
  credentialId: number;
  port: number;
  enableSecret?: string;
  globalDelayFactor: number;
  authTimeout: number;
  bannerTimeout: number;
  fastCli: boolean;
  sessionTimeout: number;
  connTimeout: number;
  keepalive: number;
  verbose: boolean;
  createdAt: string;
  updatedAt: string;
}

// SSH凭证
export interface SSHCredential {
  id: string;
  name: string;
  username: string;
  password: string;
  enablePassword?: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
} 