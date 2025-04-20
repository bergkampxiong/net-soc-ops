from fastapi import APIRouter
from routes.device.category import router as category_router
from routes.device.credential import router as credential_router
from routes.device.connections import router as connections_router
from .pool_config import router as pool_config_router

router = APIRouter()

# 包含子路由
router.include_router(category_router)
router.include_router(credential_router)
router.include_router(connections_router)
router.include_router(pool_config_router, prefix="/connections/pools", tags=["pool-config"]) 