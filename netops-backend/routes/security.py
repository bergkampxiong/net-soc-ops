from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from database.session import get_db
from database.models import SecuritySettings, User
from auth.authentication import get_current_active_user

router = APIRouter()

class SecuritySettingsModel(BaseModel):
    password_expiry_days: int
    max_failed_attempts: int
    lockout_duration_minutes: int
    session_timeout_minutes: int
    require_2fa_for_admins: bool
    password_complexity_enabled: bool
    password_min_length: int
    password_require_uppercase: bool
    password_require_lowercase: bool
    password_require_numbers: bool
    password_require_special: bool

@router.get("/settings")
async def get_security_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取安全设置"""
    # 检查用户权限
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # 获取安全设置
    settings = db.query(SecuritySettings).first()
    
    # 如果没有设置，创建默认设置
    if not settings:
        settings = SecuritySettings(
            password_expiry_days=90,
            max_failed_attempts=5,
            lockout_duration_minutes=15,
            session_timeout_minutes=30,
            require_2fa_for_admins=True,
            password_complexity_enabled=True,
            password_min_length=8,
            password_require_uppercase=True,
            password_require_lowercase=True,
            password_require_numbers=True,
            password_require_special=False
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return {
        "password_expiry_days": settings.password_expiry_days,
        "max_failed_attempts": settings.max_failed_attempts,
        "lockout_duration_minutes": settings.lockout_duration_minutes,
        "session_timeout_minutes": settings.session_timeout_minutes,
        "require_2fa_for_admins": settings.require_2fa_for_admins,
        "password_complexity_enabled": settings.password_complexity_enabled,
        "password_min_length": settings.password_min_length,
        "password_require_uppercase": settings.password_require_uppercase,
        "password_require_lowercase": settings.password_require_lowercase,
        "password_require_numbers": settings.password_require_numbers,
        "password_require_special": settings.password_require_special
    }

@router.put("/settings")
async def update_security_settings(
    settings_data: SecuritySettingsModel,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新安全设置"""
    # 检查用户权限
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # 获取安全设置
    settings = db.query(SecuritySettings).first()
    
    # 如果没有设置，创建新设置
    if not settings:
        settings = SecuritySettings()
        db.add(settings)
    
    # 更新设置
    settings.password_expiry_days = settings_data.password_expiry_days
    settings.max_failed_attempts = settings_data.max_failed_attempts
    settings.lockout_duration_minutes = settings_data.lockout_duration_minutes
    settings.session_timeout_minutes = settings_data.session_timeout_minutes
    settings.require_2fa_for_admins = settings_data.require_2fa_for_admins
    settings.password_complexity_enabled = settings_data.password_complexity_enabled
    settings.password_min_length = settings_data.password_min_length
    settings.password_require_uppercase = settings_data.password_require_uppercase
    settings.password_require_lowercase = settings_data.password_require_lowercase
    settings.password_require_numbers = settings_data.password_require_numbers
    settings.password_require_special = settings_data.password_require_special
    
    db.commit()
    db.refresh(settings)
    
    return {
        "message": "Security settings updated successfully",
        "settings": {
            "password_expiry_days": settings.password_expiry_days,
            "max_failed_attempts": settings.max_failed_attempts,
            "lockout_duration_minutes": settings.lockout_duration_minutes,
            "session_timeout_minutes": settings.session_timeout_minutes,
            "require_2fa_for_admins": settings.require_2fa_for_admins,
            "password_complexity_enabled": settings.password_complexity_enabled,
            "password_min_length": settings.password_min_length,
            "password_require_uppercase": settings.password_require_uppercase,
            "password_require_lowercase": settings.password_require_lowercase,
            "password_require_numbers": settings.password_require_numbers,
            "password_require_special": settings.password_require_special
        }
    } 