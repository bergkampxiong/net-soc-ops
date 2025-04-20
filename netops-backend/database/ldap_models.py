from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .base import Base
from datetime import datetime

class LDAPTemplate(Base):
    """LDAP模板数据库模型"""
    __tablename__ = "ldap_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False, comment="模板名称")
    server_url = Column(String(255), nullable=False, comment="LDAP服务器地址")
    port = Column(Integer, default=389, comment="LDAP服务器端口")
    bind_dn = Column(String(255), nullable=False, comment="绑定DN")
    bind_password = Column(String(255), nullable=False, comment="绑定密码")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间") 