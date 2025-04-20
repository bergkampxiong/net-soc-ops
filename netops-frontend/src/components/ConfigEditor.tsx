import React, { useEffect, useRef } from 'react';
import MonacoEditor from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
import { message } from 'antd';

// 设备类型的语法定义
const deviceSyntax = {
  cisco_ios: {
    keywords: [
      'interface', 'ip', 'router', 'enable', 'configure', 'terminal', 'end',
      'show', 'write', 'reload', 'exit', 'hostname', 'password', 'access-list'
    ],
    commands: [
      { label: 'interface', detail: '配置接口', insertText: 'interface ${1:interface-name}\n  $0' },
      { label: 'ip address', detail: '配置IP地址', insertText: 'ip address ${1:ip-address} ${2:subnet-mask}' },
      { label: 'router ospf', detail: '配置OSPF路由', insertText: 'router ospf ${1:process-id}' }
    ]
  },
  huawei_vrp: {
    keywords: [
      'system-view', 'interface', 'ip', 'ospf', 'quit', 'sysname', 'acl',
      'display', 'save', 'reset', 'return'
    ],
    commands: [
      { label: 'system-view', detail: '进入系统视图', insertText: 'system-view' },
      { label: 'interface', detail: '配置接口', insertText: 'interface ${1:interface-type} ${2:interface-number}' },
      { label: 'ip address', detail: '配置IP地址', insertText: 'ip address ${1:ip-address} ${2:subnet-mask}' }
    ]
  },
  // ... 其他设备类型的语法定义
};

interface ConfigEditorProps {
  value: string;
  onChange: (value: string | undefined) => void;
  deviceType: string;
  templateType: string;
  readOnly?: boolean;
  height?: string | number;
  onValidate?: (markers: any[]) => void;
}

const ConfigEditor: React.FC<ConfigEditorProps> = ({
  value,
  onChange,
  deviceType,
  templateType,
  readOnly = false,
  height = '500px',
  onValidate
}) => {
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);

  // 注册设备特定的语言
  const registerDeviceLanguage = (monaco: any, deviceType: string) => {
    const syntax = deviceSyntax[deviceType as keyof typeof deviceSyntax];
    if (!syntax) return;

    monaco.languages.register({ id: deviceType });
    monaco.languages.setMonarchTokensProvider(deviceType, {
      keywords: syntax.keywords,
      tokenizer: {
        root: [
          [/^#.*$/, 'comment'],
          [/^!.*$/, 'comment'],
          [new RegExp(syntax.keywords.join('|')), 'keyword'],
          [/\d+\.\d+\.\d+\.\d+/, 'number'],
          [/\d+/, 'number'],
        ]
      }
    });

    // 注册命令补全提供程序
    monaco.languages.registerCompletionItemProvider(deviceType, {
      provideCompletionItems: () => {
        return {
          suggestions: syntax.commands.map(cmd => ({
            label: cmd.label,
            kind: monaco.languages.CompletionItemKind.Function,
            detail: cmd.detail,
            insertText: cmd.insertText,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
          }))
        };
      }
    });
  };

  // 处理编辑器挂载
  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    // 注册设备语言
    registerDeviceLanguage(monaco, deviceType);

    // 配置编辑器
    editor.updateOptions({
      minimap: { enabled: false },
      lineNumbers: 'on',
      rulers: [80],
      wordWrap: 'on',
      wrappingIndent: 'indent',
      automaticLayout: true,
      formatOnPaste: true,
      formatOnType: true,
      suggestOnTriggerCharacters: true,
      snippetSuggestions: 'inline'
    });

    // 添加注释快捷键
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Slash, () => {
      editor.trigger('keyboard', 'editor.action.commentLine', null);
    });
  };

  // 获取编辑器语言
  const getEditorLanguage = () => {
    if (templateType === 'jinja2') return 'handlebars';
    if (deviceType in deviceSyntax) return deviceType;
    return 'plaintext';
  };

  // 格式化代码
  const formatCode = () => {
    if (!editorRef.current) return;
    editorRef.current.getAction('editor.action.formatDocument').run();
  };

  // 注释/取消注释当前行
  const toggleComment = () => {
    if (!editorRef.current) return;
    editorRef.current.trigger('keyboard', 'editor.action.commentLine', null);
  };

  return (
    <div className="config-editor">
      <MonacoEditor
        height={height}
        language={getEditorLanguage()}
        value={value}
        onChange={onChange}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          minimap: { enabled: false },
          wordWrap: 'on',
          theme: 'vs-dark'
        }}
      />
    </div>
  );
};

export default ConfigEditor; 