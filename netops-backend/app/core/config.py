from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    # 数据库配置
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./netops.db"
    
    # JWT配置
    SECRET_KEY: str = secrets.token_urlsafe(32)  # 生成一个安全的随机密钥
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS配置
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    class Config:
        case_sensitive = True

settings = Settings() 