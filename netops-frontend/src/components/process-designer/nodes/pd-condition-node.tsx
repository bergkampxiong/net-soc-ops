import React from 'react';
import { Handle, Position } from 'reactflow';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDConditionNodeProps {
  data: PDNodeData;
}

export const PDConditionNode: React.FC<PDConditionNodeProps> = ({ data }) => {
  return (
    <div className="pd-condition-node">
      <Handle
        type="target"
        position={Position.Top}
        className="pd-handle pd-handle-top"
      />
      
      <PDBaseNode
        data={data}
        type="条件节点"
        className="pd-condition-node-content"
        icon={<QuestionCircleOutlined style={{ fontSize: 16, color: '#faad14' }} />}
      />

      <Handle
        type="source"
        position={Position.Left}
        id="false"
        className="pd-handle pd-handle-left"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="true"
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