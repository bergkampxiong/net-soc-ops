from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database.session import get_db
from services.config_management_service import ConfigManagementService
from schemas.config_management import ConfigFile, ConfigFileCreate, ConfigFileUpdate
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
)

@router.get("/files", response_model=List[ConfigFile])
def get_configs(
    device_type: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    try:
        print(f"Received request with device_type: {device_type}")  # 添加日志
        service = ConfigManagementService(db)
        result = service.get_configs(
            device_type=device_type,
            name=name,
            status=status,
            skip=skip,
            limit=limit
        )
        print(f"Returning {len(result)} configs")  # 添加日志
        return result
    except Exception as e:
        logger.error(f"Error getting configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/{config_id}", response_model=ConfigFile)
def get_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    try:
        service = ConfigManagementService(db)
        config = service.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return config
    except Exception as e:
        logger.error(f"Error getting config {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files", response_model=ConfigFile)
def create_config(
    config: ConfigFileCreate,
    db: Session = Depends(get_db)
):
    try:
        service = ConfigManagementService(db)
        # 这里使用系统用户ID，实际项目中应该从认证中间件获取
        user_id = "system"
        return service.create_config(config, user_id)
    except Exception as e:
        logger.error(f"Error creating config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/files/{config_id}", response_model=ConfigFile)
def update_config(
    config_id: int,
    config: ConfigFileUpdate,
    db: Session = Depends(get_db)
):
    try:
        service = ConfigManagementService(db)
        updated_config = service.update_config(config_id, config)
        if not updated_config:
            raise HTTPException(status_code=404, detail="Config not found")
        return updated_config
    except Exception as e:
        logger.error(f"Error updating config {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/files/{config_id}")
def delete_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    try:
        service = ConfigManagementService(db)
        if not service.delete_config(config_id):
            raise HTTPException(status_code=404, detail="Config not found")
        return {"message": "Config deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting config {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/search", response_model=List[ConfigFile])
def search_configs(
    name: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    try:
        service = ConfigManagementService(db)
        return service.search_configs(
            name=name,
            device_type=device_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error searching configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 