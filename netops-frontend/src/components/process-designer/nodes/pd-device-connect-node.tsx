import React from 'react';
import { Handle, Position } from 'reactflow';
import { CloudServerOutlined } from '@ant-design/icons';

interface DeviceConnectData {
  label: string;
  sshConfigId?: string;
  deviceGroupId?: string;
  selectedDevices?: string[];
  isConfigured?: boolean;  // 新增标记，用于显示是否已配置
}

interface DeviceConnectNodeProps {
  id: string;
  data: DeviceConnectData;
  selected: boolean;
  onClick?: () => void;
}

export const PDDeviceConnectNode: React.FC<DeviceConnectNodeProps> = ({ 
  data,
  selected,
  onClick 
}) => {
  // 根据配置状态显示不同的样式
  const nodeStyle = data.isConfigured ? { borderColor: '#52c41a' } : undefined;

  return (
    <div className="pd-device-connect-node" style={nodeStyle} onClick={onClick}>
      <div className="node-content">
        <CloudServerOutlined style={{ color: data.isConfigured ? '#52c41a' : '#13c2c2' }} />
        <div className="node-title">
          {data.label}
          {data.isConfigured && <span className="node-status">（已配置）</span>}
        </div>
      </div>
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}; 