from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.process_management import ProcessDefinition, ProcessDefinitionVersion
from ..schemas.process_management import ProcessDefinitionCreate, ProcessDefinitionUpdate
from database.session import get_db

router = APIRouter(prefix="/api/process-definitions", tags=["流程管理"])

@router.get("", response_model=List[ProcessDefinition])
async def get_process_definitions(db: Session = Depends(get_db)):
    """获取流程定义列表"""
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE deleted_at IS NULL
    """))
    
    # 处理查询结果，确保符合模型要求
    process_definitions = []
    for row in result.mappings():
        # 将 datetime 对象转换为 ISO 格式字符串
        row_dict = dict(row)
        row_dict['created_at'] = row_dict['created_at'].isoformat() if row_dict['created_at'] else None
        row_dict['updated_at'] = row_dict['updated_at'].isoformat() if row_dict['updated_at'] else None
        row_dict['deleted_at'] = row_dict['deleted_at'].isoformat() if row_dict['deleted_at'] else None
        
        # 确保 variables 是字典类型
        if row_dict['variables'] is None:
            row_dict['variables'] = {}
            
        process_definitions.append(ProcessDefinition(**row_dict))
    
    return process_definitions

@router.post("", response_model=ProcessDefinition)
async def create_process_definition(process: ProcessDefinitionCreate, db: Session = Depends(get_db)):
    """创建流程定义"""
    process_id = str(uuid4())
    now = datetime.now().isoformat()
    
    # 将 JSON 数据序列化为字符串
    nodes_json = json.dumps(process.nodes)
    edges_json = json.dumps(process.edges)
    variables_json = json.dumps(process.variables)
    
    db.execute(text("""
        INSERT INTO process_definitions (
            id, name, description, version, status, nodes, edges, variables,
            created_by, created_at, updated_by, updated_at
        ) VALUES (
            :id, :name, :description, :version, :status, :nodes, :edges, :variables,
            :created_by, :created_at, :updated_by, :updated_at
        )
    """), {
        'id': process_id,
        'name': process.name,
        'description': process.description,
        'version': 1,
        'status': 'draft',
        'nodes': nodes_json,
        'edges': edges_json,
        'variables': variables_json,
        'created_by': 'admin',  # TODO: 从当前用户获取
        'created_at': now,
        'updated_by': 'admin',  # TODO: 从当前用户获取
        'updated_at': now
    })
    
    db.commit()
    
    # 获取新创建的流程定义
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE id = :id
    """), {'id': process_id})
    
    row = result.mappings().first()
    if row:
        # 将数据库返回的数据转换为字典
        row_dict = dict(row)
        # 将 datetime 对象转换为 ISO 格式字符串
        row_dict['created_at'] = row_dict['created_at'].isoformat() if row_dict['created_at'] else None
        row_dict['updated_at'] = row_dict['updated_at'].isoformat() if row_dict['updated_at'] else None
        row_dict['deleted_at'] = row_dict['deleted_at'].isoformat() if row_dict['deleted_at'] else None
        return ProcessDefinition(**row_dict)
    else:
        raise HTTPException(status_code=500, detail="创建流程定义失败")

@router.get("/{process_id}", response_model=ProcessDefinition)
async def get_process_definition(process_id: str, db: Session = Depends(get_db)):
    """获取流程定义详情"""
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE id = :id AND deleted_at IS NULL
    """), {'id': process_id})
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    # 将数据库返回的数据转换为字典
    row_dict = dict(row)
    # 将 datetime 对象转换为 ISO 格式字符串
    row_dict['created_at'] = row_dict['created_at'].isoformat() if row_dict['created_at'] else None
    row_dict['updated_at'] = row_dict['updated_at'].isoformat() if row_dict['updated_at'] else None
    row_dict['deleted_at'] = row_dict['deleted_at'].isoformat() if row_dict['deleted_at'] else None
    
    return ProcessDefinition(**row_dict)

@router.put("/{process_id}", response_model=ProcessDefinition)
async def update_process_definition(process_id: str, process: ProcessDefinitionUpdate, db: Session = Depends(get_db)):
    """更新流程定义"""
    # 获取现有流程定义
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE id = :id AND deleted_at IS NULL
    """), {'id': process_id})
    
    existing_process = result.mappings().first()
    if not existing_process:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    now = datetime.now().isoformat()
    
    # 创建新版本
    db.execute(text("""
        INSERT INTO process_definition_versions (
            id, process_id, version, nodes, edges, variables,
            created_by, created_at
        ) VALUES (
            :id, :process_id, :version, :nodes, :edges, :variables,
            :created_by, :created_at
        )
    """), {
        'id': str(uuid4()),
        'process_id': process_id,
        'version': existing_process['version'],
        'nodes': existing_process['nodes'],
        'edges': existing_process['edges'],
        'variables': existing_process['variables'],
        'created_by': existing_process['updated_by'],
        'created_at': now
    })
    
    # 更新流程定义
    db.execute(text("""
        UPDATE process_definitions 
        SET name = COALESCE(:name, name),
            description = COALESCE(:description, description),
            version = version + 1,
            nodes = COALESCE(:nodes, nodes),
            edges = COALESCE(:edges, edges),
            variables = COALESCE(:variables, variables),
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id = :id
    """), {
        'id': process_id,
        'name': process.name,
        'description': process.description,
        'nodes': process.nodes,
        'edges': process.edges,
        'variables': process.variables,
        'updated_by': 'admin',  # TODO: 从当前用户获取
        'updated_at': now
    })
    
    db.commit()
    
    # 获取更新后的流程定义
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE id = :id
    """), {'id': process_id})
    
    return ProcessDefinition(**result.mappings().first())

@router.delete("/{process_id}")
async def delete_process_definition(process_id: str, db: Session = Depends(get_db)):
    """删除流程定义"""
    result = db.execute(text("""
        UPDATE process_definitions 
        SET deleted_at = :deleted_at
        WHERE id = :id AND deleted_at IS NULL
    """), {
        'id': process_id,
        'deleted_at': datetime.now().isoformat()
    })
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    db.commit()
    return {"message": "流程定义已删除"}

@router.post("/{process_id}/publish")
async def publish_process_definition(process_id: str, db: Session = Depends(get_db)):
    """发布流程定义"""
    result = db.execute(text("""
        UPDATE process_definitions 
        SET status = 'published',
            updated_at = :updated_at
        WHERE id = :id AND deleted_at IS NULL
    """), {
        'id': process_id,
        'updated_at': datetime.now().isoformat()
    })
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    db.commit()
    return {"message": "流程定义已发布"}

@router.post("/{process_id}/disable")
async def disable_process_definition(process_id: str, db: Session = Depends(get_db)):
    """禁用流程定义"""
    result = db.execute(text("""
        UPDATE process_definitions 
        SET status = 'disabled',
            updated_at = :updated_at
        WHERE id = :id AND deleted_at IS NULL
    """), {
        'id': process_id,
        'updated_at': datetime.now().isoformat()
    })
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    db.commit()
    return {"message": "流程定义已禁用"}

@router.get("/{process_id}/versions", response_model=List[ProcessDefinitionVersion])
async def get_process_versions(process_id: str):
    """获取流程版本历史"""
    # This endpoint is no longer available in the new implementation
    raise HTTPException(status_code=404, detail="此功能已移除")

@router.post("/{process_id}/rollback/{version}")
async def rollback_process_version(process_id: str, version: int):
    """回滚到指定版本"""
    # This endpoint is no longer available in the new implementation
    raise HTTPException(status_code=404, detail="此功能已移除") 