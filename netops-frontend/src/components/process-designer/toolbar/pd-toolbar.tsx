import React from 'react';
import { Button, Space, Divider } from 'antd';
import {
  UndoOutlined,
  RedoOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
} from '@ant-design/icons';
import type { PDToolbarConfig } from '../../../types/process-designer/pd-types';

export const PDToolbar: React.FC<PDToolbarConfig> = ({
  onSave,
  onUndo,
  onRedo,
  onValidate,
  onExecute,
  canUndo,
  canRedo,
}) => {
  const [isFullscreen, setIsFullscreen] = React.useState(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <div className="pd-toolbar">
      <Space split={<Divider type="vertical" />}>
        <Button
          icon={<UndoOutlined />}
          onClick={onUndo}
          disabled={!canUndo}
          title="撤销"
        />
        <Button
          icon={<RedoOutlined />}
          onClick={onRedo}
          disabled={!canRedo}
          title="重做"
        />
        <Button
          icon={<SaveOutlined />}
          onClick={onSave}
          title="保存"
        />
        <Button
          icon={<CheckCircleOutlined />}
          onClick={onValidate}
          title="验证"
        />
        <Button
          icon={<PlayCircleOutlined />}
          onClick={onExecute}
          title="执行"
        />
        <Button
          icon={<ZoomInOutlined />}
          onClick={() => {
            // TODO: 实现放大功能
          }}
          title="放大"
        />
        <Button
          icon={<ZoomOutOutlined />}
          onClick={() => {
            // TODO: 实现缩小功能
          }}
          title="缩小"
        />
        <Button
          icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          onClick={toggleFullscreen}
          title={isFullscreen ? '退出全屏' : '全屏'}
        />
      </Space>
    </div>
  );
}; 