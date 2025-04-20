import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.device_connection_models import DeviceConnection
from database.category_models import Credential
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoAuthenticationException, NetMikoTimeoutException
import logging
from enum import Enum
import pickle
import os
from .redis_manager import redis_manager

logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    """连接状态枚举"""
    ACTIVE = "active"
    IDLE = "idle"
    FAILED = "failed"
    DISCONNECTED = "disconnected"

class DeviceConnectionManager:
    """设备连接管理器"""
    
    def __init__(self):
        """初始化连接管理器"""
        self._pool = {}  # 统一的连接池
        self._pool_lock = asyncio.Lock()  # 统一的连接池锁
        self._connection_stats = {  # 统一的连接统计信息
            "current": 0,
            "total": 0,
            "failed": 0
        }
        self._connection_times = {}  # 连接时间记录
        self._connection_status = {}  # 连接状态记录
        self._cleanup_task = None  # 清理任务
        self._health_check_task = None  # 健康检查任务
        
        try:
            # 尝试获取 Redis 客户端
            self.redis_client = redis_manager.client
            logger.info("成功获取 Redis 客户端")
        except Exception as e:
            logger.error(f"Redis 连接失败: {str(e)}")
            self.redis_client = None
    
    def _use_redis(self) -> bool:
        """检查是否可以使用 Redis"""
        if self.redis_client is None:
            try:
                self.redis_client = redis_manager.client
                return True
            except Exception as e:
                logger.error(f"Redis 连接失败: {str(e)}")
                return False
        return True
    
    async def start(self):
        """启动连接管理器"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop(self):
        """停止连接管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
    
    def _get_pool_key(self, connection_id: int, host: str) -> str:
        """获取连接池的 Redis 键"""
        return f"device_connection:{connection_id}:{host}"
    
    def _get_status_key(self, connection_id: int, host: str) -> str:
        """获取连接状态的 Redis 键"""
        return f"device_connection_status:{connection_id}:{host}"
    
    async def _cleanup_loop(self):
        """定期清理空闲连接"""
        while True:
            try:
                await self._cleanup_idle_connections()
                await asyncio.sleep(300)  # 每5分钟执行一次清理
            except Exception as e:
                logger.error(f"清理空闲连接时发生错误: {str(e)}")
                await asyncio.sleep(60)  # 发生错误时等待1分钟后重试
    
    async def _cleanup_idle_connections(self):
        """清理空闲连接"""
        if self.redis_client is None:
            current_time = datetime.now()
            for pool_key, last_used in self._connection_times.items():
                if current_time - last_used > timedelta(minutes=30):  # 30分钟未使用的连接将被清理
                    try:
                        await self.cleanup_host_connections(pool_key)
                    except Exception as e:
                        logger.error(f"清理主机 {pool_key} 的连接时发生错误: {str(e)}")
        else:
            try:
                current_time = datetime.now()
                # 获取所有连接池键
                pool_keys = self.redis_client.keys("device_connection:*")
                for pool_key in pool_keys:
                    pool_key = pool_key.decode('utf-8')
                    last_used = self.redis_client.get(f"device_connection_last_used:{pool_key}")
                    if last_used:
                        last_used = datetime.fromtimestamp(float(last_used))
                        if current_time - last_used > timedelta(minutes=30):  # 30分钟未使用的连接将被清理
                            try:
                                await self.cleanup_host_connections(pool_key)
                            except Exception as e:
                                logger.error(f"清理主机 {pool_key} 的连接时发生错误: {str(e)}")
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                self._pool = {}
                self._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                self._connection_times = {}
                self._connection_status = {}
    
    async def cleanup_host_connections(self, pool_key: str):
        """清理特定主机的所有连接"""
        if self.redis_client is None:
            if pool_key not in self._pool:
                return
                
            async with self._pool_lock:
                connection = self._pool[pool_key]
                connection.disconnect()
                del self._pool[pool_key]
        else:
            try:
                # 删除连接池中的所有连接
                self.redis_client.delete(pool_key)
                # 删除相关的状态和统计信息
                self.redis_client.delete(self._get_status_key(pool_key))
                self.redis_client.delete(f"device_connection_last_used:{pool_key}")
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                self._pool = {}
                self._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                self._connection_times = {}
                self._connection_status = {}
    
    async def _retry_connection(self, device_params: dict, max_retries: int = 3, initial_delay: float = 1.0) -> ConnectHandler:
        """重试建立连接"""
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return ConnectHandler(**device_params)
            except (NetMikoAuthenticationException, NetMikoTimeoutException) as e:
                last_exception = e
                logger.warning(f"连接尝试 {attempt + 1}/{max_retries} 失败: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # 指数退避
                    
        raise last_exception
    
    async def _health_check_loop(self):
        """定期检查连接健康状态"""
        while True:
            try:
                await self._check_connections_health()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"健康检查时发生错误: {str(e)}")
                await asyncio.sleep(30)  # 发生错误时等待30秒后重试
    
    async def _check_connections_health(self):
        """检查所有连接的健康状态"""
        if self.redis_client is None:
            for pool_key, status in self._connection_status.items():
                if status == ConnectionStatus.ACTIVE:
                    try:
                        # 获取连接但不从连接池中移除
                        connection = await self._check_connection_health(pool_key)
                        if connection:
                            # 将连接放回连接池
                            await self._add_connection_to_pool(pool_key, connection)
                    except Exception as e:
                        logger.error(f"检查主机 {pool_key} 连接健康状态时发生错误: {str(e)}")
                        self._connection_status[pool_key] = ConnectionStatus.FAILED
        else:
            try:
                # 获取所有连接池键
                pool_keys = self.redis_client.keys("device_connection:*")
                for pool_key in pool_keys:
                    pool_key = pool_key.decode('utf-8')
                    status = self.redis_client.get(self._get_status_key(pool_key))
                    if status and status.decode('utf-8') == ConnectionStatus.ACTIVE.value:
                        try:
                            # 获取连接但不从连接池中移除
                            connection = await self._check_connection_health(pool_key)
                            if connection:
                                # 将连接放回连接池
                                await self._add_connection_to_pool(pool_key, connection)
                        except Exception as e:
                            logger.error(f"检查主机 {pool_key} 连接健康状态时发生错误: {str(e)}")
                            self.redis_client.set(self._get_status_key(pool_key), ConnectionStatus.FAILED.value)
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                self._pool = {}
                self._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                self._connection_times = {}
                self._connection_status = {}
    
    async def _check_connection_health(self, pool_key: str) -> Optional[ConnectHandler]:
        """检查特定连接的健康状态"""
        if self.redis_client is None:
            if pool_key not in self._pool:
                return None
                
            try:
                connection = self._pool[pool_key]
                if connection.is_alive():
                    # 尝试执行简单命令来验证连接
                    try:
                        connection.send_command("show version", strip_command=False, strip_prompt=False)
                        self._connection_status[pool_key] = ConnectionStatus.ACTIVE
                        return connection
                    except:
                        connection.disconnect()
                        self._connection_status[pool_key] = ConnectionStatus.FAILED
                        return None
                else:
                    self._connection_status[pool_key] = ConnectionStatus.DISCONNECTED
                    return None
            except:
                self._connection_status[pool_key] = ConnectionStatus.FAILED
                return None
        else:
            try:
                connection_data = self.redis_client.rpop(pool_key)
                if not connection_data:
                    return None
                    
                try:
                    connection = pickle.loads(connection_data)
                    if connection.is_alive():
                        # 尝试执行简单命令来验证连接
                        try:
                            connection.send_command("show version", strip_command=False, strip_prompt=False)
                            self.redis_client.set(self._get_status_key(pool_key), ConnectionStatus.ACTIVE.value)
                            return connection
                        except:
                            connection.disconnect()
                            self.redis_client.set(self._get_status_key(pool_key), ConnectionStatus.FAILED.value)
                            return None
                    else:
                        self.redis_client.set(self._get_status_key(pool_key), ConnectionStatus.DISCONNECTED.value)
                        return None
                except:
                    self.redis_client.set(self._get_status_key(pool_key), ConnectionStatus.FAILED.value)
                    return None
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                self._pool = {}
                self._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                self._connection_times = {}
                self._connection_status = {}
                return None
    
    def get_connection_status(self, pool_key: str) -> ConnectionStatus:
        """获取连接状态"""
        if self.redis_client is None:
            if pool_key in self._connection_status:
                return self._connection_status[pool_key]
            return ConnectionStatus.DISCONNECTED
        else:
            try:
                status = self.redis_client.get(self._get_status_key(pool_key))
                if status:
                    return ConnectionStatus(status.decode('utf-8'))
                return ConnectionStatus.DISCONNECTED
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                self._pool = {}
                self._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                self._connection_times = {}
                self._connection_status = {}
                return ConnectionStatus.DISCONNECTED
    
    async def _add_connection_to_pool(self, pool_key: str, connection: ConnectHandler):
        """添加连接到连接池"""
        if self.redis_client is None:
            async with self._pool_lock:
                # 检查是否达到最大连接数
                if self._connection_stats["current"] >= 100:  # 统一的最大连接数限制为100
                    raise ValueError("连接池已达到最大连接数")
                
                # 尝试从连接池获取连接
                if pool_key in self._pool:
                    conn = self._pool[pool_key]
                    if conn.is_alive():
                        self._connection_status[pool_key] = ConnectionStatus.ACTIVE
                        return
                    else:
                        conn.disconnect()
                        del self._pool[pool_key]
                
                # 创建新连接
                try:
                    self._connection_stats["current"] += 1
                    self._connection_stats["total"] += 1
                    self._connection_times[pool_key] = datetime.now()
                    self._connection_status[pool_key] = ConnectionStatus.ACTIVE
                    
                    # 将新连接添加到连接池
                    self._pool[pool_key] = connection
                except Exception as e:
                    # 更新失败统计
                    self._connection_stats["failed"] += 1
                    raise e
        else:
            try:
                self.redis_client.rpush(pool_key, pickle.dumps(connection))
                self.redis_client.set(f"device_connection_last_used:{pool_key}", datetime.now().timestamp())
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                self._pool = {}
                self._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                self._connection_times = {}
                self._connection_status = {}
                # 重试添加到内存存储
                await this._add_connection_to_pool(pool_key, connection)
    
    async def get_connection(self, db: Session, connection_id: int, host: str) -> Optional[ConnectHandler]:
        """从连接池获取设备连接"""
        connection = db.query(DeviceConnection).filter(DeviceConnection.id == connection_id).first()
        if not connection:
            raise ValueError(f"设备连接配置 {connection_id} 不存在")
            
        credential = db.query(Credential).filter(Credential.id == connection.credential_id).first()
        if not credential:
            raise ValueError(f"凭证 {connection.credential_id} 不存在")
            
        if this.redis_client is None:
            # 使用内存存储
            async with this._pool_lock:
                # 检查是否达到最大连接数
                if this._connection_stats["current"] >= 100:  # 统一的最大连接数限制为100
                    raise ValueError("连接池已达到最大连接数")
                
                # 尝试从连接池获取连接
                pool_key = f"{connection_id}:{host}"
                if pool_key in this._pool:
                    conn = this._pool[pool_key]
                    if conn.is_alive():
                        this._connection_status[pool_key] = ConnectionStatus.ACTIVE
                        return conn
                    else:
                        conn.disconnect()
                        del this._pool[pool_key]
                
                # 创建新连接
                try:
                    device_params = {
                        "device_type": connection.device_type,
                        "host": host,
                        "username": credential.username,
                        "password": credential.password,
                        "port": connection.port,
                        "global_delay_factor": connection.global_delay_factor,
                        "auth_timeout": connection.auth_timeout,
                        "banner_timeout": connection.banner_timeout,
                        "fast_cli": connection.fast_cli,
                        "session_timeout": connection.session_timeout,
                        "conn_timeout": connection.conn_timeout,
                        "keepalive": connection.keepalive,
                        "verbose": connection.verbose
                    }
                    
                    if connection.enable_secret:
                        device_params["secret"] = connection.enable_secret
                        
                    # 使用重试机制创建新连接
                    netmiko_conn = await this._retry_connection(device_params)
                    
                    # 更新统计信息
                    this._connection_stats["current"] += 1
                    this._connection_stats["total"] += 1
                    this._connection_times[pool_key] = datetime.now()
                    this._connection_status[pool_key] = ConnectionStatus.ACTIVE
                    
                    # 将新连接添加到连接池
                    this._pool[pool_key] = netmiko_conn
                    
                    return netmiko_conn
                except Exception as e:
                    # 更新失败统计
                    this._connection_stats["failed"] += 1
                    raise e
        else:
            try:
                pool_key = f"device_connection:{connection_id}:{host}"
                stats_key = "device_connection_stats"
                
                # 尝试从连接池获取连接
                connection_data = this.redis_client.rpop(pool_key)
                if connection_data:
                    try:
                        connection = pickle.loads(connection_data)
                        # 检查连接是否仍然有效
                        if not connection.is_alive():
                            connection.disconnect()
                            connection_data = None
                        else:
                            # 在成功获取连接后更新状态
                            this.redis_client.set(f"device_connection_status:{connection_id}:{host}", ConnectionStatus.ACTIVE.value)
                            this.redis_client.set(f"device_connection_last_used:{connection_id}:{host}", datetime.now().timestamp())
                            return connection
                    except:
                        connection_data = None
                
                # 如果连接池为空或连接无效，创建新连接
                stats = this.redis_client.hgetall(stats_key)
                current_connections = int(stats.get(b'current_connections', 0))
                max_connections = 100  # 统一的最大连接数限制为100
                
                if current_connections >= max_connections:
                    raise ValueError("连接池已达到最大连接数")
                    
                try:
                    # 创建设备连接参数
                    device_params = {
                        "device_type": connection.device_type,
                        "host": host,
                        "username": credential.username,
                        "password": credential.password,
                        "port": connection.port,
                        "global_delay_factor": connection.global_delay_factor,
                        "auth_timeout": connection.auth_timeout,
                        "banner_timeout": connection.banner_timeout,
                        "fast_cli": connection.fast_cli,
                        "session_timeout": connection.session_timeout,
                        "conn_timeout": connection.conn_timeout,
                        "keepalive": connection.keepalive,
                        "verbose": connection.verbose
                    }
                    
                    if connection.enable_secret:
                        device_params["secret"] = connection.enable_secret
                        
                    # 使用重试机制创建新连接
                    netmiko_conn = await this._retry_connection(device_params)
                    
                    # 更新统计信息
                    this.redis_client.hincrby(stats_key, 'current_connections', 1)
                    this.redis_client.hincrby(stats_key, 'total_connections', 1)
                    this.redis_client.hset(stats_key, 'last_used', datetime.now().timestamp())
                    
                    # 将新连接添加到连接池
                    await this._add_connection_to_pool(pool_key, netmiko_conn)
                    
                    return netmiko_conn
                except Exception as e:
                    # 更新失败统计
                    this.redis_client.hincrby(stats_key, 'failed_connections', 1)
                    raise e
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                this._pool = {}
                this._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                this._connection_times = {}
                this._connection_status = {}
                # 重试使用内存存储
                return await this.get_connection(db, connection_id, host)
    
    async def release_connection(self, db: Session, connection_id: int, host: str, connection: ConnectHandler):
        """释放设备连接回连接池"""
        if this.redis_client is None:
            async with this._pool_lock:
                pool_key = f"{connection_id}:{host}"
                if pool_key in this._pool:
                    try:
                        # 检查连接是否仍然有效
                        if connection and connection.is_alive():
                            this._pool[pool_key] = connection
                            this._connection_status[pool_key] = ConnectionStatus.IDLE
                        else:
                            # 如果连接已断开，关闭并更新统计信息
                            if connection:
                                connection.disconnect()
                            this._connection_stats["current"] -= 1
                            if pool_key in this._pool:
                                del this._pool[pool_key]
                    except Exception as e:
                        # 如果发生错误，确保连接被关闭
                        if connection:
                            try:
                                connection.disconnect()
                            except:
                                pass
                        this._connection_stats["current"] -= 1
                        if pool_key in this._pool:
                            del this._pool[pool_key]
                        logger.error(f"释放连接失败: {str(e)}")
                        raise ValueError(f"释放连接失败: {str(e)}")
        else:
            try:
                # 检查连接是否仍然有效
                if connection and connection.is_alive():
                    await this._add_connection_to_pool(f"{connection_id}:{host}", connection)
                    this.redis_client.set(f"device_connection_status:{connection_id}:{host}", ConnectionStatus.IDLE.value)
                else:
                    # 如果连接已断开，关闭并更新统计信息
                    if connection:
                        connection.disconnect()
                    stats_key = "device_connection_stats"
                    this.redis_client.hincrby(stats_key, 'current_connections', -1)
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                this._pool = {}
                this._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                this._connection_times = {}
                this._connection_status = {}
                # 重试使用内存存储
                await this.release_connection(db, connection_id, host, connection)
            except Exception as e:
                # 如果发生错误，确保连接被关闭
                if connection:
                    try:
                        connection.disconnect()
                    except:
                        pass
                stats_key = "device_connection_stats"
                this.redis_client.hincrby(stats_key, 'current_connections', -1)
                logger.error(f"释放连接失败: {str(e)}")
                raise ValueError(f"释放连接失败: {str(e)}")
    
    async def cleanup_pool(self, db: Session):
        """清理连接池中的所有连接"""
        if this.redis_client is None:
            async with this._pool_lock:
                for pool_key, connection in list(this._pool.items()):
                    try:
                        connection.disconnect()
                    except:
                        pass
                
                # 重置统计信息
                this._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                
                # 清理连接池
                this._pool.clear()
                this._connection_times.clear()
                this._connection_status.clear()
        else:
            try:
                # 获取所有连接池键
                pool_keys = this.redis_client.keys("device_connection:*")
                for pool_key in pool_keys:
                    pool_key = pool_key.decode('utf-8')
                    try:
                        connection_data = this.redis_client.rpop(pool_key)
                        if connection_data:
                            connection = pickle.loads(connection_data)
                            connection.disconnect()
                    except Exception as e:
                        logger.error(f"清理连接时发生错误: {str(e)}")
                        
                # 重置统计信息
                stats_key = "device_connection_stats"
                this.redis_client.delete(stats_key)
                this.redis_client.hset(stats_key, 'current_connections', 0)
                this.redis_client.hset(stats_key, 'total_connections', 0)
                this.redis_client.hset(stats_key, 'failed_connections', 0)
            except redis.ConnectionError as e:
                logger.error(f"Redis 连接错误: {str(e)}")
                # 如果 Redis 连接失败，切换到内存存储
                this._pool = {}
                this._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                this._connection_times = {}
                this._connection_status = {}
                # 重试使用内存存储
                await this.cleanup_pool(db)
    
    async def initialize_pool(self):
        """初始化连接池"""
        try:
            if this._use_redis():
                # 初始化 Redis 中的连接池统计信息
                stats_key = "device_connection_stats"
                this.redis_client.hmset(stats_key, {
                    'current_connections': 0,
                    'total_connections': 0,
                    'failed_connections': 0,
                    'last_used': datetime.now().timestamp()
                })
                logger.info("成功初始化 Redis 连接池")
            else:
                # 使用内存存储
                this._pool = {}
                this._connection_stats = {
                    "current": 0,
                    "total": 0,
                    "failed": 0
                }
                this._connection_times = {}
                this._connection_status = {}
                logger.info("成功初始化内存连接池")
        except Exception as e:
            logger.error(f"初始化连接池失败: {str(e)}")
            raise

# 创建全局实例
device_connection_manager = DeviceConnectionManager() 