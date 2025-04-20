from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database.session import get_db
from database.category_models import ApiConfig
from schemas.api_config import ApiConfig as ApiConfigSchema
from schemas.api_config import ApiConfigCreate, ApiConfigUpdate
from crud import api_config as crud_api_config

router = APIRouter()

@router.get("/api_configs", response_model=List[ApiConfigSchema])
def get_api_configs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有API配置"""
    return crud_api_config.get_api_configs(db, skip=skip, limit=limit)

@router.post("/api_config", response_model=ApiConfigSchema)
def create_api_config(api_config: ApiConfigCreate, db: Session = Depends(get_db)):
    """创建新的API配置"""
    return crud_api_config.create_api_config(db=db, api_config=api_config)

@router.get("/api_config/{api_config_id}", response_model=ApiConfigSchema)
def get_api_config(api_config_id: int, db: Session = Depends(get_db)):
    """获取指定的API配置"""
    db_api_config = crud_api_config.get_api_config(db, api_config_id=api_config_id)
    if db_api_config is None:
        raise HTTPException(status_code=404, detail="API配置不存在")
    return db_api_config

@router.put("/api_config/{api_config_id}", response_model=ApiConfigSchema)
def update_api_config(api_config_id: int, api_config: ApiConfigUpdate, db: Session = Depends(get_db)):
    """更新API配置"""
    db_api_config = crud_api_config.update_api_config(db, api_config_id=api_config_id, api_config=api_config)
    if db_api_config is None:
        raise HTTPException(status_code=404, detail="API配置不存在")
    return db_api_config

@router.delete("/api_config/{api_config_id}")
def delete_api_config(api_config_id: int, db: Session = Depends(get_db)):
    """删除API配置"""
    success = crud_api_config.delete_api_config(db, api_config_id=api_config_id)
    if not success:
        raise HTTPException(status_code=404, detail="API配置不存在")
    return {"message": "API配置已删除"} 