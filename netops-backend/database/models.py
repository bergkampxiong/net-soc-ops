from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String, default="user")  # admin, operator, auditor, user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 新增字段
    is_ldap_user = Column(Boolean, default=False)  # 是否为LDAP用户
    ldap_dn = Column(String, nullable=True)  # LDAP Distinguished Name
    department = Column(String, nullable=True)  # 部门
    
    # 2FA相关
    has_2fa = Column(Boolean, default=False)  # 是否启用2FA
    totp_secret = Column(String, nullable=True)  # TOTP密钥
    
    # 安全相关
    failed_login_attempts = Column(Integer, default=0)  # 失败登录尝试次数
    locked_until = Column(String, nullable=True)  # 锁定截止时间
    last_login = Column(String, nullable=True)  # 最后登录时间
    password_changed_at = Column(String, nullable=True)  # 密码最后修改时间

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String)  # 事件时间
    user_id = Column(Integer, nullable=True)  # 关联用户ID
    username = Column(String, nullable=True)  # 用户名
    event_type = Column(String)  # 事件类型: login, logout, password_change等
    ip_address = Column(String, nullable=True)  # IP地址
    user_agent = Column(String, nullable=True)  # 用户代理
    details = Column(String, nullable=True)  # 详细信息，JSON格式
    success = Column(Boolean, default=True)  # 操作是否成功

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)  # 关联用户ID
    token = Column(String, unique=True, index=True)  # 刷新令牌
    expires_at = Column(String)  # 过期时间
    is_revoked = Column(Boolean, default=False)  # 是否已撤销

class LDAPConfig(Base):
    __tablename__ = "ldap_config"
    
    id = Column(Integer, primary_key=True, index=True)
    server_url = Column(String)  # LDAP服务器URL
    bind_dn = Column(String)  # 绑定DN
    bind_password = Column(String)  # 绑定密码
    search_base = Column(String)  # 搜索基础
    use_ssl = Column(Boolean, default=False)  # 是否使用SSL
    user_search_filter = Column(String, default="(sAMAccountName={username})")  # 用户搜索过滤器
    admin_group_dn = Column(String, nullable=True)  # 管理员组DN
    auditor_group_dn = Column(String, nullable=True)  # 审计员组DN
    require_2fa = Column(Boolean, default=False)  # 是否要求2FA

class UsedTOTP(Base):
    __tablename__ = "used_totp"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)  # 关联用户ID
    totp_code = Column(String)  # TOTP验证码
    used_at = Column(String)  # 使用时间
    expires_at = Column(String)  # 过期时间（用于清理）

class SecuritySettings(Base):
    __tablename__ = "security_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    password_expiry_days = Column(Integer, default=90)  # 密码过期时间（天）
    max_failed_attempts = Column(Integer, default=5)  # 最大失败尝试次数
    lockout_duration_minutes = Column(Integer, default=15)  # 账号锁定时长（分钟）
    session_timeout_minutes = Column(Integer, default=30)  # 会话超时时间（分钟）
    require_2fa_for_admins = Column(Boolean, default=True)  # 管理员强制启用双因素认证
    password_complexity_enabled = Column(Boolean, default=True)  # 启用密码复杂度要求
    password_min_length = Column(Integer, default=8)  # 密码最小长度
    password_require_uppercase = Column(Boolean, default=True)  # 要求包含大写字母
    password_require_lowercase = Column(Boolean, default=True)  # 要求包含小写字母
    password_require_numbers = Column(Boolean, default=True)  # 要求包含数字
    password_require_special = Column(Boolean, default=False)  # 要求包含特殊字符 