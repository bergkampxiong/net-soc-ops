from fastapi import APIRouter
from .base import router as base_router
from .asset import router as asset_router
from .discovery import router as discovery_router

# 创建CMDB主路由
router = APIRouter(prefix="/cmdb", tags=["CMDB"])

# 包含子路由
router.include_router(base_router)
router.include_router(asset_router)
router.include_router(discovery_router) 