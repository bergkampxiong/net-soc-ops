import React from 'react';
import { Card, List, Button, Tag, Typography } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { Node, Edge } from 'reactflow';
import { PDCustomNode } from '../../../types/process-designer/pd-types';

const { Text } = Typography;

interface ValidationResult {
  type: 'error' | 'warning' | 'info';
  message: string;
  nodeId?: string;
  edgeId?: string;
}

interface PDValidationPanelProps {
  nodes: Node[];
  edges: Edge[];
  onClose: () => void;
}

export const PDValidationPanel: React.FC<PDValidationPanelProps> = ({
  nodes,
  edges,
  onClose,
}) => {
  const [validationResults, setValidationResults] = React.useState<ValidationResult[]>([]);

  // 验证流程
  React.useEffect(() => {
    const results: ValidationResult[] = [];

    // 1. 检查是否有开始节点
    const hasStartNode = nodes.some((node) => node.type === 'pd_start');
    if (!hasStartNode) {
      results.push({
        type: 'error',
        message: '流程缺少开始节点',
      });
    }

    // 2. 检查是否有结束节点
    const hasEndNode = nodes.some((node) => node.type === 'pd_end');
    if (!hasEndNode) {
      results.push({
        type: 'error',
        message: '流程缺少结束节点',
      });
    }

    // 3. 检查节点连接
    nodes.forEach((node) => {
      const nodeEdges = edges.filter(
        (edge) => edge.source === node.id || edge.target === node.id
      );

      if (node.type === 'pd_start') {
        // 开始节点不应该有入边
        const hasIncomingEdge = edges.some((edge) => edge.target === node.id);
        if (hasIncomingEdge) {
          results.push({
            type: 'error',
            message: '开始节点不应该有入边',
            nodeId: node.id,
          });
        }
      } else if (node.type === 'pd_end') {
        // 结束节点不应该有出边
        const hasOutgoingEdge = edges.some((edge) => edge.source === node.id);
        if (hasOutgoingEdge) {
          results.push({
            type: 'error',
            message: '结束节点不应该有出边',
            nodeId: node.id,
          });
        }
      } else {
        // 其他节点应该有入边和出边
        const hasIncomingEdge = edges.some((edge) => edge.target === node.id);
        const hasOutgoingEdge = edges.some((edge) => edge.source === node.id);

        if (!hasIncomingEdge) {
          results.push({
            type: 'error',
            message: '节点缺少入边',
            nodeId: node.id,
          });
        }
        if (!hasOutgoingEdge) {
          results.push({
            type: 'error',
            message: '节点缺少出边',
            nodeId: node.id,
          });
        }
      }
    });

    // 4. 检查条件节点
    nodes.forEach((node) => {
      if (node.type === 'pd_condition') {
        const conditionNode = node as PDCustomNode;
        const outgoingEdges = edges.filter((edge) => edge.source === node.id);
        
        // 条件节点应该有true和false两个出边
        const hasTrueEdge = outgoingEdges.some((edge) => edge.id === 'true');
        const hasFalseEdge = outgoingEdges.some((edge) => edge.id === 'false');

        if (!hasTrueEdge || !hasFalseEdge) {
          results.push({
            type: 'error',
            message: '条件节点必须同时有true和false两个出边',
            nodeId: node.id,
          });
        }
      }
    });

    // 5. 检查循环节点
    nodes.forEach((node) => {
      if (node.type === 'pd_loop') {
        const loopNode = node as PDCustomNode;
        const outgoingEdges = edges.filter((edge) => edge.source === node.id);
        
        // 循环节点应该有continue和break两个出边
        const hasContinueEdge = outgoingEdges.some((edge) => edge.id === 'continue');
        const hasBreakEdge = outgoingEdges.some((edge) => edge.id === 'break');

        if (!hasContinueEdge || !hasBreakEdge) {
          results.push({
            type: 'error',
            message: '循环节点必须同时有continue和break两个出边',
            nodeId: node.id,
          });
        }
      }
    });

    setValidationResults(results);
  }, [nodes, edges]);

  const getTagColor = (type: ValidationResult['type']) => {
    switch (type) {
      case 'error':
        return 'red';
      case 'warning':
        return 'orange';
      case 'info':
        return 'blue';
      default:
        return 'default';
    }
  };

  return (
    <Card
      title="流程验证"
      extra={
        <Button type="text" icon={<CloseOutlined />} onClick={onClose} />
      }
      className="pd-validation-panel"
    >
      <List
        dataSource={validationResults}
        renderItem={(item) => (
          <List.Item>
            <Tag color={getTagColor(item.type)}>{item.type.toUpperCase()}</Tag>
            <Text>{item.message}</Text>
            {(item.nodeId || item.edgeId) && (
              <Text type="secondary">
                {item.nodeId ? `节点ID: ${item.nodeId}` : `连接ID: ${item.edgeId}`}
              </Text>
            )}
          </List.Item>
        )}
      />
    </Card>
  );
}; 