from dotenv import load_dotenv
load_dotenv()

# 统一使用北京时区（日志、APScheduler 等依赖本地时间的逻辑），避免重启后系统 TZ 非 Asia/Shanghai 导致时间偏差
import os
import time
import logging
# 降低 watchfiles 日志级别，避免 "2 changes detected" 反复刷屏
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
_ = os.environ.setdefault("TZ", "Asia/Shanghai")
if hasattr(time, "tzset"):
    time.tzset()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import warnings
from sqlalchemy import exc as sa_exc
import asyncio

# 禁用SQLAlchemy的警告
warnings.filterwarnings('ignore', category=sa_exc.SAWarning)

# 导入数据库模型和会话
from database.models import Base, UsedTOTP, RefreshToken
from database.session import engine, get_db
import database.cmdb_models  # 先导入CMDB模型
import database.category_models  # 再导入设备分类模型
import database.config_management_models  # 导入配置管理模型

# 导入路由
from routes import auth, users, audit, ldap, security, config_management, config_generator_router, config_module
from routes.strix_integration import router as strix_router
from routes.system_global_config import router as system_global_config_router
from routes.frontend_cert_config import router as frontend_cert_config_router
from routes.monitoring_integration import router as monitoring_integration_router
from routes.cmdb import router as cmdb_router
from routes.device import router as device_router, connections, ssh_connections
from routes.job_config_router import router as job_config_router
from app.api import process_management
from app.api.job import router as job_router  # 添加job路由导入

# 导入连接管理器
from utils.device_connection_manager import device_connection_manager

# 导入任务
from tasks import scheduler

# 创建应用
app = FastAPI(title="NetOps API", version="1.0.0")

# 添加中间件来获取真实客户端IP
@app.middleware("http")
async def get_real_ip(request: Request, call_next):
    # 获取真实客户端IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 如果有多个IP，取第一个（最原始的客户端IP）
        request.state.client_ip = forwarded_for.split(",")[0].strip()
    else:
        # 尝试获取X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            request.state.client_ip = real_ip
        else:
            # 如果没有代理头，使用连接IP
            request.state.client_ip = request.client.host
    
    response = await call_next(request)
    return response

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许特定的来源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # 明确指定允许的方法
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["*"],  # 暴露所有响应头
    max_age=3600,  # 预检请求的缓存时间
)

def init_db():
    """初始化数据库，确保所有表都被创建"""
    try:
        # 只创建新表，不删除现有表
        Base.metadata.create_all(bind=engine)
        # Strix 集成表、系统全局配置表、前端证书配置表（导入以注册到 database.base.Base.metadata）
        import database.strix_models  # noqa: F401
        import database.system_global_config_models  # noqa: F401
        import database.frontend_cert_config_models  # noqa: F401
        from database.base import Base as StrixBase
        StrixBase.metadata.create_all(bind=engine, checkfirst=True)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise e

# 初始化数据库
init_db()

# 加载全局时钟时区（系统管理里配置的展示时区，重启后生效）
def _load_global_display_timezone():
    try:
        from database.session import SessionLocal
        from database.system_global_config_models import SystemGlobalConfig
        from utils.datetime_utils import set_display_timezone
        db = SessionLocal()
        row = db.query(SystemGlobalConfig).filter(SystemGlobalConfig.config_key == "GLOBAL_TIMEZONE").first()
        if row and row.config_value:
            set_display_timezone(row.config_value.strip())
        db.close()
    except Exception:
        pass
_load_global_display_timezone()

# 包含路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(ldap.router)
app.include_router(security.router, prefix="/api/security")
app.include_router(cmdb_router, prefix="/api")
app.include_router(device_router)
app.include_router(config_management.router, prefix="/api", tags=["config"])
app.include_router(config_generator_router, prefix="/api/config-generator", tags=["config-generator"])
app.include_router(config_module.router, prefix="/api/config-module")
app.include_router(strix_router, prefix="/api/config-module")
app.include_router(system_global_config_router, prefix="/api")
app.include_router(frontend_cert_config_router, prefix="/api")
app.include_router(job_config_router, prefix="/api")
app.include_router(connections.router)
app.include_router(ssh_connections.router, prefix="/api")
app.include_router(process_management.router, prefix="")
app.include_router(job_router, prefix="/api")  # 添加job路由注册
app.include_router(monitoring_integration_router)  # 监控系统集成 Webhook + 告警

# 定期清理任务
def cleanup_expired_records():
    """清理过期的记录"""
    from sqlalchemy.orm import Session
    from database.session import SessionLocal
    
    db = SessionLocal()
    try:
        # 当前时间
        now = datetime.utcnow().isoformat()
        
        # 清理过期的TOTP记录
        db.query(UsedTOTP).filter(UsedTOTP.expires_at < now).delete()
        
        # 清理过期的刷新令牌
        db.query(RefreshToken).filter(RefreshToken.expires_at < now).delete()
        
        db.commit()
        print(f"Cleanup task completed at {now}")
    except Exception as e:
        print(f"Error in cleanup task: {e}")
    finally:
        db.close()

# 启动定期清理任务
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_expired_records, 'interval', hours=24)  # 每24小时执行一次
scheduler.start()

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    # 初始化数据库
    init_db()
    
    # 启动连接管理器
    await device_connection_manager.start()
    
    # 启动调度器（如果尚未启动）
    try:
        if not scheduler.running:
            scheduler.start()
            print("调度器已启动")
    except Exception as e:
        print(f"启动调度器时出错: {e}")

# 根路由
@app.get("/")
async def root():
    return {"message": "Welcome to NetOps API"}

# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的操作"""
    # 停止连接管理器（stop 为 async，必须 await）
    await device_connection_manager.stop()
    
    # 停止调度器
    scheduler.shutdown()
    print("调度器已停止")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """处理favicon.ico请求，返回204状态码（无内容）"""
    return Response(status_code=204)

if __name__ == "__main__":
    import uvicorn
    # 排除运行时目录，避免 data/、__pycache__ 等变更触发反复 reload（watchfiles 刷屏）
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=[
            "data",
            "data/*",
            "data/**",
            "*/data/*",
            "*/data/**",
            "__pycache__",
            "*/__pycache__/*",
            ".git",
            ".git/*",
            ".venv",
            ".venv/*",
            "*.pyc",
            "*.pyo",
        ],
    ) 