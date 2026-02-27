import React from 'react';
import { AimOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import type { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDScanTargetNodeProps {
  data: PDNodeData;
}

export const PDScanTargetNode: React.FC<PDScanTargetNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="扫描目标"
      className="pd-scan-target-node"
      icon={<AimOutlined style={{ fontSize: 16, color: '#722ed1' }} />}
    />
  );
};
