import asyncio
from typing import Dict, Optional
import asyncssh
from datetime import datetime
from sqlalchemy.orm import Session
from database.device_connection_models import SSHConnection, ConnectionPool, ConnectionStats
import httpx
from fastapi import HTTPException

class SSHConnectionManager:
    """SSH连接管理器"""
    def __init__(self):
        self._pools: Dict[int, Dict[str, asyncssh.SSHClientConnection]] = {}
        self._pool_locks: Dict[int, asyncio.Lock] = {}
        self._stats: Dict[int, Dict] = {}

    async def get_credential(self, credential_id: str) -> Optional[Dict]:
        """获取凭证信息"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000/api/device/credential/{credential_id}/full")
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取凭证信息失败: {str(e)}")

    async def get_connection(self, db: Session, pool_id: int, host: str) -> Optional[asyncssh.SSHClientConnection]:
        """获取SSH连接"""
        # 获取连接池配置
        pool = db.query(ConnectionPool).filter(ConnectionPool.id == pool_id).first()
        if not pool:
            return None

        # 获取SSH配置
        ssh_config = db.query(SSHConnection).filter(SSHConnection.id == pool.ssh_config_id).first()
        if not ssh_config:
            return None

        # 获取凭证信息
        credential = await self.get_credential(ssh_config.credential_id)
        if not credential:
            return None

        # 确保连接池存在
        if pool_id not in self._pools:
            self._pools[pool_id] = {}
            self._pool_locks[pool_id] = asyncio.Lock()
            self._stats[pool_id] = {
                "current_connections": 0,
                "total_connections": 0,
                "failed_connections": 0,
                "last_used": None
            }

        # 获取或创建连接
        async with self._pool_locks[pool_id]:
            if host in self._pools[pool_id]:
                # 更新统计信息
                self._stats[pool_id]["last_used"] = datetime.now()
                return self._pools[pool_id][host]

            # 检查是否达到最大连接数
            if self._stats[pool_id]["current_connections"] >= pool.max_connections:
                return None

            try:
                # 创建新连接
                conn = await asyncssh.connect(
                    host=host,
                    port=ssh_config.port,
                    username=credential["username"],
                    password=credential["password"],
                    known_hosts=None  # 在生产环境中应该配置known_hosts
                )

                # 更新连接池和统计信息
                self._pools[pool_id][host] = conn
                self._stats[pool_id]["current_connections"] += 1
                self._stats[pool_id]["total_connections"] += 1
                self._stats[pool_id]["last_used"] = datetime.now()

                # 更新数据库中的统计信息
                stats = db.query(ConnectionStats).filter(ConnectionStats.pool_id == pool_id).first()
                if not stats:
                    stats = ConnectionStats(pool_id=pool_id)
                    db.add(stats)
                
                stats.current_connections = self._stats[pool_id]["current_connections"]
                stats.total_connections = self._stats[pool_id]["total_connections"]
                stats.last_used = self._stats[pool_id]["last_used"]
                db.commit()

                return conn

            except Exception as e:
                # 更新失败统计
                self._stats[pool_id]["failed_connections"] += 1
                stats = db.query(ConnectionStats).filter(ConnectionStats.pool_id == pool_id).first()
                if stats:
                    stats.failed_connections = self._stats[pool_id]["failed_connections"]
                    db.commit()
                return None

    async def release_connection(self, db: Session, pool_id: int, host: str):
        """释放SSH连接"""
        if pool_id in self._pools and host in self._pools[pool_id]:
            async with self._pool_locks[pool_id]:
                try:
                    await self._pools[pool_id][host].close()
                except:
                    pass
                del self._pools[pool_id][host]
                self._stats[pool_id]["current_connections"] -= 1

                # 更新数据库中的统计信息
                stats = db.query(ConnectionStats).filter(ConnectionStats.pool_id == pool_id).first()
                if stats:
                    stats.current_connections = self._stats[pool_id]["current_connections"]
                    db.commit()

    async def cleanup_pool(self, db: Session, pool_id: int):
        """清理连接池"""
        if pool_id in self._pools:
            async with self._pool_locks[pool_id]:
                for host in list(self._pools[pool_id].keys()):
                    await self.release_connection(db, pool_id, host)
                self._pools[pool_id].clear()
                self._stats[pool_id]["current_connections"] = 0

                # 更新数据库中的统计信息
                stats = db.query(ConnectionStats).filter(ConnectionStats.pool_id == pool_id).first()
                if stats:
                    stats.current_connections = 0
                    db.commit()

# 创建全局连接管理器实例
connection_manager = SSHConnectionManager() 