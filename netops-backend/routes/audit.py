from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from database.session import get_db
from database.models import User, AuditLog
from auth.authentication import get_current_active_user
from auth.rbac import roles_required
from auth.audit import get_audit_logs as get_audit_logs_service, get_event_type_category

router = APIRouter(prefix="/api/audit", tags=["audit"])


class BatchDeleteRequest(BaseModel):
    """批量删除审计日志请求体"""
    ids: List[int] = []

@router.get("/logs")
@roles_required(["admin", "auditor"])
async def get_audit_logs(
    request: Request,
    skip: int = 0,
    limit: Optional[int] = None,
    username: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    success: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取审计日志，返回 { items, total } 便于前端分页与总条数展示"""
    logs, total = get_audit_logs_service(
        db=db,
        skip=skip,
        limit=limit,
        username=username,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        success=success
    )
    return {"items": logs, "total": total}

@router.get("/event-types")
@roles_required(["admin", "auditor"])
async def get_event_types(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取事件类型列表，含分组信息便于前端按登录/登出/首次登录等筛选"""
    event_types = db.query(AuditLog.event_type).distinct().all()
    return [
        {"event_type": et[0], "category": get_event_type_category(et[0])}
        for et in event_types
    ]

@router.delete("/logs/{log_id}")
@roles_required(["admin"])
async def delete_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按主键删除单条审计日志，仅 admin 可操作"""
    log_entry = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审计日志不存在")
    db.delete(log_entry)
    db.commit()
    return {"detail": "已删除"}


@router.post("/logs/batch-delete")
@roles_required(["admin"])
async def batch_delete_audit_logs(
    body: BatchDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量删除审计日志，仅 admin 可操作。请求体 JSON: { \"ids\": [1, 2, 3] }"""
    ids = body.ids or []
    if not ids:
        return {"detail": "已删除", "deleted_count": 0}
    deleted = db.query(AuditLog).filter(AuditLog.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"detail": "已删除", "deleted_count": deleted}


@router.get("/export")
@roles_required(["admin", "auditor"])
async def export_audit_logs(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    event_type: Optional[str] = None,
    search_text: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Implementation of export_audit_logs function
    pass