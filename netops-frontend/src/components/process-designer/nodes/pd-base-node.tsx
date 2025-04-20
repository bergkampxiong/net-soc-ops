import React from 'react';
import { Handle, Position } from 'reactflow';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDBaseNodeProps {
  data: PDNodeData;
  type: string;
  className?: string;
  icon: React.ReactNode;
}

export const PDBaseNode: React.FC<PDBaseNodeProps> = ({
  data,
  className = '',
  icon,
}) => {
  return (
    <div className={`pd-node ${className}`}>
      <Handle
        type="target"
        position={Position.Top}
        className="pd-handle pd-handle-top"
        isConnectable={true}
        style={{ background: '#fff', border: '1px solid #1890ff' }}
      />
      
      <div className="node-content">
        {icon}
        <div className="node-info">
          <div className="node-title">{data.label}</div>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="pd-handle pd-handle-bottom"
        isConnectable={true}
        style={{ background: '#fff', border: '1px solid #1890ff' }}
      />
    </div>
  );
}; 