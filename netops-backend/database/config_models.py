from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .models import Base

class ConfigFile(Base):
    __tablename__ = "config_files"

    id = Column(String, primary_key=True)
    name = Column(String, index=True)
    device_type = Column(String)
    description = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    status = Column(String, default="draft")
    template_type = Column(String, default="jinja2")
    content = Column(String)
    created_at = Column(String)
    updated_at = Column(String)
    created_by = Column(String)
    updated_by = Column(String)

class ConfigVersion(Base):
    __tablename__ = "config_versions"

    id = Column(String, primary_key=True)
    config_id = Column(String, ForeignKey("config_files.id"))
    version = Column(String)
    content = Column(String)
    comment = Column(String)
    created_at = Column(String)
    created_by = Column(String)

    config = relationship("ConfigFile", back_populates="versions")

ConfigFile.versions = relationship("ConfigVersion", order_by=ConfigVersion.created_at, back_populates="config") 