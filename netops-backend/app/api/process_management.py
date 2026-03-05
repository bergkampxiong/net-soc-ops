from fastapi import APIRouter, Depends, HTTPException, Response
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
from utils.datetime_utils import utc_to_beijing_str
from ..process_designer.code_generator import CodeGenerator
from ..schemas.job import JobCreate, JobUpdate
from ..services.job import JobService
from auth.authentication import get_current_user

router = APIRouter(prefix="/api/process-definitions", tags=["流程管理"])


def _row_to_process_dict(row) -> dict:
    """将查询行转为 ProcessDefinition 可用的字典，兼容 nodes/edges/variables 为 JSON 字符串的情况"""
    row_dict = dict(getattr(row, "_mapping", row))
    row_dict["created_at"] = utc_to_beijing_str(row_dict.get("created_at"))
    row_dict["updated_at"] = utc_to_beijing_str(row_dict.get("updated_at"))
    row_dict["deleted_at"] = utc_to_beijing_str(row_dict.get("deleted_at"))
    for key, default in (("nodes", []), ("edges", []), ("variables", {})):
        val = row_dict.get(key)
        if val is None:
            row_dict[key] = default
        elif isinstance(val, str):
            try:
                row_dict[key] = json.loads(val) if val else default
            except (TypeError, ValueError):
                row_dict[key] = default
    return row_dict


@router.get("", response_model=List[ProcessDefinition])
async def get_process_definitions(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取流程定义列表（已登录用户可见全部，系统管理员具备完整操作权限）"""
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE deleted_at IS NULL
    """))
    process_definitions = []
    for row in result.mappings():
        try:
            process_definitions.append(ProcessDefinition(**_row_to_process_dict(row)))
        except Exception as e:
            # 单条解析失败不拖垮整列表，可打日志
            continue
    return process_definitions

@router.post("", response_model=ProcessDefinition)
async def create_process_definition(
    process: ProcessDefinitionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建流程定义"""
    process_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    username = getattr(current_user, "username", None) or "system"

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
        'created_by': username,
        'created_at': now,
        'updated_by': username,
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
        return ProcessDefinition(**_row_to_process_dict(row))
    raise HTTPException(status_code=500, detail="创建流程定义失败")

# 带子路径的路由必须写在通用 /{process_id} 之前，否则 POST /xxx/generate-code 会被误匹配为 GET
@router.post("/{process_id}/generate-code")
async def generate_code(
    process_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """生成流程代码"""
    try:
        result = db.execute(text("""
            SELECT * FROM process_definitions 
            WHERE id = :id AND deleted_at IS NULL
        """), {'id': process_id})
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="流程定义不存在")
        process = dict(row._mapping) if hasattr(row, '_mapping') else row
        generator = CodeGenerator(process)
        code = generator.generate_code()
        headers = {
            "Content-Disposition": f"attachment; filename=process_{process_id}.py",
            "Content-Type": "text/plain; charset=utf-8"
        }
        return Response(content=code, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{process_id}", response_model=ProcessDefinition)
async def get_process_definition(
    process_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取流程定义详情"""
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE id = :id AND deleted_at IS NULL
    """), {'id': process_id})
    
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    return ProcessDefinition(**_row_to_process_dict(row))

@router.put("/{process_id}", response_model=ProcessDefinition)
async def update_process_definition(
    process_id: str,
    process: ProcessDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新流程定义"""
    # 获取现有流程定义
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE id = :id AND deleted_at IS NULL
    """), {'id': process_id})

    existing_process = result.mappings().first()
    if not existing_process:
        raise HTTPException(status_code=404, detail="流程定义不存在")

    now = datetime.utcnow().isoformat()
    ep = _row_to_process_dict(existing_process)
    username = getattr(current_user, "username", None) or "system"
    nodes_ver = ep["nodes"]
    edges_ver = ep["edges"]
    variables_ver = ep["variables"]
    nodes_ver_str = nodes_ver if isinstance(nodes_ver, str) else json.dumps(nodes_ver)
    edges_ver_str = edges_ver if isinstance(edges_ver, str) else json.dumps(edges_ver)
    variables_ver_str = variables_ver if isinstance(variables_ver, str) else json.dumps(variables_ver)

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
        'version': ep['version'],
        'nodes': nodes_ver_str,
        'edges': edges_ver_str,
        'variables': variables_ver_str,
        'created_by': ep.get('updated_by') or username,
        'created_at': now
    })

    nodes_up = json.dumps(process.nodes) if process.nodes is not None else None
    edges_up = json.dumps(process.edges) if process.edges is not None else None
    variables_up = json.dumps(process.variables) if process.variables is not None else None
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
        'nodes': nodes_up,
        'edges': edges_up,
        'variables': variables_up,
        'updated_by': username,
        'updated_at': now
    })
    
    db.commit()
    
    result = db.execute(text("""
        SELECT * FROM process_definitions 
        WHERE id = :id
    """), {'id': process_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=500, detail="更新后未查到流程")
    return ProcessDefinition(**_row_to_process_dict(row))

@router.delete("/{process_id}")
async def delete_process_definition(
    process_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """删除流程定义"""
    result = db.execute(text("""
        UPDATE process_definitions 
        SET deleted_at = :deleted_at
        WHERE id = :id AND deleted_at IS NULL
    """), {
        'id': process_id,
        'deleted_at': datetime.utcnow().isoformat()
    })
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    db.commit()
    return {"message": "流程定义已删除"}

@router.post("/{process_id}/publish")
async def publish_process_definition(
    process_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """发布流程定义；同时创建或更新作业（一次作业），供作业执行控制使用"""
    result = db.execute(text("""
        UPDATE process_definitions 
        SET status = 'published',
            updated_at = :updated_at
        WHERE id = :id AND deleted_at IS NULL
    """), {
        'id': process_id,
        'updated_at': datetime.utcnow().isoformat()
    })
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    db.commit()

    # 查询流程名称与 nodes，根据是否含渗透测试节点决定作业类型
    row = db.execute(text("SELECT name, nodes FROM process_definitions WHERE id = :id"), {'id': process_id}).fetchone()
    name = row[0] if row else process_id
    nodes_raw = row[1] if row and len(row) > 1 else None
    job_type = "config_backup"
    if nodes_raw:
        try:
            nodes_list = json.loads(nodes_raw) if isinstance(nodes_raw, str) else (nodes_raw or [])
            if any((n.get("type") == "penetrationTest" for n in nodes_list)):
                job_type = "penetration_task"
        except (TypeError, ValueError):
            pass
    job_service = JobService(db)
    existing = job_service.get_job_by_process_definition_id(process_id)
    if existing:
        job_service.update_job(existing.id, JobUpdate(name=name, job_type=job_type))
    else:
        job_service.create_job(JobCreate(
            name=name,
            job_type=job_type,
            process_definition_id=process_id,
            run_type="once",
        ))
    return {"message": "流程定义已发布"}

@router.post("/{process_id}/disable")
async def disable_process_definition(
    process_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """禁用流程定义"""
    result = db.execute(text("""
        UPDATE process_definitions 
        SET status = 'disabled',
            updated_at = :updated_at
        WHERE id = :id AND deleted_at IS NULL
    """), {
        'id': process_id,
        'updated_at': datetime.utcnow().isoformat()
    })
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    
    db.commit()
    return {"message": "流程定义已禁用"}

@router.get("/{process_id}/versions", response_model=List[ProcessDefinitionVersion])
async def get_process_versions(
    process_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取流程版本历史"""
    # 获取流程版本历史
    result = db.execute(text("""
        SELECT * FROM process_definition_versions 
        WHERE process_id = :process_id
        ORDER BY version DESC
    """), {'process_id': process_id})
    
    versions = []
    for row in result.mappings():
        row_dict = dict(row)
        # 将 datetime 对象转换为 ISO 格式字符串
        row_dict['created_at'] = utc_to_beijing_str(row_dict['created_at']) if row_dict.get('created_at') else None
        versions.append(ProcessDefinitionVersion(**row_dict))
    
    return versions

@router.post("/{process_id}/rollback/{version}")
async def rollback_process_version(
    process_id: str,
    version: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """回滚到指定版本"""
    # 获取指定版本的流程定义
    result = db.execute(text("""
        SELECT * FROM process_definition_versions 
        WHERE process_id = :process_id AND version = :version
    """), {'process_id': process_id, 'version': version})
    
    version_data = result.mappings().first()
    if not version_data:
        raise HTTPException(status_code=404, detail="指定版本不存在")
    
    now = datetime.utcnow().isoformat()
    
    # 更新流程定义
    db.execute(text("""
        UPDATE process_definitions 
        SET nodes = :nodes,
            edges = :edges,
            variables = :variables,
            version = :version,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id = :id
    """), {
        'id': process_id,
        'nodes': version_data['nodes'],
        'edges': version_data['edges'],
        'variables': version_data['variables'],
        'version': version,
        'updated_by': getattr(current_user, "username", None) or "system",
        'updated_at': now
    })
    db.commit()
    return {"message": "回滚成功"}
