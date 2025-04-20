// 设备分组
export interface DeviceGroup {
  id: string;
  name: string;
  description?: string;
  memberCount: number;
  createdAt: string;
  updatedAt: string;
}

// 设备成员
export interface DeviceMember {
  id: string;
  name: string;
  ip: string;
  deviceType: string;
  status: string;
  description?: string;
} 