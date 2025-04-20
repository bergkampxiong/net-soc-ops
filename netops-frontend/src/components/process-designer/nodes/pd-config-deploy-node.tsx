import React from 'react';
import { UploadOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDConfigDeployNodeProps {
  data: PDNodeData;
}

export const PDConfigDeployNode: React.FC<PDConfigDeployNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="配置下发节点"
      className="pd-config-deploy-node"
      icon={<UploadOutlined style={{ fontSize: 16, color: '#eb2f96' }} />}
    />
  );
}; 