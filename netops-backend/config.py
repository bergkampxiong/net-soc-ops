from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    # 基础配置
    PROJECT_NAME: str = "NetOps"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./netops.db")
    
    # Redis配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # LDAP配置
    LDAP_SERVER: Optional[str] = os.getenv("LDAP_SERVER")
    LDAP_PORT: int = int(os.getenv("LDAP_PORT", "389"))
    LDAP_BASE_DN: Optional[str] = os.getenv("LDAP_BASE_DN")
    LDAP_USER_DN: Optional[str] = os.getenv("LDAP_USER_DN")
    LDAP_ADMIN_DN: Optional[str] = os.getenv("LDAP_ADMIN_DN")
    LDAP_ADMIN_PASSWORD: Optional[str] = os.getenv("LDAP_ADMIN_PASSWORD")
    
    # 安全设置
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # 会话设置
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    
    class Config:
        case_sensitive = True

# 创建全局设置实例
settings = Settings() 