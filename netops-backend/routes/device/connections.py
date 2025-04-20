from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from database.session import get_db
from database.device_connection_models import DeviceConnectionPool, DeviceConnectionStats
from schemas.device_connection import (
    ConnectionPoolCreate, ConnectionPoolUpdate, ConnectionPoolResponse,
    ConnectionStatsResponse
)
from utils.connection_pool_manager import ConnectionPoolManager
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/api/device/connections/pools",
    tags=["connection-pools"]
)

# 创建连接池管理器实例
pool_manager = ConnectionPoolManager()

@router.get("/{config_id}", response_model=ConnectionPoolResponse)
async def get_pool_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """获取连接池配置"""
    try:
        # 从 Redis 获取连接池配置
        pool_config = pool_manager.redis_client.hgetall('connection_pool_config')
        if not pool_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"连接池配置 {config_id} 不存在"
            )
        return pool_config
    except Exception as e:
        logger.error(f"获取连接池配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取连接池配置失败: {str(e)}"
        )

@router.put("/{config_id}", response_model=ConnectionPoolResponse)
async def update_pool_config(
    config_id: int,
    pool_update: ConnectionPoolUpdate,
    db: Session = Depends(get_db)
):
    """更新连接池配置"""
    try:
        # 检查配置是否存在
        if not pool_manager.redis_client.exists('connection_pool_config'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"连接池配置 {config_id} 不存在"
            )
        
        # 更新配置
        update_data = pool_update.dict(exclude_unset=True)
        pool_manager.redis_client.hmset('connection_pool_config', update_data)
        
        # 获取更新后的配置
        updated_config = pool_manager.redis_client.hgetall('connection_pool_config')
        return updated_config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新连接池配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新连接池配置失败: {str(e)}"
        )

@router.get("/{config_id}/stats", response_model=Dict[str, Any])
async def get_pool_status(
    config_id: int,
    db: Session = Depends(get_db)
):
    """获取连接池状态"""
    try:
        # 从 Redis 获取连接池状态
        stats = pool_manager.redis_client.hgetall('device_connection_stats')
        if not stats:
            # 如果没有状态数据，返回默认值
            return {
                "total_connections": 0,
                "active_connections": 0,
                "idle_connections": 0,
                "waiting_connections": 0,
                "max_wait_time": 0,
                "avg_wait_time": 0,
                "created_at": datetime.now().isoformat()
            }
        
        # 转换数据格式以匹配前端期望
        return {
            "total_connections": int(stats.get(b'total_connections', 0)),
            "active_connections": int(stats.get(b'current_connections', 0)),
            "idle_connections": int(stats.get(b'current_connections', 0)) - int(stats.get(b'failed_connections', 0)),
            "waiting_connections": 0,  # 默认值
            "max_wait_time": 0,  # 默认值
            "avg_wait_time": 0,  # 默认值
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取连接池状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取连接池状态失败: {str(e)}"
        )

@router.get("/{config_id}/metrics", response_model=dict)
async def get_pool_metrics(
    config_id: int,
    time_range: str = "1h",
    db: Session = Depends(get_db)
):
    """获取连接池指标"""
    try:
        # 从 Redis 获取连接池指标
        metrics = {
            "current_connections": 0,
            "total_connections": 0,
            "failed_connections": 0,
            "time_range": time_range
        }
        
        stats = pool_manager.redis_client.hgetall('device_connection_stats')
        if stats:
            metrics.update({
                "current_connections": int(stats.get(b'current_connections', 0)),
                "total_connections": int(stats.get(b'total_connections', 0)),
                "failed_connections": int(stats.get(b'failed_connections', 0))
            })
        
        return metrics
    except Exception as e:
        logger.error(f"获取连接池指标失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取连接池指标失败: {str(e)}"
        )

@router.post("/{config_id}/cleanup", status_code=status.HTTP_204_NO_CONTENT)
async def cleanup_pool(
    config_id: int,
    db: Session = Depends(get_db)
):
    """清理连接池"""
    try:
        # 获取所有连接池键
        pool_keys = pool_manager.redis_client.keys("device_connection:*")
        for pool_key in pool_keys:
            pool_key = pool_key.decode('utf-8')
            try:
                # 删除连接池中的所有连接
                pool_manager.redis_client.delete(pool_key)
                # 删除相关的状态和统计信息
                pool_manager.redis_client.delete(f"device_connection_status:{pool_key}")
                pool_manager.redis_client.delete(f"device_connection_last_used:{pool_key}")
            except Exception as e:
                logger.error(f"清理连接 {pool_key} 失败: {str(e)}")
        
        # 重置统计信息
        stats_key = "device_connection_stats"
        pool_manager.redis_client.delete(stats_key)
        pool_manager.redis_client.hmset(stats_key, {
            'current_connections': 0,
            'total_connections': 0,
            'failed_connections': 0
        })
        return None
    except Exception as e:
        logger.error(f"清理连接池失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理连接池失败: {str(e)}"
        ) 