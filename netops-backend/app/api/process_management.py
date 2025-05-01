from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel
from ..models.process_management import ProcessDefinition, ProcessDefinitionVersion
from ..schemas.process_management import ProcessDefinitionCreate, ProcessDefinitionUpdate

router = APIRouter(prefix="/process-definitions", tags=["流程管理"])

# 临时存储（后续替换为数据库）
process_definitions = {}
process_versions = {}

@router.get("", response_model=List[ProcessDefinition])
async def get_process_definitions():
    """获取流程定义列表"""
    return list(process_definitions.values())

@router.post("", response_model=ProcessDefinition)
async def create_process_definition(process: ProcessDefinitionCreate):
    """创建流程定义"""
    process_id = str(uuid4())
    now = datetime.now().isoformat()
    
    new_process = ProcessDefinition(
        id=process_id,
        name=process.name,
        description=process.description,
        version=1,
        status="draft",
        nodes=process.nodes,
        edges=process.edges,
        variables=process.variables,
        created_by="admin",  # TODO: 从当前用户获取
        created_at=now,
        updated_by="admin",  # TODO: 从当前用户获取
        updated_at=now
    )
    
    process_definitions[process_id] = new_process
    return new_process

@router.get("/{process_id}", response_model=ProcessDefinition)
async def get_process_definition(process_id: str):
    """获取流程定义详情"""
    if process_id not in process_definitions:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    return process_definitions[process_id]

@router.put("/{process_id}", response_model=ProcessDefinition)
async def update_process_definition(process_id: str, process: ProcessDefinitionUpdate):
    """更新流程定义"""
    if process_id not in process_definitions:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    existing_process = process_definitions[process_id]
    now = datetime.now().isoformat()
    
    # 创建新版本
    version = ProcessDefinitionVersion(
        id=str(uuid4()),
        process_id=process_id,
        version=existing_process.version,
        nodes=existing_process.nodes,
        edges=existing_process.edges,
        variables=existing_process.variables,
        created_by=existing_process.updated_by,
        created_at=now
    )
    process_versions[version.id] = version
    
    # 更新流程定义
    updated_process = ProcessDefinition(
        **existing_process.dict(),
        name=process.name or existing_process.name,
        description=process.description or existing_process.description,
        nodes=process.nodes or existing_process.nodes,
        edges=process.edges or existing_process.edges,
        variables=process.variables or existing_process.variables,
        version=existing_process.version + 1,
        updated_by="admin",  # TODO: 从当前用户获取
        updated_at=now
    )
    
    process_definitions[process_id] = updated_process
    return updated_process

@router.delete("/{process_id}")
async def delete_process_definition(process_id: str):
    """删除流程定义"""
    if process_id not in process_definitions:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    del process_definitions[process_id]
    return {"message": "流程定义已删除"}

@router.post("/{process_id}/publish")
async def publish_process_definition(process_id: str):
    """发布流程定义"""
    if process_id not in process_definitions:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    process = process_definitions[process_id]
    process.status = "published"
    process.updated_at = datetime.now().isoformat()
    return {"message": "流程定义已发布"}

@router.post("/{process_id}/disable")
async def disable_process_definition(process_id: str):
    """禁用流程定义"""
    if process_id not in process_definitions:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    process = process_definitions[process_id]
    process.status = "disabled"
    process.updated_at = datetime.now().isoformat()
    return {"message": "流程定义已禁用"}

@router.get("/{process_id}/versions", response_model=List[ProcessDefinitionVersion])
async def get_process_versions(process_id: str):
    """获取流程版本历史"""
    versions = [v for v in process_versions.values() if v.process_id == process_id]
    return sorted(versions, key=lambda x: x.version, reverse=True)

@router.post("/{process_id}/rollback/{version}")
async def rollback_process_version(process_id: str, version: int):
    """回滚到指定版本"""
    if process_id not in process_definitions:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    target_version = next(
        (v for v in process_versions.values() 
         if v.process_id == process_id and v.version == version),
        None
    )
    if not target_version:
        raise HTTPException(status_code=404, detail="指定版本不存在")
    
    process = process_definitions[process_id]
    now = datetime.now().isoformat()
    
    # 创建新版本
    new_version = ProcessDefinitionVersion(
        id=str(uuid4()),
        process_id=process_id,
        version=process.version,
        nodes=process.nodes,
        edges=process.edges,
        variables=process.variables,
        created_by=process.updated_by,
        created_at=now
    )
    process_versions[new_version.id] = new_version
    
    # 回滚到指定版本
    process.nodes = target_version.nodes
    process.edges = target_version.edges
    process.variables = target_version.variables
    process.version = process.version + 1
    process.updated_by = "admin"  # TODO: 从当前用户获取
    process.updated_at = now
    
    return {"message": f"已回滚到版本 {version}"} 