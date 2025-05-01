import React, { useState, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  NodeChange,
  EdgeChange,
  PanelPosition,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { PDFlowDesignerProps } from '../../types/process-designer/pd-types';
import { PDNodePanel } from './panels/pd-node-panel';
import { PDValidationPanel } from './panels/pd-validation-panel';
import { PDToolbar } from './toolbar/pd-toolbar';
import { PDNodeConfigPanel } from './panels/pd-node-config-panel';
import {
  PDStartNode,
  PDEndNode,
  PDTaskNode,
  PDConditionNode,
  PDLoopNode,
  PDDeviceConnectNode,
  PDConfigDeployNode,
  PDCommandExecuteNode,
  PDConfigBackupNode,
  PDStatusCheckNode,
} from './nodes';
import './styles/pd-flow-designer.css';
import { message, Modal } from 'antd';
import { processCodeGeneratorApi } from '../../api/process-designer';

const nodeTypes = {
  start: PDStartNode,
  end: PDEndNode,
  task: PDTaskNode,
  condition: PDConditionNode,
  loop: PDLoopNode,
  deviceConnect: PDDeviceConnectNode,
  configDeploy: PDConfigDeployNode,
  commandExecute: PDCommandExecuteNode,
  configBackup: PDConfigBackupNode,
  statusCheck: PDStatusCheckNode,
};

export const PDFlowDesigner: React.FC<PDFlowDesignerProps> = ({
  initialData,
  readOnly = false,
  executionData,
  onSave,
  onCancel,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialData.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialData.edges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showNodePanel, setShowNodePanel] = useState(true);
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [showValidationPanel, setShowValidationPanel] = useState(false);
  const [history, setHistory] = useState<Array<{ nodes: Node[]; edges: Edge[] }>>([{ nodes, edges }]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [isValid, setIsValid] = useState(false);

  // 处理节点变化
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);
      // 更新历史记录
      const newNodes = changes.reduce((acc, change) => {
        if ('id' in change) {
          if (change.type === 'remove') {
            return acc.filter((node) => node.id !== change.id);
          }
          if (change.type === 'position' || change.type === 'dimensions' || change.type === 'select') {
            return acc.map((node) =>
              node.id === change.id ? { ...node, ...change } : node
            );
          }
        }
        return acc;
      }, nodes);
      setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes: newNodes, edges }]);
      setHistoryIndex((prev) => prev + 1);
    },
    [nodes, edges, historyIndex, onNodesChange]
  );

  // 处理边变化
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChange(changes);
      // 更新历史记录
      const newEdges = changes.reduce((acc, change) => {
        if ('id' in change) {
          if (change.type === 'remove') {
            return acc.filter((edge) => edge.id !== change.id);
          }
          if (change.type === 'select') {
            return acc.map((edge) =>
              edge.id === change.id ? { ...edge, ...change } : edge
            );
          }
        }
        return acc;
      }, edges);
      setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes, edges: newEdges }]);
      setHistoryIndex((prev) => prev + 1);
    },
    [nodes, edges, historyIndex, onEdgesChange]
  );

  // 处理连接
  const handleConnect = useCallback(
    (connection: Connection) => {
      const newEdge = addEdge(connection, edges);
      setEdges(newEdge);
      // 更新历史记录
      setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes, edges: newEdge }]);
      setHistoryIndex((prev) => prev + 1);
    },
    [nodes, edges, historyIndex, setEdges]
  );

  // 处理节点选择
  const handleNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (!readOnly) {
        setSelectedNode(node);
        setShowConfigPanel(true);
      }
    },
    [readOnly]
  );

  // 处理节点配置更新
  const handleNodeConfigUpdate = useCallback(
    (updatedNode: Node) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === updatedNode.id ? updatedNode : node
        )
      );
      // 更新历史记录
      setHistory((prev) => [...prev.slice(0, historyIndex + 1), { 
        nodes: nodes.map((node) => node.id === updatedNode.id ? updatedNode : node),
        edges 
      }]);
      setHistoryIndex((prev) => prev + 1);
    },
    [nodes, edges, historyIndex, setNodes]
  );

  // 处理撤销
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const prevState = history[historyIndex - 1];
      setNodes(prevState.nodes);
      setEdges(prevState.edges);
      setHistoryIndex((prev) => prev - 1);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  // 处理重做
  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextState = history[historyIndex + 1];
      setNodes(nextState.nodes);
      setEdges(nextState.edges);
      setHistoryIndex((prev) => prev + 1);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  // 处理保存
  const handleSave = useCallback(() => {
    if (onSave) {
      onSave({
        ...initialData,
        nodes,
        edges,
      });
    }
  }, [initialData, nodes, edges, onSave]);

  // 处理验证
  const handleValidate = useCallback(async () => {
    try {
      const response = await processCodeGeneratorApi.validate(initialData.id);
      const { isValid, errors } = response.data.data;
      setIsValid(isValid);
      if (isValid) {
        message.success('流程验证通过');
      } else {
        message.error('流程验证失败：' + errors.join(', '));
      }
    } catch (error) {
      message.error('验证失败');
    }
  }, [initialData.id]);

  // 处理代码生成
  const handleExecute = useCallback(async () => {
    if (!isValid) {
      message.warning('请先通过流程验证');
      return;
    }

    try {
      const response = await processCodeGeneratorApi.generate(initialData.id);
      const code = response.data.data;
      
      // 创建下载链接
      const blob = new Blob([code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${initialData.name}_generated.py`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      message.success('代码生成成功');
    } catch (error) {
      message.error('代码生成失败');
    }
  }, [initialData.id, initialData.name, isValid]);

  // 处理拖拽开始
  const handleDragStart = useCallback((event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
  }, []);

  return (
    <div className="pd-flow-designer">
      <PDToolbar
        onSave={handleSave}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onValidate={handleValidate}
        onExecute={handleExecute}
        canUndo={historyIndex > 0}
        canRedo={historyIndex < history.length - 1}
      />

      <div className="pd-flow-container">
        {!readOnly && showNodePanel && (
          <div className="pd-node-panel-container">
            <PDNodePanel onDragStart={handleDragStart} />
          </div>
        )}

        <div className="pd-flow-content">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-right"
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>

        {!readOnly && showConfigPanel && selectedNode && (
          <div className="pd-config-panel-container">
            <PDNodeConfigPanel
              node={selectedNode}
              onChange={handleNodeConfigUpdate}
              onClose={() => {
                setSelectedNode(null);
                setShowConfigPanel(false);
              }}
            />
          </div>
        )}

        {showValidationPanel && (
          <div className="pd-validation-panel-container">
            <PDValidationPanel
              nodes={nodes}
              edges={edges}
              onClose={() => setShowValidationPanel(false)}
            />
          </div>
        )}
      </div>
    </div>
  );
}; 