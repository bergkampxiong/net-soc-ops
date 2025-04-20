import React from 'react';
import { PlayCircleOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDStartNodeProps {
  data: PDNodeData;
}

export const PDStartNode: React.FC<PDStartNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="开始节点"
      className="pd-node"
      icon={<PlayCircleOutlined style={{ fontSize: 16, color: '#1890ff' }} />}
    />
  );
}; 