# -*- coding: utf-8 -*-
"""CMDB 设备发现接口：POST /cmdb/discovery，按 discovery_type 调度并写入 CMDB。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from database.cmdb_session import get_cmdb_db
from services.discovery import run_discovery, sync_discovered_to_cmdb

router = APIRouter()


class DiscoveryRequest(BaseModel):
    """发现请求体，与前端表单一致。"""
    discovery_type: str = Field(..., description="发现类型：cisco-campus 等")
    ip_range: str = Field(..., description="IP 范围，如 192.168.1.0/24 或 192.168.1.1-254")
    username: str = Field(..., description="SSH 用户名")
    password: str = Field(..., description="SSH 密码")
    enable_password: Optional[str] = Field(None, description="Enable 密码（可选，Cisco 等需提权时必填）")
    port: int = Field(22, description="SSH 端口")
    timeout: int = Field(30, description="单台超时秒数")
    threads: int = Field(5, description="并发数（当前 Cisco 为串行，预留）")


@router.post("/discovery")
def post_discovery(
    body: DiscoveryRequest,
    db: Session = Depends(get_cmdb_db),
):
    """
    执行设备发现并写入 CMDB。
    全部 IP 处理完后返回：成功列表、失败列表及原因，前端据此汇总展示，不因单台失败而报错。
    """
    params = {
        "ip_range": body.ip_range,
        "username": body.username,
        "password": body.password,
        "enable_password": body.enable_password,
        "port": body.port,
        "timeout": body.timeout,
        "threads": body.threads,
    }
    try:
        devices, failed = run_discovery(body.discovery_type, params)
        count = sync_discovered_to_cmdb(db, devices)
        succeeded = [{"ip": d.ip_address, "name": d.name} for d in devices]
        failed_list = [{"ip": ip, "reason": reason} for ip, reason in failed]
        return {
            "success": True,
            "discovered_count": count,
            "succeeded": succeeded,
            "failed": failed_list,
            "message": f"成功 {count} 台，失败 {len(failed_list)} 台",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备发现失败: {e!s}")
