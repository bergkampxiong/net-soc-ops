from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from database.database import get_db
from services.config_management_service import ConfigManagementService
from schemas.config_management import ConfigFileCreate, ConfigFileUpdate, ConfigFile
from datetime import datetime

router = APIRouter()

@router.get("/config/files", response_model=List[ConfigFile])
def get_configs(
    device_type: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    try:
        service = ConfigManagementService(db)
        return service.get_configs(
            device_type=device_type,
            name=name,
            status=status,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置列表失败: {str(e)}")

@router.get("/config/files/{config_id}", response_model=ConfigFile)
def get_config(config_id: int, db: Session = Depends(get_db)):
    service = ConfigManagementService(db)
    config = service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config

@router.post("/config/files", response_model=ConfigFile)
def create_config(config: ConfigFileCreate, db: Session = Depends(get_db)):
    try:
        service = ConfigManagementService(db)
        # 这里使用系统用户ID，实际项目中应该从认证中间件获取
        user_id = "system"
        return service.create_config(config, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")

@router.put("/config/files/{config_id}", response_model=ConfigFile)
def update_config(config_id: int, config: ConfigFileUpdate, db: Session = Depends(get_db)):
    try:
        service = ConfigManagementService(db)
        # 这里使用系统用户ID，实际项目中应该从认证中间件获取
        user_id = "system"
        updated_config = service.update_config(config_id, config, user_id)
        if not updated_config:
            raise HTTPException(status_code=404, detail="配置不存在")
        return updated_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@router.delete("/config/files/{config_id}")
def delete_config(config_id: int, db: Session = Depends(get_db)):
    try:
        service = ConfigManagementService(db)
        if not service.delete_config(config_id):
            raise HTTPException(status_code=404, detail="配置不存在")
        return {"message": "配置已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}") 