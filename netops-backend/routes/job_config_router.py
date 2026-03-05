from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from services.job_config_service import JobConfigService
from schemas.config_management import ConfigFile
from database.session import get_db
from auth.authentication import get_current_user

router = APIRouter(prefix="/config-generator", tags=["config-generator"])

@router.get("/job-templates",
    response_model=List[ConfigFile],
    summary="获取所有job类型的模板",
    description="返回系统中所有template_type为job的模板列表",
)
def get_job_templates(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取所有job类型的模板（已登录用户可见全部）"""
    service = JobConfigService(db)
    return service.get_job_templates() 