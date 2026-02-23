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
    """发现请求体，与前端表单一致。网络设备用 ip_range/username/password；VMware 用 vcenter_host；AWS 用 access_key/secret_key/region。"""
    discovery_type: str = Field(..., description="发现类型：cisco-campus、vmware、aws 等")
    ip_range: Optional[str] = Field(None, description="IP 范围；VMware 时可选")
    vcenter_host: Optional[str] = Field(None, description="vCenter/ESXi 主机地址，仅 VMware 发现时使用")
    username: Optional[str] = Field(None, description="SSH / vCenter 用户名")
    password: Optional[str] = Field(None, description="SSH / vCenter 密码")
    enable_password: Optional[str] = Field(None, description="Enable 密码（可选）")
    port: Optional[int] = Field(None, description="SSH 端口或 vCenter 端口")
    timeout: Optional[int] = Field(None, description="单台超时秒数，默认 30")
    threads: Optional[int] = Field(None, description="并发数，默认 5")
    # AWS / 阿里云 发现
    access_key: Optional[str] = Field(None, description="Access Key（AWS 或阿里云）")
    secret_key: Optional[str] = Field(None, description="Secret Key（AWS 或阿里云）")
    region: Optional[str] = Field(None, description="区域（AWS 或阿里云）")


@router.post("/discovery")
def post_discovery(
    body: DiscoveryRequest,
    db: Session = Depends(get_cmdb_db),
):
    """
    执行设备发现并写入 CMDB。
    全部 IP 处理完后返回：成功列表、失败列表及原因，前端据此汇总展示，不因单台失败而报错。
    """
    # 按发现类型解析参数
    if body.discovery_type == "aws":
        access_key = (body.access_key or "").strip()
        secret_key = (body.secret_key or "").strip()
        region = (body.region or "").strip()
        if not access_key or not secret_key or not region:
            raise HTTPException(
                status_code=400,
                detail="AWS 发现请填写 Access Key、Secret Key 和区域",
            )
        params = {
            "ip_range": "",
            "username": "",
            "password": "",
            "access_key": access_key,
            "secret_key": secret_key,
            "region": region,
            "timeout": body.timeout if body.timeout is not None else 30,
            "threads": body.threads if body.threads is not None else 5,
        }
    elif body.discovery_type == "aliyun":
        access_key = (body.access_key or "").strip()
        secret_key = (body.secret_key or "").strip()
        region = (body.region or "").strip()
        if not access_key or not secret_key or not region:
            raise HTTPException(
                status_code=400,
                detail="阿里云发现请填写 Access Key、Secret Key 和区域",
            )
        params = {
            "ip_range": "",
            "username": "",
            "password": "",
            "access_key": access_key,
            "secret_key": secret_key,
            "region": region,
            "timeout": body.timeout if body.timeout is not None else 30,
            "threads": body.threads if body.threads is not None else 5,
        }
    elif body.discovery_type == "vmware":
        ip_range_value = (body.vcenter_host or body.ip_range or "").strip()
        if not ip_range_value:
            raise HTTPException(
                status_code=400,
                detail="vCenter/ESXi 主机地址必填（填写 vcenter_host 或 ip_range）",
            )
        port = body.port if body.port is not None else 443
        params = {
            "ip_range": ip_range_value,
            "username": body.username or "",
            "password": body.password or "",
            "enable_password": body.enable_password,
            "port": port,
            "timeout": body.timeout if body.timeout is not None else 30,
            "threads": body.threads if body.threads is not None else 5,
        }
    else:
        ip_range_value = (body.ip_range or "").strip()
        if not ip_range_value:
            raise HTTPException(status_code=400, detail="IP范围必填")
        if not (body.username or "").strip() or not (body.password or "").strip():
            raise HTTPException(status_code=400, detail="用户名和密码必填")
        port = body.port if body.port is not None else 22
        params = {
            "ip_range": ip_range_value,
            "username": (body.username or "").strip(),
            "password": (body.password or "").strip(),
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
