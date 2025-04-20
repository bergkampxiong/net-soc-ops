from redis import Redis
from typing import Dict, Any, Optional
from datetime import datetime
import json
import time

class ConnectionPoolManager:
    """连接池管理器"""
    def __init__(self):
        self.redis_client = Redis(
            host='172.18.40.80',
            port=6379,
            db=0,
            decode_responses=True
        )
        self._init_default_config()

    def _init_default_config(self):
        """初始化默认配置"""
        # 检查配置是否存在
        if not self.redis_client.exists('connection_pool_config'):
            default_config = {
                'id': '1',
                'connection_id': '0',
                'max_connections': '50',
                'min_idle': '1',
                'idle_timeout': '300',
                'connection_timeout': '30',
                'description': '默认连接池配置',
                'is_active': 'true',
                'created_at': datetime.now().isoformat(),
                'updated_at': str(int(time.time()))
            }
            self.redis_client.hmset('connection_pool_config', default_config)

    def get_pool_config(self, pool_type: str = 'redis') -> Dict[str, Any]:
        """获取连接池配置"""
        config_key = f'connection_pool_config:{pool_type}'
        config = self.redis_client.hgetall(config_key)
        if not config:
            self._init_default_config()
            config = self.redis_client.hgetall(config_key)
        
        # 确保所有必需的字段都存在
        default_config = {
            'id': '1',
            'connection_id': '0',
            'max_connections': '50',
            'min_idle': '1',
            'idle_timeout': '300',
            'connection_timeout': '30',
            'description': f'默认{pool_type}连接池配置',
            'is_active': 'true',
            'created_at': datetime.now().isoformat(),
            'updated_at': str(int(time.time()))
        }
        
        # 使用默认值填充缺失的字段
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        
        return config

    def update_pool_config(self, config: Dict[str, Any], pool_type: str = 'redis') -> Dict[str, Any]:
        """更新连接池配置"""
        # 确保所有值都是字符串类型
        config = {k: str(v) for k, v in config.items()}
        config['updated_at'] = str(int(time.time()))
        
        # 保持id和connection_id不变
        current_config = self.get_pool_config(pool_type)
        config['id'] = current_config['id']
        config['connection_id'] = current_config['connection_id']
        
        config_key = f'connection_pool_config:{pool_type}'
        self.redis_client.hmset(config_key, config)
        return self.get_pool_config(pool_type)

    def get_pool_stats(self, pool_type: str = 'redis') -> Dict[str, Any]:
        """获取连接池真实状态"""
        try:
            # 从Redis获取连接池状态
            stats_key = f'connection_pool_stats:{pool_type}'
            stats = self.redis_client.hgetall(stats_key)
            if not stats:
                # 如果没有状态数据，初始化为0
                stats = {
                    'total_connections': '0',
                    'active_connections': '0',
                    'idle_connections': '0',
                    'waiting_connections': '0',
                    'max_wait_time': '0',
                    'avg_wait_time': '0',
                    'created_at': datetime.now().isoformat()
                }
                self.redis_client.hmset(stats_key, stats)
            return stats
        except Exception as e:
            print(f"获取连接池状态失败: {str(e)}")
            return {
                'total_connections': '0',
                'active_connections': '0',
                'idle_connections': '0',
                'waiting_connections': '0',
                'max_wait_time': '0',
                'avg_wait_time': '0',
                'created_at': datetime.now().isoformat()
            }

    def update_pool_stats(self, stats: Dict[str, Any], pool_type: str = 'redis') -> None:
        """更新连接池状态"""
        try:
            # 确保所有值都是字符串类型
            stats = {k: str(v) for k, v in stats.items()}
            stats_key = f'connection_pool_stats:{pool_type}'
            self.redis_client.hmset(stats_key, stats)
        except Exception as e:
            print(f"更新连接池状态失败: {str(e)}")

# 创建全局实例
connection_pool_manager = ConnectionPoolManager() 