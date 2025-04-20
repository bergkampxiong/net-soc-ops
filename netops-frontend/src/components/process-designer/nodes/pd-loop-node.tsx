import React from 'react';
import { Handle, Position } from 'reactflow';
import { SyncOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDLoopNodeProps {
  data: PDNodeData;
}

export const PDLoopNode: React.FC<PDLoopNodeProps> = ({ data }) => {
  return (
    <div className="pd-loop-node">
      <Handle
        type="target"
        position={Position.Top}
        className="pd-handle pd-handle-top"
      />
      
      <PDBaseNode
        data={data}
        type="循环节点"
        className="pd-loop-node-content"
        icon={<SyncOutlined style={{ fontSize: 16, color: '#722ed1' }} />}
      />

      <Handle
        type="source"
        position={Position.Left}
        id="break"
        className="pd-handle pd-handle-left"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="continue"
        className="pd-handle pd-handle-right"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="pd-handle pd-handle-bottom"
      />
    </div>
  );
}; 