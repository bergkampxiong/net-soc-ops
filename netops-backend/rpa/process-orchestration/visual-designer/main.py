from fastapi import FastAPI
from .routes import router as device_connection_router

app = FastAPI()

# 注册设备连接池管理路由
app.include_router(device_connection_router, prefix="/api/device-connections", tags=["device-connections"]) 