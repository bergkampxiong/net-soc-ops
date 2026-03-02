# 系统全局配置 API：供 netops 全局功能使用（如统一渗透测试报告 LLM 中文化）
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.system_global_config_models import SystemGlobalConfig

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/system",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)

# 前端脱敏占位符，PUT 带此值表示未修改、不覆盖
_SENSITIVE_PLACEHOLDER = "********"

# 全局配置键：LLM（证书配置已迁移至 frontend_cert_config 表）
GLOBAL_CONFIG_KEYS = ("GLOBAL_LLM_MODEL", "GLOBAL_LLM_API_KEY", "GLOBAL_LLM_API_BASE")


class GlobalConfigItem(BaseModel):
    config_key: str
    config_value: Optional[str] = None
    updated_at: Optional[str] = None


class GlobalConfigUpdate(BaseModel):
    GLOBAL_LLM_MODEL: Optional[str] = None
    GLOBAL_LLM_API_KEY: Optional[str] = None
    GLOBAL_LLM_API_BASE: Optional[str] = None


@router.get("/global-config", response_model=List[dict])
def get_global_config(db: Session = Depends(get_db)):
    """获取系统全局配置，敏感字段脱敏。"""
    rows = db.query(SystemGlobalConfig).filter(
        SystemGlobalConfig.config_key.in_(GLOBAL_CONFIG_KEYS)
    ).all()
    return [r.to_dict(mask_sensitive=True) for r in rows]


@router.put("/global-config")
def update_global_config(body: GlobalConfigUpdate, db: Session = Depends(get_db)):
    """更新系统全局配置（如 OPENAI_API_KEY）。敏感键为脱敏占位符时不覆盖。"""
    key_values = body.dict(exclude_none=True)
    for k, v in key_values.items():
        if v is None:
            continue
        if k not in GLOBAL_CONFIG_KEYS:
            continue
        if "key" in k.lower() and (v == _SENSITIVE_PLACEHOLDER or (v and v.strip() == "")):
            continue
        row = db.query(SystemGlobalConfig).filter(SystemGlobalConfig.config_key == k).first()
        if row:
            row.config_value = v
        else:
            db.add(SystemGlobalConfig(config_key=k, config_value=v))
    db.commit()
    return {"ok": True}


def get_global_config_kv(db: Session) -> dict:
    """供其他模块调用：读取全局配置键值对，不脱敏（仅后端使用）。"""
    rows = db.query(SystemGlobalConfig).filter(
        SystemGlobalConfig.config_key.in_(GLOBAL_CONFIG_KEYS)
    ).all()
    return {r.config_key: r.config_value for r in rows if r.config_value}
