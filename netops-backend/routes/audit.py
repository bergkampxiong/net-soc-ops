from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from database.session import get_db
from database.models import User, AuditLog
from auth.authentication import get_current_active_user
from auth.rbac import roles_required
from auth.audit import get_audit_logs as get_audit_logs_service

router = APIRouter(prefix="/api/audit", tags=["audit"])

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
    """获取审计日志"""
    logs = get_audit_logs_service(
        db=db,
        skip=skip,
        limit=limit,
        username=username,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        success=success
    )
    
    return logs

@router.get("/event-types")
@roles_required(["Admin", "Auditor"])
async def get_event_types(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取事件类型列表"""
    # 从数据库中获取所有不同的事件类型
    event_types = db.query(AuditLog.event_type).distinct().all()
    return [event_type[0] for event_type in event_types]

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