import React from 'react';
import { Card, Collapse, Typography } from 'antd';
import { PDNodeType } from '../../../types/process-designer/pd-types';

const { Panel } = Collapse;
const { Text } = Typography;

interface PDNodePanelProps {
  onDragStart: (event: React.DragEvent, nodeType: string) => void;
}

// 节点分类
const nodeCategories = {
  basic: {
    title: '基础节点',
    nodes: [
      { type: PDNodeType.START, label: '开始节点' },
      { type: PDNodeType.END, label: '结束节点' },
      { type: PDNodeType.TASK, label: '任务节点' },
      { type: PDNodeType.CONDITION, label: '条件节点' },
      { type: PDNodeType.LOOP, label: '循环节点' },
    ],
  },
  network: {
    title: '网络自动化节点',
    nodes: [
      { type: PDNodeType.DEVICE_CONNECT, label: '设备连接节点' },
      { type: PDNodeType.CONFIG_DEPLOY, label: '配置下发节点' },
      { type: PDNodeType.COMMAND_EXECUTE, label: '命令执行节点' },
      { type: PDNodeType.CONFIG_BACKUP, label: '配置备份节点' },
      { type: PDNodeType.STATUS_CHECK, label: '状态检查节点' },
    ],
  },
};

export const PDNodePanel: React.FC<PDNodePanelProps> = ({ onDragStart }) => {
  return (
    <div className="pd-node-panel">
      <Card title="节点类型" className="pd-node-panel-card">
        <Collapse defaultActiveKey={['basic', 'network']}>
          {Object.entries(nodeCategories).map(([key, category]) => (
            <Panel header={category.title} key={key}>
              <div className="pd-node-list">
                {category.nodes.map((node) => (
                  <div
                    key={node.type}
                    className="pd-node-item"
                    draggable
                    onDragStart={(e) => onDragStart(e, node.type)}
                  >
                    <div className="pd-node-icon">
                      {/* TODO: 添加节点图标 */}
                    </div>
                    <Text>{node.label}</Text>
                  </div>
                ))}
              </div>
            </Panel>
          ))}
        </Collapse>
      </Card>
    </div>
  );
}; 