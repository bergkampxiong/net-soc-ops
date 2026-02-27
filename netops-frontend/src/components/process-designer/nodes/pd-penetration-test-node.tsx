import React from 'react';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import type { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDPenetrationTestNodeProps {
  data: PDNodeData;
}

export const PDPenetrationTestNode: React.FC<PDPenetrationTestNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="渗透测试"
      className="pd-penetration-test-node"
      icon={<SafetyCertificateOutlined style={{ fontSize: 16, color: '#cf1322' }} />}
    />
  );
};
