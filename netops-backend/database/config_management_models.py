from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.base import Base
from datetime import datetime
from sqlalchemy.sql import func

class ConfigFile(Base):
    __tablename__ = "rpa_config_files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    template_type = Column(String(20), nullable=False)  # jinja2, textfsm, job
    content = Column(Text, nullable=False)
    description = Column(String(500), nullable=True)
    device_type = Column(String(50), nullable=False, default='cisco_ios')
    status = Column(String(20), nullable=False, default='draft')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ConfigFile(id={self.id}, name='{self.name}', template_type='{self.template_type}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'template_type': self.template_type,
            'content': self.content,
            'description': self.description,
            'device_type': self.device_type,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 