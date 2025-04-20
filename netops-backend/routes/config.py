from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import List, Optional
from datetime import datetime
from schemas.config import ConfigFileCreate, ConfigFileUpdate, ConfigFile, ConfigVersion
from services.config_management import ConfigManagementService
from services.config_validation import ConfigValidationService
from auth.authentication import get_current_active_user as get_current_user
from fastapi.responses import StreamingResponse, JSONResponse
import io

router = APIRouter()
config_service = ConfigManagementService()
validation_service = ConfigValidationService()

@router.post("/config/files", response_model=ConfigFile)
async def create_config(config: ConfigFileCreate, current_user = Depends(get_current_user)):
    return config_service.create_config(config, current_user.id)

@router.get("/config/files", response_model=List[ConfigFile])
async def get_configs(
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    device_type: Optional[str] = None,
    tags: Optional[str] = Query(None),
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    tag_list = tags.split(',') if tags else None
    return config_service.get_configs(
        skip=skip,
        limit=limit,
        name=name,
        device_type=device_type,
        tags=tag_list,
        status=status,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/config/files/{config_id}", response_model=ConfigFile)
async def get_config(config_id: str):
    config = config_service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@router.put("/config/files/{config_id}", response_model=ConfigFile)
async def update_config(config_id: str, config: ConfigFileUpdate, current_user = Depends(get_current_user)):
    updated_config = config_service.update_config(config_id, config, current_user.id)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Config not found")
    return updated_config

@router.delete("/config/files/{config_id}")
async def delete_config(config_id: str):
    if not config_service.delete_config(config_id):
        raise HTTPException(status_code=404, detail="Config not found")
    return {"status": "success"}

@router.post("/config/files/{config_id}/versions", response_model=ConfigVersion)
async def create_version(config_id: str, content: str, comment: str, current_user = Depends(get_current_user)):
    version = config_service.create_version(config_id, content, comment, current_user.id)
    if not version:
        raise HTTPException(status_code=404, detail="Config not found")
    return version

@router.get("/config/files/{config_id}/versions", response_model=List[ConfigVersion])
async def get_versions(config_id: str):
    return config_service.get_versions(config_id)

@router.post("/config/render-template")
async def render_template(template_name: str, variables: dict):
    try:
        return {"content": config_service.render_template(template_name, **variables)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/config/parse-config")
async def parse_config(template_name: str, raw_text: str):
    try:
        return {"result": config_service.parse_with_textfsm(template_name, raw_text)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/config/files/import")
async def import_config(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    content = await file.read()
    config_name = file.filename.rsplit('.', 1)[0]
    config = ConfigFileCreate(
        name=config_name,
        content=content.decode(),
        device_type="unknown",  # 可以根据文件内容自动检测
        tags=[],
        description=f"Imported from {file.filename}"
    )
    return config_service.create_config(config, current_user.id)

@router.get("/config/files/{config_id}/export")
async def export_config(config_id: str):
    config = config_service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    content = config.content
    filename = f"{config.name}.txt"
    
    # 创建一个字节流
    stream = io.StringIO(content)
    
    # 返回文件下载响应
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/config/validate")
async def validate_config(content: str, device_type: str):
    """验证配置内容"""
    errors = validation_service.validate_config(content, device_type)
    return {"errors": errors}

@router.post("/config/format")
async def format_config(content: str, device_type: str):
    """格式化配置内容"""
    formatted = validation_service.format_config(content, device_type)
    return {"content": formatted}

@router.post("/config/files/{config_id}/versions/compare")
async def compare_versions(config_id: str, version1_id: str, version2_id: str):
    """比较两个版本的配置"""
    v1 = config_service.get_version(config_id, version1_id)
    v2 = config_service.get_version(config_id, version2_id)
    
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Version not found")
    
    changes = validation_service.compare_versions(v1.content, v2.content)
    return {"changes": changes}

@router.post("/config/files/{config_id}/versions/{version_id}/rollback")
async def rollback_version(
    config_id: str,
    version_id: str,
    current_user = Depends(get_current_user)
):
    """回滚到指定版本"""
    success = config_service.rollback_to_version(config_id, version_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"status": "success"}

@router.get("/config/files/{config_id}/versions/{version_id}/export")
async def export_version(config_id: str, version_id: str):
    """导出特定版本的配置"""
    version = config_service.get_version(config_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    config = config_service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    filename = f"{config.name}_v{version.version}.txt"
    stream = io.StringIO(version.content)
    
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    ) 