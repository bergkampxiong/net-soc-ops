from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import pytz

from database.models import AuditLog, User

def log_event(
    db: Session,
    event_type: str,
    user: User = None,
    username: str = None,
    ip_address: str = None,
    user_agent: str = None,
    details: dict = None,
    success: bool = True
):
    """记录审计日志"""
    # 如果提供了user对象，从中获取username
    user_id = user.id if user else None
    user_name = user.username if user else username
    
    # 使用带时区的时间
    timezone = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(timezone)
    
    log_entry = AuditLog(
        timestamp=current_time.isoformat(),
        user_id=user_id,
        username=user_name,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        details=json.dumps(details) if details else None,
        success=success
    )
    
    db.add(log_entry)
    db.commit()
    
    return log_entry

def get_audit_logs(
    db: Session,
    skip: int = 0,
    limit: int = None,  # 修改为None，表示不限制数量
    username: str = None,
    event_type: str = None,
    start_date: str = None,
    end_date: str = None,
    success: bool = None
):
    """获取审计日志"""
    query = db.query(AuditLog)
    
    # 应用过滤条件
    if username:
        query = query.filter(AuditLog.username == username)
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    if success is not None:
        query = query.filter(AuditLog.success == success)
    
    # 排序和分页
    query = query.order_by(AuditLog.timestamp.desc())
    
    # 应用分页，但如果limit为None则不限制数量
    if skip > 0:
        query = query.offset(skip)
    
    if limit is not None:
        query = query.limit(limit)
    
    return query.all()

def cleanup_old_logs(db: Session, months: int = 3):
    """清理超过指定月数的旧日志"""
    timezone = pytz.timezone('Asia/Shanghai')
    cutoff_date = datetime.now(timezone) - timedelta(days=months*30)
    cutoff_date_str = cutoff_date.isoformat()
    
    # 删除旧日志
    deleted_count = db.query(AuditLog).filter(AuditLog.timestamp < cutoff_date_str).delete()
    db.commit()
    
    return deleted_count 