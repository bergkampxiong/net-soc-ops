from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from services.config_generator_service import ConfigGeneratorService
from schemas.config_management import ConfigFile
from database.database import get_db

router = APIRouter()

@router.get("/templates", response_model=List[ConfigFile])
def get_jinja2_templates(
    db: Session = Depends(get_db)
):
    """获取所有jinja2类型的模板"""
    service = ConfigGeneratorService(db)
    return service.get_jinja2_templates() 