import React, { useState, useEffect } from 'react';
import { Modal, Button, Progress } from 'antd';
import { ClockCircleOutlined } from '@ant-design/icons';

interface SessionTimeoutModalProps {
  open: boolean;
  remainingTime: number; // 剩余时间（秒）
  onContinue: () => void;
  onLogout: () => void;
}

const SessionTimeoutModal: React.FC<SessionTimeoutModalProps> = ({
  open,
  remainingTime,
  onContinue,
  onLogout
}) => {
  const [countdown, setCountdown] = useState(remainingTime);
  
  // 倒计时效果
  useEffect(() => {
    if (!open) {
      setCountdown(remainingTime);
      return;
    }
    
    setCountdown(remainingTime);
    
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(timer);
  }, [open, remainingTime]);
  
  // 计算进度条百分比
  const progressPercent = Math.floor((countdown / remainingTime) * 100);
  
  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <ClockCircleOutlined style={{ marginRight: 8, color: '#faad14' }} />
          会话即将超时
        </div>
      }
      open={open}
      closable={false}
      maskClosable={false}
      footer={[
        <Button key="logout" onClick={onLogout}>
          立即退出
        </Button>,
        <Button key="continue" type="primary" onClick={onContinue}>
          继续操作
        </Button>
      ]}
      centered
    >
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <p>由于长时间未操作，您的会话即将超时。</p>
        <p>请选择继续操作或退出系统。</p>
        
        <div style={{ margin: '20px 0' }}>
          <Progress 
            percent={progressPercent} 
            status={progressPercent <= 20 ? "exception" : "active"}
            showInfo={false}
          />
          <p style={{ marginTop: 10 }}>
            剩余时间：{Math.floor(countdown / 60)}分{countdown % 60}秒
          </p>
        </div>
      </div>
    </Modal>
  );
};

export default SessionTimeoutModal; 