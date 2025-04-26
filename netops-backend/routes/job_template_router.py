from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..services.job_template_service import JobTemplateService
from ..models.config_file import ConfigFile
from ..database import get_db

router = APIRouter(prefix="/config-generator")

@router.get("/job-templates", response_model=List[ConfigFile])
async def get_job_templates(db: Session = Depends(get_db)):
    service = JobTemplateService(db)
    return await service.get_job_templates() 