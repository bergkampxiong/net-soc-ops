import React from 'react';
import { DownloadOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDConfigBackupNodeProps {
  data: PDNodeData;
}

export const PDConfigBackupNode: React.FC<PDConfigBackupNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="配置备份节点"
      className="pd-config-backup-node"
      icon={<DownloadOutlined style={{ fontSize: 16, color: '#2f54eb' }} />}
    />
  );
}; 