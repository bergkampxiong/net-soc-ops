from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import re

from database.session import get_db
from database.models import User, SecuritySettings, LDAPConfig
from schemas.user import UserOut, UserCreate
from auth.authentication import get_current_active_user, verify_password, get_password_hash
from auth.rbac import role_required, roles_required, permission_required
from auth.user_management import (
    create_user as create_user_service,
    disable_user as disable_user_service,
    reset_password as reset_password_service,
    toggle_2fa as toggle_2fa_service,
    get_users as get_users_service,
    update_user_role as update_user_role_service,
    update_user_department as update_user_department_service
)
from auth.audit import log_event
from utils.ldap_utils import test_ldap_connection

router = APIRouter(prefix="/api/users", tags=["users"])

# 用户更新模型
class UserUpdate(BaseModel):
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    totp_enabled: Optional[bool] = None
    permissions: Optional[dict] = None

# 用户删除请求模型
class UserDeleteRequest(BaseModel):
    username: str

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user

@router.get("/", response_model=List[UserOut])
# 暂时移除角色检查以便调试
# @roles_required(["admin", "auditor"])
async def get_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    try:
        # 手动检查角色
        if current_user.role not in ["admin", "auditor"]:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # 获取所有用户
        users = db.query(User).offset(skip).limit(limit).all()
        return users
    except Exception as e:
        raise

@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建新用户"""
    # 检查权限
    if current_user.role not in ["admin", "superuser"]:
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以创建用户"
        )
    
    # 如果是LDAP用户，验证LDAP配置
    if user.is_ldap_user:
        # 获取LDAP配置
        ldap_config = db.query(LDAPConfig).first()
        if not ldap_config:
            raise HTTPException(
                status_code=400,
                detail="LDAP未配置，无法创建LDAP用户"
            )
        
        # 测试LDAP连接
        try:
            test_ldap_connection(
                server_url=ldap_config.server_url,
                bind_dn=ldap_config.bind_dn,
                bind_password=ldap_config.bind_password,
                search_base=ldap_config.search_base,
                use_ssl=ldap_config.use_ssl
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"LDAP连接测试失败: {str(e)}"
            )
    
    # 创建用户
    try:
        # 创建新用户对象
        db_user = User(
            username=user.username,
            email=user.email,
            department=user.department,
            role=user.role,  # 直接使用传入的角色
            is_active=user.is_active,
            has_2fa=user.has_2fa,
            is_ldap_user=user.is_ldap_user
        )
        
        # 如果不是LDAP用户，则设置密码
        if not user.is_ldap_user:
            db_user.password = get_password_hash(user.password)
        
        # 设置默认值
        if not db_user.role:
            db_user.role = "operator"
        if db_user.is_active is None:
            db_user.is_active = True
        if db_user.has_2fa is None:
            db_user.has_2fa = False
        
        # 保存到数据库
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建用户失败: {str(e)}"
        )

@router.post("/disable")
@role_required("admin")
async def disable_user(
    request: Request,
    username: str = Body(...),
    enable: Optional[bool] = Body(None),  # 添加可选参数，用于指定是启用还是禁用
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """禁用/启用用户"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    # 查找用户
    user = db.query(User).filter(User.username == username).first()
    if not user:
        log_event(
            db=db,
            event_type="toggle_user_status",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "User not found", "username": username}
        )
        raise HTTPException(status_code=404, detail="User not found")
    
    # 如果提供了enable参数，则使用它；否则，切换当前状态
    if enable is not None:
        user.is_active = enable
    else:
        user.is_active = not user.is_active
    
    db.commit()
    
    action = "enable" if user.is_active else "disable"
    log_event(
        db=db,
        event_type=f"{action}_user",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        details={"username": username, "is_active": user.is_active}
    )
    
    return {"detail": f"User {action}d successfully"}

@router.post("/reset-password")
@role_required("admin")
async def reset_password(
    request: Request,
    username: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """重置用户密码"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    user = reset_password_service(db, username, new_password)
    if not user:
        log_event(
            db=db,
            event_type="reset_password",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "User not found", "username": username}
        )
        raise HTTPException(status_code=404, detail="User not found")
    
    log_event(
        db=db,
        event_type="reset_password",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        details={"username": username}
    )
    
    return {"detail": "Password reset successfully"}

@router.post("/toggle-2fa")
@role_required("admin")
async def toggle_2fa(
    request: Request,
    username: str = Body(...),
    enable: bool = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """启用/禁用2FA"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    user = toggle_2fa_service(db, username, enable)
    if not user:
        log_event(
            db=db,
            event_type="toggle_2fa",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "User not found", "username": username}
        )
        raise HTTPException(status_code=404, detail="User not found")
    
    log_event(
        db=db,
        event_type="toggle_2fa",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        details={"username": username, "enable": enable}
    )
    
    return {"detail": "2FA status updated successfully"}

@router.post("/update-role")
@role_required("admin")
async def update_role(
    request: Request,
    username: str = Body(...),
    role: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新用户角色"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    if role not in ["Admin", "Operator", "Auditor"]:
        log_event(
            db=db,
            event_type="update_role",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "Invalid role", "username": username, "role": role}
        )
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = update_user_role_service(db, username, role)
    if not user:
        log_event(
            db=db,
            event_type="update_role",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "User not found", "username": username}
        )
        raise HTTPException(status_code=404, detail="User not found")
    
    log_event(
        db=db,
        event_type="update_role",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        details={"username": username, "role": role}
    )
    
    return {"detail": "User role updated successfully"}

@router.post("/update-department")
@role_required("admin")
async def update_department(
    request: Request,
    username: str = Body(...),
    department: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新用户部门"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    user = update_user_department_service(db, username, department)
    if not user:
        log_event(
            db=db,
            event_type="update_department",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "User not found", "username": username}
        )
        raise HTTPException(status_code=404, detail="User not found")
    
    log_event(
        db=db,
        event_type="update_department",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        details={"username": username, "department": department}
    )
    
    return {"detail": "User department updated successfully"}

@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    # 检查权限
    if current_user.role not in ["admin", "superuser"]:
        raise HTTPException(
            status_code=403,
            detail="没有权限执行此操作"
        )
    
    # 获取要更新的用户
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    # 如果是LDAP用户，只允许更新部分字段
    if db_user.is_ldap_user:
        # 不允许更改用户名和密码
        if user_update.username and user_update.username != db_user.username:
            raise HTTPException(
                status_code=400,
                detail="不能更改LDAP用户的用户名"
            )
        if user_update.password:
            raise HTTPException(
                status_code=400,
                detail="不能更改LDAP用户的密码"
            )
        
        # 只允许更新以下字段
        update_data = user_update.dict(exclude_unset=True)
        allowed_fields = {"email", "department", "is_active", "role", "permissions"}
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        # 更新用户信息
        for field, value in update_data.items():
            if field == "permissions" and value:
                # 确保权限格式正确
                if not isinstance(value, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="权限格式不正确，应为字典格式"
                    )
                # 验证权限值
                for perm_key, perm_value in value.items():
                    if not isinstance(perm_value, bool):
                        raise HTTPException(
                            status_code=400,
                            detail=f"权限 {perm_key} 的值必须为布尔类型"
                        )
            setattr(db_user, field, value)
    else:
        # 非LDAP用户可以更新所有字段
        update_data = user_update.dict(exclude_unset=True)
        
        # 如果更新密码，需要哈希处理
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        # 更新用户信息
        for field, value in update_data.items():
            if field == "permissions" and value:
                # 确保权限格式正确
                if not isinstance(value, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="权限格式不正确，应为字典格式"
                    )
                # 验证权限值
                for perm_key, perm_value in value.items():
                    if not isinstance(perm_value, bool):
                        raise HTTPException(
                            status_code=400,
                            detail=f"权限 {perm_key} 的值必须为布尔类型"
                        )
            setattr(db_user, field, value)
    
    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新用户失败: {str(e)}"
        )

@router.post("/delete")
@role_required("admin")
async def delete_user(
    request: Request,
    user_delete: UserDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除用户"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    # 不允许删除自己
    if user_delete.username == current_user.username:
        log_event(
            db=db,
            event_type="delete_user",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "Cannot delete yourself", "username": user_delete.username}
        )
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # 查找用户
    user = db.query(User).filter(User.username == user_delete.username).first()
    if not user:
        log_event(
            db=db,
            event_type="delete_user",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "User not found", "username": user_delete.username}
        )
        raise HTTPException(status_code=404, detail="User not found")
    
    # 删除用户
    db.delete(user)
    db.commit()
    
    log_event(
        db=db,
        event_type="delete_user",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        details={"username": user_delete.username}
    )
    
    return {"detail": "User deleted successfully"}

@router.post("/change-password")
async def change_password(
    request: Request,
    old_password: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """修改当前用户密码"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    # 验证旧密码
    if not verify_password(old_password, current_user.hashed_password):
        log_event(
            db=db,
            event_type="change_password",
            user=current_user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": "Invalid old password"}
        )
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    # 获取密码策略
    settings = db.query(SecuritySettings).first()
    if not settings:
        settings = SecuritySettings()
    
    # 验证新密码是否符合密码策略
    if settings.password_complexity_enabled:
        # 检查密码长度
        if len(new_password) < settings.password_min_length:
            raise HTTPException(
                status_code=400, 
                detail=f"Password must be at least {settings.password_min_length} characters long"
            )
        
        # 检查是否包含大写字母
        if settings.password_require_uppercase and not re.search(r'[A-Z]', new_password):
            raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
        
        # 检查是否包含小写字母
        if settings.password_require_lowercase and not re.search(r'[a-z]', new_password):
            raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
        
        # 检查是否包含数字
        if settings.password_require_numbers and not re.search(r'[0-9]', new_password):
            raise HTTPException(status_code=400, detail="Password must contain at least one number")
        
        # 检查是否包含特殊字符
        if settings.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            raise HTTPException(status_code=400, detail="Password must contain at least one special character")
    
    # 更新密码
    current_user.hashed_password = get_password_hash(new_password)
    current_user.password_changed_at = datetime.utcnow().isoformat()
    db.commit()
    
    log_event(
        db=db,
        event_type="change_password",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True
    )
    
    return {"detail": "Password changed successfully"} 