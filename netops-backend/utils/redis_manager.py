import redis
import os
import logging
from typing import Optional
from redis.connection import ConnectionPool

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis 连接管理器"""
    _instance = None
    _redis_client = None
    _redis_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._redis_client:
            self._init_redis()
    
    def _init_redis(self):
        """初始化 Redis 连接"""
        try:
            # 从环境变量获取 Redis 配置
            redis_host = os.getenv('REDIS_HOST', '172.18.40.80')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            # 创建连接池
            self._redis_pool = ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                max_connections=10  # 修改为更合理的最大连接数
            )
            
            # 创建 Redis 客户端
            self._redis_client = redis.Redis(connection_pool=self._redis_pool)
            
            # 测试连接
            self._redis_client.ping()
            logger.info(f"成功连接到 Redis 服务器: {redis_host}:{redis_port}")
            
        except redis.ConnectionError as e:
            logger.error(f"Redis 连接失败: {str(e)}")
            self._redis_client = None
            self._redis_pool = None
            raise
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端实例"""
        if not self._redis_client:
            self._init_redis()
        return self._redis_client
    
    def get_connection_pool(self) -> Optional[ConnectionPool]:
        """获取 Redis 连接池"""
        if not self._redis_pool:
            self._init_redis()
        return self._redis_pool
    
    def close(self):
        """关闭 Redis 连接"""
        if self._redis_client:
            self._redis_client.close()
        if self._redis_pool:
            self._redis_pool.disconnect()
        self._redis_client = None
        self._redis_pool = None
        logger.info("Redis 连接已关闭")

# 创建全局实例
redis_manager = RedisManager() 