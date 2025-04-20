import React from 'react';
import { CheckCircleOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDStatusCheckNodeProps {
  data: PDNodeData;
}

export const PDStatusCheckNode: React.FC<PDStatusCheckNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="状态检查节点"
      className="pd-status-check-node"
      icon={<CheckCircleOutlined style={{ fontSize: 16, color: '#52c41a' }} />}
    />
  );
}; 