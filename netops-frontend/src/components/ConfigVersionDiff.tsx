import React from 'react';
import { DiffEditor } from '@monaco-editor/react';
import { Card } from 'antd';

interface ConfigVersionDiffProps {
  originalContent: string;
  modifiedContent: string;
  height?: string;
}

const ConfigVersionDiff: React.FC<ConfigVersionDiffProps> = ({
  originalContent,
  modifiedContent,
  height = '400px'
}) => {
  return (
    <Card className="version-diff-card">
      <DiffEditor
        height={height}
        original={originalContent}
        modified={modifiedContent}
        language="plaintext"
        theme="vs-dark"
        options={{
          readOnly: true,
          renderSideBySide: true,
          minimap: { enabled: false },
          wordWrap: 'on',
          scrollBeyondLastLine: false
        }}
      />
    </Card>
  );
};

export default ConfigVersionDiff; 