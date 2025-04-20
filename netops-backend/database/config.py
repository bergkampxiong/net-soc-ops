import os
from typing import Dict
from urllib.parse import quote_plus

# 数据库配置
DATABASE_CONFIG = {
    "host": "172.18.40.80",
    "port": 5432,
    "database": "netops",
    "user": "amber",
    "password": "amberman@2025!",
}

# Redis配置
REDIS_CONFIG = {
    "host": "172.18.40.80",
    "port": 6379,
    "db": 0,
}

# 构建数据库URL
def get_database_url(db_name: str = "netops") -> str:
    """构建数据库连接URL"""
    config = DATABASE_CONFIG.copy()
    config["database"] = db_name
    password = quote_plus(config['password'])
    return f"postgresql://{config['user']}:{password}@{config['host']}:{config['port']}/{config['database']}"

# 构建Redis URL
def get_redis_url(db: int = 0) -> str:
    """构建Redis连接URL"""
    config = REDIS_CONFIG.copy()
    config["db"] = db
    return f"redis://{config['host']}:{config['port']}/{config['db']}"

# 导出环境变量
os.environ["DATABASE_URL"] = get_database_url()
os.environ["CMDB_DATABASE_URL"] = get_database_url()  # 使用同一个数据库
os.environ["REDIS_URL"] = get_redis_url() 