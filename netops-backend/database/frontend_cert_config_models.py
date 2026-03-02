# 前端证书配置表：自签名或导入 CA 证书，供开发环境 HTTPS 使用
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database.base import Base


class FrontendCertConfig(Base):
    """前端证书配置（单例：仅保留一行）。"""
    __tablename__ = "frontend_cert_config"

    id = Column(Integer, primary_key=True, index=True)
    cert_mode = Column(String(32), nullable=False, default="self_signed", comment="self_signed | ca_import")
    validity_days = Column(Integer, nullable=True, comment="自签名证书有效期（天），仅 cert_mode=self_signed 时有效")
    enable_https = Column(Boolean, nullable=False, default=False, comment="是否启用开发环境 HTTPS")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
