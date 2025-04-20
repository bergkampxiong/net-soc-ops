import React from 'react';
import { Handle, Position } from 'reactflow';
import { StopOutlined } from '@ant-design/icons';

interface NodeData {
  label: string;
  icon?: React.ReactNode;
}

export const PDEndNode: React.FC<{ data: NodeData }> = ({ data }) => {
  return (
    <div className="pd-node pd-end-node">
      <Handle type="target" position={Position.Top} className="pd-handle pd-handle-top" />
      <div className="node-content">
        <StopOutlined style={{ fontSize: 16, color: '#ff4d4f' }} />
        <div className="node-info">
          <div className="node-title">{data.label}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="pd-handle pd-handle-bottom" />
    </div>
  );
}; 