import React from 'react';
import { ToolOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDTaskNodeProps {
  data: PDNodeData;
}

export const PDTaskNode: React.FC<PDTaskNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="任务节点"
      className="pd-task-node"
      icon={<ToolOutlined style={{ fontSize: 16, color: '#1890ff' }} />}
    />
  );
}; 