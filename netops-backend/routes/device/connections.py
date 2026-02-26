from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from database.session import get_db
from database.device_connection_models import DeviceConnectionPool, DeviceConnectionStats
from schemas.device_connection import (
    ConnectionPoolCreate, ConnectionPoolUpdate, ConnectionPoolResponse,
    ConnectionStatsResponse
)
from utils.connection_pool_manager import connection_pool_manager  # 与 device_connection_manager 共用 Redis，stats 由 device_connection_manager 写入
from datetime import datetime


def _zero_device_stats() -> Dict[str, Any]:
    """返回全零的设备连接池统计（用于 Redis 不可用或无数据时）。"""
    return {
        "total_connections": 0,
        "active_connections": 0,
        "idle_connections": 0,
        "waiting_connections": 0,
        "max_wait_time": 0,
        "avg_wait_time": 0,
        "created_at": datetime.now().isoformat(),
    }


def _get_device_stats_from_redis(redis_client) -> Dict[str, Any]:
    """从 Redis 读取 device_connection_stats（device_connection_manager 写入），兼容 str/bytes key。"""
    if not redis_client:
        return _zero_device_stats()
    try:
        stats = redis_client.hgetall("device_connection_stats")
    except Exception as e:
        logger.warning(f"读取 device_connection_stats 失败: {e}，返回零统计")
        return _zero_device_stats()
    if not stats:
        return _zero_device_stats()
    def _v(key):
        v = stats.get(key) or stats.get(key.encode("utf-8") if isinstance(key, str) else key)
        if v is None:
            return 0
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0
    total = _v("total_connections")
    current = _v("current_connections")
    failed = _v("failed_connections")
    return {
        "total_connections": total,
        "active_connections": current,
        "idle_connections": max(0, current - failed),
        "waiting_connections": 0,
        "max_wait_time": 0,
        "avg_wait_time": 0,
        "created_at": datetime.now().isoformat(),
    }

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/api/device/connections/pools",
    tags=["connection-pools"]
)

# 连接池 API 使用的 Redis 客户端（与 connection_pool_manager 同源，用于读写 device_connection_stats）
pool_manager = connection_pool_manager


class ReportEventBody(BaseModel):
    event: str  # "connect" | "disconnect"


@router.post("/report", status_code=status.HTTP_204_NO_CONTENT)
async def report_connection_event(body: ReportEventBody):
    """作业执行（生成代码子进程）在建立/关闭设备连接时调用，用于更新连接池统计，使「连接池监控」能正确显示。"""
    event = (body.event or "").strip().lower()
    if event not in ("connect", "disconnect"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="event 必须为 connect 或 disconnect")
    redis_client = getattr(pool_manager, "redis_client", None)
    if not redis_client:
        return None
    try:
        stats_key = "device_connection_stats"
        if event == "connect":
            redis_client.hincrby(stats_key, "current_connections", 1)
            redis_client.hincrby(stats_key, "total_connections", 1)
        else:
            redis_client.hincrby(stats_key, "current_connections", -1)
            cur = redis_client.hget(stats_key, "current_connections")
            if cur is not None and int(cur) < 0:
                redis_client.hset(stats_key, "current_connections", 0)
    except Exception as e:
        logger.warning(f"上报连接事件失败: {e}")
    return None


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
    pool_type: str = Query("device", description="连接池类型：redis | device"),
    db: Session = Depends(get_db)
):
    """获取连接池状态。device=网络设备 SSH 连接池（由 device_connection_manager 维护），redis=Redis 通信连接池配置统计。"""
    try:
        if pool_type == "device":
            return _get_device_stats_from_redis(getattr(pool_manager, "redis_client", None))
        # redis：返回 connection_pool_stats:redis 的统计（若无可返回零值）
        stats = pool_manager.get_pool_stats("redis")
        return {
            "total_connections": int(stats.get("total_connections", 0)),
            "active_connections": int(stats.get("active_connections", 0)),
            "idle_connections": int(stats.get("idle_connections", 0)),
            "waiting_connections": int(stats.get("waiting_connections", 0)),
            "max_wait_time": int(stats.get("max_wait_time", 0)),
            "avg_wait_time": float(stats.get("avg_wait_time", 0)),
            "created_at": stats.get("created_at", datetime.now().isoformat()),
        }
    except Exception as e:
        logger.warning(f"获取连接池状态失败: {str(e)}，返回零统计")
        return _zero_device_stats()

def _zero_metrics(time_range: str) -> Dict[str, Any]:
    """返回全零的指标（用于 Redis 不可用或异常时）。"""
    return {
        "connection_history": [],
        "error_history": [],
        "resource_usage": [],
        "current_connections": 0,
        "total_connections": 0,
        "failed_connections": 0,
        "time_range": time_range,
    }


@router.get("/{config_id}/metrics", response_model=dict)
async def get_pool_metrics(
    config_id: int,
    time_range: str = Query("1h", description="时间范围"),
    pool_type: str = Query("device", description="连接池类型：redis | device"),
    db: Session = Depends(get_db)
):
    """获取连接池指标。device 时返回 device_connection_manager 写入的统计。"""
    try:
        metrics = {
            "connection_history": [],
            "error_history": [],
            "resource_usage": [],
            "current_connections": 0,
            "total_connections": 0,
            "failed_connections": 0,
            "time_range": time_range,
        }
        redis_client = getattr(pool_manager, "redis_client", None)
        if pool_type == "device":
            if redis_client:
                try:
                    stats = redis_client.hgetall("device_connection_stats")
                    if stats:
                        def _v(k):
                            v = stats.get(k) or stats.get(k.encode("utf-8") if isinstance(k, str) else k)
                            return int(float(v)) if v is not None else 0
                        metrics["current_connections"] = _v("current_connections")
                        metrics["total_connections"] = _v("total_connections")
                        metrics["failed_connections"] = _v("failed_connections")
                except Exception as e:
                    logger.warning(f"读取 device_connection_stats 失败: {e}")
        else:
            s = pool_manager.get_pool_stats("redis")
            metrics["current_connections"] = int(s.get("active_connections", 0))
            metrics["total_connections"] = int(s.get("total_connections", 0))
        return metrics
    except Exception as e:
        logger.warning(f"获取连接池指标失败: {str(e)}，返回零指标")
        return _zero_metrics(time_range)

@router.post("/{config_id}/cleanup", status_code=status.HTTP_204_NO_CONTENT)
async def cleanup_pool(
    config_id: int,
    pool_type: str = Query("device", description="连接池类型：redis | device"),
    db: Session = Depends(get_db)
):
    """清理连接池。device=清空网络设备 SSH 连接池及统计；redis=仅重置 Redis 连接池统计。"""
    try:
        if pool_type != "device":
            pool_manager.update_pool_stats({
                "total_connections": 0,
                "active_connections": 0,
                "idle_connections": 0,
                "waiting_connections": 0,
                "max_wait_time": 0,
                "avg_wait_time": 0,
                "created_at": datetime.now().isoformat(),
            }, "redis")
            return None
        # 清理网络设备连接池（与 device_connection_manager 使用的键一致）
        pool_keys = pool_manager.redis_client.keys("device_connection:*")
        for pk in pool_keys:
            key = pk.decode("utf-8") if isinstance(pk, bytes) else pk
            suffix = key.replace("device_connection:", "", 1)
            try:
                pool_manager.redis_client.delete(key)
                pool_manager.redis_client.delete(f"device_connection_status:{suffix}")
                pool_manager.redis_client.delete(f"device_connection_last_used:{suffix}")
            except Exception as e:
                logger.error(f"清理连接 {key} 失败: {str(e)}")
        # 重置统计（与 device_connection_manager 写入的键一致）
        stats_key = "device_connection_stats"
        pool_manager.redis_client.delete(stats_key)
        pool_manager.redis_client.hmset(stats_key, {
            "current_connections": 0,
            "total_connections": 0,
            "failed_connections": 0,
        })
        return None
    except Exception as e:
        logger.error(f"清理连接池失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理连接池失败: {str(e)}"
        ) 