# 系统全局配置：供 netops 全局功能使用（如统一渗透测试报告 LLM 中文化）
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database.base import Base


class SystemGlobalConfig(Base):
    """系统全局配置表：如 OPENAI_API_KEY，仅后端使用。"""
    __tablename__ = "system_global_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(128), unique=True, nullable=False, index=True, comment="配置键")
    config_value = Column(Text, nullable=True, comment="配置值（敏感项脱敏展示）")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self, mask_sensitive=True):
        val = self.config_value
        if mask_sensitive and self.config_key and "key" in self.config_key.lower() and val:
            val = "********"
        return {
            "config_key": self.config_key,
            "config_value": val,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
