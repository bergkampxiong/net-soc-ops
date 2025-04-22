from fastapi import APIRouter, HTTPException
from typing import Dict, List
from .device_connection_pool import connection_pool

router = APIRouter()

@router.get("/status", response_model=List[Dict])
async def get_connection_status():
    """获取所有设备连接状态"""
    return await connection_pool.get_connection_status()

@router.post("/connect")
async def connect_device(device_info: Dict):
    """连接设备"""
    try:
        success = await connection_pool.connect_device(device_info)
        if not success:
            raise HTTPException(status_code=500, detail="设备连接失败")
        return {"message": "设备连接成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disconnect/{device_id}")
async def disconnect_device(device_id: str):
    """断开设备连接"""
    success = await connection_pool.disconnect_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="设备未找到或断开连接失败")
    return {"message": "设备断开连接成功"}

@router.get("/stats")
async def get_pool_stats():
    """获取连接池统计信息"""
    return connection_pool.get_stats() 