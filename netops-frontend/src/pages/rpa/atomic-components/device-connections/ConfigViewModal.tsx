import React from 'react';
import { Modal, Typography, Space, Button } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import { message } from 'antd';

const { Text } = Typography;
const { Paragraph } = Typography;

interface ConfigViewModalProps {
  visible: boolean;
  onClose: () => void;
  config: any;
}

const ConfigViewModal: React.FC<ConfigViewModalProps> = ({
  visible,
  onClose,
  config
}) => {
  const generateNetmikoConfig = (config: any) => {
    const { name, deviceType, username, password, port, timeout, useProxy, reuseConnection } = config;
    
    let configCode = `from netmiko import ConnectHandler\n\n`;
    configCode += `# ${name}\n`;
    configCode += `device = {\n`;
    configCode += `    'device_type': '${deviceType}',\n`;
    configCode += `    'host': '${config.host}',\n`;
    configCode += `    'username': '${username}',\n`;
    configCode += `    'password': '${password}',\n`;
    configCode += `    'port': ${port},\n`;
    configCode += `    'timeout': ${timeout},\n`;
    
    if (deviceType.startsWith('cisco_')) {
      configCode += `    'secret': '${password}',  # Enable password for Cisco devices\n`;
      configCode += `    'global_delay_factor': 2,\n`;
    }
    
    if (useProxy) {
      configCode += `    'ssh_proxy_enable': True,\n`;
      configCode += `    'ssh_proxy_host': '${config.proxyHost}',\n`;
      configCode += `    'ssh_proxy_port': ${config.proxyPort},\n`;
    }
    
    if (reuseConnection) {
      configCode += `    'fast_cli': True,\n`;
    }
    
    configCode += `}\n\n`;
    configCode += `# 建立连接\n`;
    configCode += `net_connect = ConnectHandler(**device)\n\n`;
    configCode += `# 执行命令\n`;
    configCode += `output = net_connect.send_command('show version')\n\n`;
    configCode += `# 关闭连接\n`;
    configCode += `net_connect.disconnect()`;
    
    return configCode;
  };

  const handleCopy = () => {
    const configCode = generateNetmikoConfig(config);
    navigator.clipboard.writeText(configCode)
      .then(() => message.success('配置代码已复制到剪贴板'))
      .catch(() => message.error('复制失败'));
  };

  return (
    <Modal
      title="Netmiko配置代码"
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="copy" icon={<CopyOutlined />} onClick={handleCopy}>
          复制代码
        </Button>,
        <Button key="close" onClick={onClose}>
          关闭
        </Button>
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Text type="secondary">以下是根据当前配置生成的Netmiko连接代码：</Text>
        <Paragraph
          style={{
            backgroundColor: '#f5f5f5',
            padding: '16px',
            borderRadius: '4px',
            maxHeight: '400px',
            overflow: 'auto'
          }}
        >
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
            {generateNetmikoConfig(config)}
          </pre>
        </Paragraph>
      </Space>
    </Modal>
  );
};

export default ConfigViewModal; 