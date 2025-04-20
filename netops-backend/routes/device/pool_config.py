from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from utils.connection_pool_manager import connection_pool_manager
import time

router = APIRouter(
    tags=["pool-config"]
)

class PoolConfigResponse(BaseModel):
    id: int = 1
    connection_id: int = 0
    max_connections: int
    min_idle: int
    idle_timeout: int
    connection_timeout: int
    description: str
    created_at: str
    updated_at: str
    is_active: bool
    pool_type: str = 'redis'  # 新增：连接池类型字段

    class Config:
        from_attributes = True

class PoolConfigUpdate(BaseModel):
    max_connections: Optional[int] = None
    min_idle: Optional[int] = None
    idle_timeout: Optional[int] = None
    connection_timeout: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class PoolStatsResponse(BaseModel):
    total_connections: int
    active_connections: int
    idle_connections: int
    waiting_connections: int
    max_wait_time: int
    avg_wait_time: float
    created_at: str

class PoolMetricsResponse(BaseModel):
    timestamp: str
    value: float

@router.get("", response_model=PoolConfigResponse)
async def get_pool_config():
    """获取连接池配置"""
    try:
        config = connection_pool_manager.get_pool_config()
        return PoolConfigResponse(
            id=int(config['id']),
            connection_id=int(config['connection_id']),
            max_connections=int(config['max_connections']),
            min_idle=int(config['min_idle']),
            idle_timeout=int(config['idle_timeout']),
            connection_timeout=int(config['connection_timeout']),
            description=config['description'],
            created_at=config['created_at'],
            updated_at=config['updated_at'],
            is_active=config['is_active'].lower() == 'true'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("", response_model=PoolConfigResponse)
async def update_pool_config(config: PoolConfigUpdate):
    """更新连接池配置"""
    try:
        update_data = {k: str(v) for k, v in config.dict(exclude_unset=True).items()}
        updated_config = connection_pool_manager.update_pool_config(update_data)
        return PoolConfigResponse(
            id=int(updated_config['id']),
            connection_id=int(updated_config['connection_id']),
            max_connections=int(updated_config['max_connections']),
            min_idle=int(updated_config['min_idle']),
            idle_timeout=int(updated_config['idle_timeout']),
            connection_timeout=int(updated_config['connection_timeout']),
            description=updated_config['description'],
            created_at=updated_config['created_at'],
            updated_at=updated_config['updated_at'],
            is_active=updated_config['is_active'].lower() == 'true'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{config_id}/stats", response_model=Dict[str, Any])
async def get_pool_stats(
    config_id: int,
    pool_type: str = Query('redis', description="连接池类型：redis或device")
):
    """获取连接池状态"""
    try:
        stats = connection_pool_manager.get_pool_stats(pool_type)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取连接池状态失败: {str(e)}"
        )

@router.get("/{config_id}/metrics", response_model=Dict[str, Any])
async def get_pool_metrics(
    config_id: int,
    time_range: str = Query('1h', description="时间范围：1h, 6h, 24h"),
    pool_type: str = Query('redis', description="连接池类型：redis或device")
):
    """获取连接池指标"""
    try:
        # 这里可以根据pool_type返回不同的指标数据
        metrics = {
            'connection_history': [],
            'error_history': [],
            'resource_usage': []
        }
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取连接池指标失败: {str(e)}"
        )

@router.post("/{config_id}/cleanup")
async def cleanup_pool(
    config_id: int,
    pool_type: str = Query('redis', description="连接池类型：redis或device")
):
    """清理连接池"""
    try:
        # 这里可以根据pool_type执行不同的清理操作
        return {"message": "连接池清理成功"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"清理连接池失败: {str(e)}"
        ) 