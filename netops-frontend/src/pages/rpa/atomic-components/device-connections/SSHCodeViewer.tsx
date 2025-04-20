import React, { useEffect, useState } from 'react';
import { Modal, Typography, message, Spin } from 'antd';
import { SSHConfig } from '../../../../services/sshConfig';
import { FullCredential, getFullCredential } from '../../../../services/credential';

const { Text } = Typography;

interface SSHCodeViewerProps {
  visible: boolean;
  onClose: () => void;
  config: SSHConfig;
}

/**
 * SSH代码查看器组件
 * 用于显示Netmiko连接代码
 */
const SSHCodeViewer: React.FC<SSHCodeViewerProps> = ({ visible, onClose, config }) => {
  const [credential, setCredential] = useState<FullCredential | null>(null);
  const [loading, setLoading] = useState(false);

  /**
   * 获取凭证信息
   */
  useEffect(() => {
    const fetchCredential = async () => {
      if (!config || !config.credential_id) {
        message.error('未选择凭证');
        return;
      }
      
      try {
        setLoading(true);
        const data = await getFullCredential(config.credential_id);
        setCredential(data);
      } catch (error) {
        // 处理错误信息时确保只显示字符串
        let errorMessage = '获取凭证信息失败';
        if (error instanceof Error) {
          errorMessage = error.message;
        } else if (typeof error === 'string') {
          errorMessage = error;
        } else if (error && typeof error === 'object') {
          errorMessage = JSON.stringify(error);
        }
        
        message.error(errorMessage);
        console.error('获取凭证信息失败:', error);
      } finally {
        setLoading(false);
      }
    };

    if (visible && config) {
      fetchCredential();
    }
  }, [visible, config]);

  /**
   * 生成Netmiko连接代码
   */
  const generateCode = () => {
    if (!credential) {
      return '// 无法获取凭证信息，请检查凭证配置';
    }

    if (!credential.username || !credential.password) {
      return '// 凭证信息不完整，请检查凭证配置';
    }

    const code = `from netmiko import ConnectHandler
from typing import Dict, Any

def create_connection(host: str) -> Dict[str, Any]:
    """
    创建Netmiko连接
    :param host: 设备IP地址
    :return: 连接对象
    """
    device = {
        'device_type': '${config.device_type}',
        'host': host,
        'port': ${config.port},
        'username': '${credential.username}',  # 从凭证管理获取
        'password': '${credential.password}',  # 从凭证管理获取
        'global_delay_factor': ${config.global_delay_factor},
        'auth_timeout': ${config.auth_timeout},
        'banner_timeout': ${config.banner_timeout},
        'fast_cli': ${config.fast_cli},
        'session_timeout': ${config.session_timeout},
        'conn_timeout': ${config.conn_timeout},
        'keepalive': ${config.keepalive},
        'verbose': ${config.verbose}
    }
    
    # 如果是思科设备，添加enable密码
    ${config.device_type.startsWith('cisco_') ? `if '${config.device_type}'.startswith('cisco_'):
        device['secret'] = '${credential.enable_password || config.enable_secret}'` : ''}
    
    try:
        connection = ConnectHandler(**device)
        return connection
    except Exception as e:
        print(f"连接失败: {str(e)}")
        raise

# 使用示例
if __name__ == "__main__":
    # 连接设备
    host = "192.168.1.1"  # 设备IP地址
    connection = create_connection(host)
    
    # 执行命令
    output = connection.send_command("show version")
    print(output)
    
    # 关闭连接
    connection.disconnect()`;

    return code;
  };

  return (
    <Modal
      title="Netmiko连接代码"
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
      confirmLoading={loading}
    >
      <Spin spinning={loading}>
        <div style={{ 
          backgroundColor: '#f5f5f5', 
          padding: '16px', 
          borderRadius: '4px',
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
          maxHeight: '600px',
          overflow: 'auto'
        }}>
          <Text code>{generateCode()}</Text>
        </div>
      </Spin>
    </Modal>
  );
};

export default SSHCodeViewer; 