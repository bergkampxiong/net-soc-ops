import React, { useState } from 'react';
import { Layout, Menu, Button, Space, message } from 'antd';
import {
  FileOutlined,
  SaveOutlined,
  HistoryOutlined,
  CommentOutlined,
  CompressOutlined,
  DownloadOutlined,
  RollbackOutlined
} from '@ant-design/icons';
import MonacoEditor from 'react-monaco-editor';
import { useParams } from 'react-router-dom';
import { getConfigContent, saveConfig, getConfigHistory, rollbackConfig } from '../../services/config';

const { Header, Sider, Content } = Layout;

interface ConfigHistory {
  id: number;
  version: string;
  timestamp: string;
  author: string;
  comment: string;
}

const ConfigEditor: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();
  const [content, setContent] = useState('');
  const [history, setHistory] = useState<ConfigHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);

  // 加载配置内容
  const loadConfig = async () => {
    try {
      const response = await getConfigContent(deviceId!);
      setContent(response.data.content);
    } catch (error) {
      message.error('加载配置失败');
    }
  };

  // 保存配置
  const handleSave = async () => {
    try {
      await saveConfig(deviceId!, content);
      message.success('保存成功');
    } catch (error) {
      message.error('保存失败');
    }
  };

  // 加载历史记录
  const loadHistory = async () => {
    try {
      const response = await getConfigHistory(deviceId!);
      setHistory(response.data);
      setShowHistory(true);
    } catch (error) {
      message.error('加载历史记录失败');
    }
  };

  // 回滚到指定版本
  const handleRollback = async (version: string) => {
    try {
      await rollbackConfig(deviceId!, version);
      message.success('回滚成功');
      loadConfig();
    } catch (error) {
      message.error('回滚失败');
    }
  };

  // 导出配置
  const handleExport = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `config_${deviceId}_${new Date().toISOString()}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // 注释/取消注释
  const handleComment = (comment: boolean) => {
    const editor = (window as any).monaco.editor.getEditors()[0];
    if (!editor) return;

    const selection = editor.getSelection();
    if (!selection) return;

    const model = editor.getModel();
    const lines = model.getLinesContent();
    const startLine = selection.startLineNumber;
    const endLine = selection.endLineNumber;

    const newLines = lines.map((line: string, index: number) => {
      if (index >= startLine - 1 && index <= endLine - 1) {
        return comment ? `! ${line}` : line.replace(/^!\s*/, '');
      }
      return line;
    });

    model.setValue(newLines.join('\n'));
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 16px' }}>
        <Space>
          <Button icon={<SaveOutlined />} onClick={handleSave}>
            保存
          </Button>
          <Button icon={<HistoryOutlined />} onClick={loadHistory}>
            历史记录
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出
          </Button>
          <Button icon={<CommentOutlined />} onClick={() => handleComment(true)}>
            注释
          </Button>
          <Button icon={<CommentOutlined />} onClick={() => handleComment(false)}>
            取消注释
          </Button>
        </Space>
      </Header>
      <Layout>
        <Sider width={300} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            defaultSelectedKeys={['1']}
            style={{ height: '100%', borderRight: 0 }}
          >
            <Menu.Item key="1" icon={<FileOutlined />}>
              当前配置
            </Menu.Item>
            <Menu.Item key="2" icon={<HistoryOutlined />}>
              历史版本
            </Menu.Item>
            <Menu.Item key="3" icon={<CompressOutlined />}>
              版本比较
            </Menu.Item>
          </Menu>
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content style={{ background: '#fff', padding: 24, margin: 0, minHeight: 280 }}>
            <MonacoEditor
              width="100%"
              height="600"
              language="cisco"
              theme="vs-dark"
              value={content}
              onChange={setContent}
              options={{
                selectOnLineNumbers: true,
                automaticLayout: true,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                roundedSelection: false,
                readOnly: false,
                cursorStyle: 'line'
              }}
            />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default ConfigEditor; 