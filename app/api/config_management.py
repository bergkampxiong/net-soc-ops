from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.schemas.config import ConfigFileCreate, ConfigFileUpdate, ConfigFile, ConfigVersion
from app.services.config_management import ConfigManagementService
from app.core.auth import get_current_user

router = APIRouter()
config_service = ConfigManagementService()

@router.post("/files", response_model=ConfigFile)
async def create_config(config: ConfigFileCreate, current_user = Depends(get_current_user)):
    return config_service.create_config(config, current_user.id)

@router.get("/files", response_model=List[ConfigFile])
async def get_configs(skip: int = 0, limit: int = 10):
    return config_service.get_configs(skip, limit)

@router.get("/files/{config_id}", response_model=ConfigFile)
async def get_config(config_id: str):
    config = config_service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@router.put("/files/{config_id}", response_model=ConfigFile)
async def update_config(config_id: str, config: ConfigFileUpdate, current_user = Depends(get_current_user)):
    updated_config = config_service.update_config(config_id, config, current_user.id)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Config not found")
    return updated_config

@router.delete("/files/{config_id}")
async def delete_config(config_id: str):
    if not config_service.delete_config(config_id):
        raise HTTPException(status_code=404, detail="Config not found")
    return {"status": "success"}

@router.post("/files/{config_id}/versions", response_model=ConfigVersion)
async def create_version(config_id: str, content: str, comment: str, current_user = Depends(get_current_user)):
    version = config_service.create_version(config_id, content, comment, current_user.id)
    if not version:
        raise HTTPException(status_code=404, detail="Config not found")
    return version

@router.get("/files/{config_id}/versions", response_model=List[ConfigVersion])
async def get_versions(config_id: str):
    return config_service.get_versions(config_id)

@router.post("/render-template")
async def render_template(template_name: str, variables: dict):
    try:
        return {"content": config_service.render_template(template_name, **variables)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/parse-config")
async def parse_config(template_name: str, raw_text: str):
    try:
        return {"result": config_service.parse_with_textfsm(template_name, raw_text)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 