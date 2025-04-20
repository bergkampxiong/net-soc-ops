from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_database_url
from .session import get_db

# 创建数据库引擎
cmdb_engine = create_engine(
    get_database_url()  # 使用netops数据库
)

# 创建会话工厂
CMDBSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cmdb_engine)

# 创建基类
CMDBBase = declarative_base()

# 使用主数据库会话
get_cmdb_db = get_db

def get_cmdb_db():
    """获取数据库会话"""
    db = CMDBSessionLocal()
    try:
        yield db
    finally:
        db.close() 