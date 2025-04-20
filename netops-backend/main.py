from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os
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
from routes import auth, users, audit, ldap, security, config_management, config_generator_router
from routes.cmdb import router as cmdb_router
from routes.device import router as device_router, connections, ssh_connections

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
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise e

# 初始化数据库
init_db()

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
app.include_router(connections.router)
app.include_router(ssh_connections.router, prefix="/api")

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
    # 停止连接管理器
    device_connection_manager.stop()
    
    # 停止调度器
    scheduler.shutdown()
    print("调度器已停止")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """处理favicon.ico请求，返回204状态码（无内容）"""
    return Response(status_code=204)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 