import React from 'react';
import { ConsoleSqlOutlined } from '@ant-design/icons';
import { PDBaseNode } from './pd-base-node';
import { PDNodeData } from '../../../types/process-designer/pd-types';

interface PDCommandExecuteNodeProps {
  data: PDNodeData;
}

export const PDCommandExecuteNode: React.FC<PDCommandExecuteNodeProps> = ({ data }) => {
  return (
    <PDBaseNode
      data={data}
      type="命令执行节点"
      className="pd-command-execute-node"
      icon={<ConsoleSqlOutlined style={{ fontSize: 16, color: '#fa8c16' }} />}
    />
  );
}; 