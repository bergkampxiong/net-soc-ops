from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException

from database.models import User
from auth.authentication import get_password_hash
from schemas.user import UserCreate

def create_user(db: Session, user_data: UserCreate) -> User:
    """创建新用户"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建新用户对象
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        department=user_data.department,
        role=user_data.role,
        is_active=user_data.is_active,
        has_2fa=user_data.has_2fa,
        is_ldap_user=user_data.is_ldap_user  # 添加LDAP用户标识
    )
    
    # 如果不是LDAP用户，则设置密码
    if not user_data.is_ldap_user:
        db_user.password = get_password_hash(user_data.password)
    
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

def disable_user(db: Session, username: str):
    """禁用用户"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    user.is_active = False
    db.commit()
    
    return user

def reset_password(db: Session, username: str, new_password: str):
    """重置用户密码"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    user.hashed_password = get_password_hash(new_password)
    user.password_changed_at = datetime.utcnow().isoformat()
    db.commit()
    
    return user

def toggle_2fa(db: Session, username: str, enable: bool):
    """启用/禁用2FA"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    user.has_2fa = enable
    db.commit()
    
    return user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """获取用户列表"""
    return db.query(User).offset(skip).limit(limit).all()

def get_user_by_id(db: Session, user_id: int):
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def update_user_role(db: Session, username: str, role: str):
    """更新用户角色"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    user.role = role
    db.commit()
    
    return user

def update_user_department(db: Session, username: str, department: str):
    """更新用户部门"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    user.department = department
    db.commit()
    
    return user 