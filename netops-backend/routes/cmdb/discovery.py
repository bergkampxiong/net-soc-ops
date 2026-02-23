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
    """发现请求体，与前端表单一致。网络设备发现用 ip_range；VMware 发现用 vcenter_host（或 ip_range）。"""
    discovery_type: str = Field(..., description="发现类型：cisco-campus、vmware 等")
    ip_range: Optional[str] = Field(None, description="IP 范围，如 192.168.1.0/24；VMware 时可选，可与 vcenter_host 二选一")
    vcenter_host: Optional[str] = Field(None, description="vCenter/ESXi 主机地址，仅 VMware 发现时使用")
    username: str = Field(..., description="SSH / vCenter 用户名")
    password: str = Field(..., description="SSH / vCenter 密码")
    enable_password: Optional[str] = Field(None, description="Enable 密码（可选，Cisco 等设备需提权时填写）")
    port: Optional[int] = Field(None, description="SSH 端口或 vCenter 端口，默认 22（VMware 为 443）")
    timeout: Optional[int] = Field(None, description="单台超时秒数，默认 30")
    threads: Optional[int] = Field(None, description="并发数，默认 5")


@router.post("/discovery")
def post_discovery(
    body: DiscoveryRequest,
    db: Session = Depends(get_cmdb_db),
):
    """
    执行设备发现并写入 CMDB。
    全部 IP 处理完后返回：成功列表、失败列表及原因，前端据此汇总展示，不因单台失败而报错。
    """
    # VMware 使用 vcenter_host（或 ip_range）；其他类型使用 ip_range
    if body.discovery_type == "vmware":
        ip_range_value = (body.vcenter_host or body.ip_range or "").strip()
        if not ip_range_value:
            raise HTTPException(
                status_code=400,
                detail="vCenter/ESXi 主机地址必填（填写 vcenter_host 或 ip_range）",
            )
        port = body.port if body.port is not None else 443
    else:
        ip_range_value = (body.ip_range or "").strip()
        if not ip_range_value:
            raise HTTPException(status_code=400, detail="IP范围必填")
        port = body.port if body.port is not None else 22
    params = {
        "ip_range": ip_range_value,
        "username": body.username,
        "password": body.password,
        "enable_password": body.enable_password,
        "port": port,
        "timeout": body.timeout if body.timeout is not None else 30,
        "threads": body.threads if body.threads is not None else 5,
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
