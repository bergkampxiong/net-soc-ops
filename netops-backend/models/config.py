from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database.base import Base
import datetime

class ConfigFile(Base):
    __tablename__ = "config_files"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    device_type = Column(String, nullable=False)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = Column(String, nullable=False)
    
    versions = relationship("ConfigVersion", back_populates="config", cascade="all, delete-orphan")

class ConfigVersion(Base):
    __tablename__ = "config_versions"
    
    id = Column(String, primary_key=True)
    config_id = Column(String, ForeignKey("config_files.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False)
    
    config = relationship("ConfigFile", back_populates="versions")
    
    __table_args__ = (
        UniqueConstraint('config_id', 'version', name='uix_config_version'),
    ) 