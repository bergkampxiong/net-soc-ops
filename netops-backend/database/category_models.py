from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database.models import Base

# 设备分组表
class DeviceGroup(Base):
    __tablename__ = "category_device_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联到设备成员
    members = relationship("DeviceGroupMember", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DeviceGroup {self.name}>"

# 设备成员表
class DeviceGroupMember(Base):
    __tablename__ = "category_device_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("category_device_groups.id", ondelete="CASCADE"))
    device_id = Column(Integer, nullable=False)  # 设备ID
    
    # 关联到设备分组
    group = relationship("DeviceGroup", back_populates="members")

    def __repr__(self):
        return f"<DeviceGroupMember {self.id}>"

# 凭证类型枚举
class CredentialType(str, enum.Enum):
    SSH_PASSWORD = "ssh_password"
    API_KEY = "api_key"
    SSH_KEY = "ssh_key"

# 凭证管理表
class Credential(Base):
    __tablename__ = "credential_mgt_credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    credential_type = Column(Enum(CredentialType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # 用户名（适用于SSH密码和SSH密钥）
    username = Column(String(100), nullable=True)
    
    # 密码（适用于SSH密码）
    password = Column(String(255), nullable=True)
    
    # 启用密码（适用于Cisco设备）
    enable_password = Column(String(255), nullable=True)
    
    # API密钥（适用于API凭证）
    api_key = Column(String(255), nullable=True)
    api_secret = Column(String(255), nullable=True)
    
    # SSH密钥（适用于SSH密钥）
    private_key = Column(Text, nullable=True)
    passphrase = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<Credential {self.name} ({self.credential_type})>" 