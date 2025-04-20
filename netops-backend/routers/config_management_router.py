from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from netops_backend.services.config_management_service import ConfigManagementService
from netops_backend.schemas.config_management import ConfigFile
from netops_backend.database.database import get_db

router = APIRouter()

@router.get("/files", response_model=List[ConfigFile])
def get_configs(
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取配置列表"""
    service = ConfigManagementService(db)
    return service.get_configs(template_type=type) 