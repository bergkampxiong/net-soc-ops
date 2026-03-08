# IP 管理模块 API：Aggregates、Prefixes、NetBox 导入、DHCP（PRD-IP管理功能）
# 仅新增路由，不修改 config_module 现有逻辑；挂载前缀 /api/config-module
import ipaddress
import logging
from datetime import datetime
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from database.session import get_db
from database.ipam_models import IpamAggregate, IpamPrefix, DhcpServer, DhcpScope, DhcpLease, NetboxImportConfig, DhcpWmiTarget
from schemas.ipam_schemas import (
    AggregateCreate,
    AggregateUpdate,
    AggregateListResponse,
    PrefixCreate,
    PrefixUpdate,
    PrefixListResponse,
    NetboxConfigBody,
    NetboxImportBody,
    NetboxImportResult,
    DhcpSyncBody,
    ScopeLinkPrefixBody,
    DhcpWmiTargetCreate,
    DhcpWmiTargetUpdate,
    DhcpScopesListResponse,
    DhcpLeasesListResponse,
)
from services.dhcp_wmi_sync import run_dhcp_wmi_sync

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["config-module-ipam"],
    responses={404: {"description": "Not found"}},
)


def _parse_cidr(cidr: str):
    """解析 CIDR，返回 ipaddress.IPv4Network 或 IPv6Network，无效则抛 ValueError。"""
    try:
        return ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效 CIDR: {cidr}")


def _aggregates_overlap(db, prefix_str: str, exclude_id: Optional[int] = None) -> bool:
    """检查 prefix_str 是否与已有 Aggregate 重叠（排除 exclude_id）。"""
    try:
        new_net = ipaddress.ip_network(prefix_str, strict=False)
    except ValueError:
        return True
    q = db.query(IpamAggregate).filter(IpamAggregate.prefix.isnot(None))
    if exclude_id is not None:
        q = q.filter(IpamAggregate.id != exclude_id)
    for agg in q.all():
        if not agg.prefix:
            continue
        try:
            existing = ipaddress.ip_network(agg.prefix, strict=False)
            if new_net.overlaps(existing):
                return True
        except ValueError:
            continue
    return False


# ---------- Aggregates ----------
@router.get("/ipam/aggregates", response_model=AggregateListResponse)
def list_aggregates(
    prefix: Optional[str] = Query(None),
    rir: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    q = db.query(IpamAggregate)
    if prefix:
        q = q.filter(IpamAggregate.prefix.ilike(f"%{prefix}%"))
    if rir:
        q = q.filter(IpamAggregate.rir.ilike(f"%{rir}%"))
    if description:
        q = q.filter(IpamAggregate.description.ilike(f"%{description}%"))
    total = q.count()
    rows = q.order_by(IpamAggregate.prefix).offset(skip).limit(limit).all()
    return AggregateListResponse(items=[r.to_dict() for r in rows], total=total)


@router.post("/ipam/aggregates")
def create_aggregate(body: AggregateCreate, db=Depends(get_db)):
    _parse_cidr(body.prefix)
    if _aggregates_overlap(db, body.prefix):
        raise HTTPException(status_code=400, detail="该 CIDR 与已有 Aggregate 重叠")
    date_added = None
    if body.date_added:
        try:
            date_added = datetime.strptime(body.date_added, "%Y-%m-%d").date()
        except ValueError:
            pass
    agg = IpamAggregate(
        prefix=body.prefix.strip(),
        rir=body.rir.strip() if body.rir else None,
        date_added=date_added,
        description=body.description.strip() if body.description else None,
    )
    db.add(agg)
    db.commit()
    db.refresh(agg)
    return agg.to_dict()


@router.get("/ipam/aggregates/{agg_id}")
def get_aggregate(agg_id: int, db=Depends(get_db)):
    agg = db.query(IpamAggregate).filter(IpamAggregate.id == agg_id).first()
    if not agg:
        raise HTTPException(status_code=404, detail="Aggregate 不存在")
    return agg.to_dict()


@router.put("/ipam/aggregates/{agg_id}")
def update_aggregate(agg_id: int, body: AggregateUpdate, db=Depends(get_db)):
    agg = db.query(IpamAggregate).filter(IpamAggregate.id == agg_id).first()
    if not agg:
        raise HTTPException(status_code=404, detail="Aggregate 不存在")
    if body.prefix is not None:
        _parse_cidr(body.prefix)
        if _aggregates_overlap(db, body.prefix, exclude_id=agg_id):
            raise HTTPException(status_code=400, detail="该 CIDR 与已有 Aggregate 重叠")
        agg.prefix = body.prefix.strip()
    if body.rir is not None:
        agg.rir = body.rir.strip() if body.rir else None
    if body.date_added is not None:
        try:
            agg.date_added = datetime.strptime(body.date_added, "%Y-%m-%d").date()
        except ValueError:
            pass
    if body.description is not None:
        agg.description = body.description.strip() if body.description else None
    db.commit()
    db.refresh(agg)
    return agg.to_dict()


@router.delete("/ipam/aggregates/{agg_id}")
def delete_aggregate(agg_id: int, db=Depends(get_db)):
    agg = db.query(IpamAggregate).filter(IpamAggregate.id == agg_id).first()
    if not agg:
        raise HTTPException(status_code=404, detail="Aggregate 不存在")
    db.delete(agg)
    db.commit()
    return {"message": "已删除"}


# ---------- Prefixes ----------
@router.get("/ipam/prefixes", response_model=PrefixListResponse)
def list_prefixes(
    prefix: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    vlan_id: Optional[int] = Query(None),
    aggregate_id: Optional[int] = Query(None),
    location: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    q = db.query(IpamPrefix)
    if prefix:
        q = q.filter(IpamPrefix.prefix.ilike(f"%{prefix}%"))
    if status:
        q = q.filter(IpamPrefix.status == status)
    if vlan_id is not None:
        q = q.filter(IpamPrefix.vlan_id == vlan_id)
    if aggregate_id is not None:
        q = q.filter(IpamPrefix.aggregate_id == aggregate_id)
    if location:
        q = q.filter(IpamPrefix.location.ilike(f"%{location}%"))
    total = q.count()
    rows = q.order_by(IpamPrefix.prefix).offset(skip).limit(limit).all()
    return PrefixListResponse(items=[r.to_dict() for r in rows], total=total)


@router.post("/ipam/prefixes")
def create_prefix(body: PrefixCreate, db=Depends(get_db)):
    _parse_cidr(body.prefix)
    p = IpamPrefix(
        prefix=body.prefix.strip(),
        status=body.status.strip(),
        description=body.description.strip() if body.description else None,
        is_pool=body.is_pool,
        mark_utilized=body.mark_utilized,
        vlan_id=body.vlan_id,
        location=body.location.strip() if body.location else None,
        aggregate_id=body.aggregate_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.get("/ipam/prefixes/{pref_id}")
def get_prefix(pref_id: int, db=Depends(get_db)):
    p = db.query(IpamPrefix).filter(IpamPrefix.id == pref_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Prefix 不存在")
    d = p.to_dict()
    # 关联的 DHCP Scope
    scopes = db.query(DhcpScope).filter(DhcpScope.prefix_id == pref_id).all()
    d["linked_dhcp_scopes"] = [s.to_dict() for s in scopes]
    return d


@router.put("/ipam/prefixes/{pref_id}")
def update_prefix(pref_id: int, body: PrefixUpdate, db=Depends(get_db)):
    p = db.query(IpamPrefix).filter(IpamPrefix.id == pref_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Prefix 不存在")
    if body.prefix is not None:
        _parse_cidr(body.prefix)
        p.prefix = body.prefix.strip()
    if body.status is not None:
        p.status = body.status.strip()
    if body.description is not None:
        p.description = body.description.strip() if body.description else None
    if body.is_pool is not None:
        p.is_pool = body.is_pool
    if body.mark_utilized is not None:
        p.mark_utilized = body.mark_utilized
    if body.vlan_id is not None:
        p.vlan_id = body.vlan_id
    if body.location is not None:
        p.location = body.location.strip() if body.location else None
    if body.aggregate_id is not None:
        p.aggregate_id = body.aggregate_id
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.delete("/ipam/prefixes/{pref_id}")
def delete_prefix(pref_id: int, db=Depends(get_db)):
    p = db.query(IpamPrefix).filter(IpamPrefix.id == pref_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Prefix 不存在")
    db.delete(p)
    db.commit()
    return {"message": "已删除"}


# ---------- NetBox 配置 ----------
@router.get("/import/netbox-config")
def get_netbox_config(db=Depends(get_db)):
    row = db.query(NetboxImportConfig).first()
    if not row:
        return {"base_url": "", "api_token": None}
    return {"base_url": row.base_url, "api_token": "***" if row.api_token else None}


@router.post("/import/netbox-config")
def save_netbox_config(body: NetboxConfigBody, db=Depends(get_db)):
    row = db.query(NetboxImportConfig).first()
    if not row:
        row = NetboxImportConfig(base_url=body.base_url.strip(), api_token=body.api_token.strip() if body.api_token else None)
        db.add(row)
    else:
        row.base_url = body.base_url.strip()
        if body.api_token is not None:
            row.api_token = body.api_token.strip() if body.api_token else None
    db.commit()
    db.refresh(row)
    return {"message": "已保存", "base_url": row.base_url}


# ---------- NetBox 导入 ----------
def _fetch_netbox_aggregates(base_url: str, token: str):
    url = base_url.rstrip("/") + "/api/ipam/aggregates/"
    headers = {"Authorization": f"Token {token}"} if token else {}
    results = []
    while url:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        url = data.get("next")
    return results


def _fetch_netbox_prefixes(base_url: str, token: str):
    url = base_url.rstrip("/") + "/api/ipam/prefixes/"
    headers = {"Authorization": f"Token {token}"} if token else {}
    results = []
    while url:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        url = data.get("next")
    return results


@router.post("/import/netbox", response_model=NetboxImportResult)
def import_from_netbox(body: NetboxImportBody, db=Depends(get_db)):
    cfg = db.query(NetboxImportConfig).first()
    if not cfg or not cfg.base_url:
        raise HTTPException(status_code=400, detail="请先配置 NetBox 基础 URL 与 Token")
    token = (cfg.api_token or "").strip()
    base_url = cfg.base_url.rstrip("/")
    strategy = (body.strategy or "merge").lower()
    if strategy not in ("merge", "replace"):
        strategy = "merge"

    agg_created = agg_updated = 0
    pref_created = pref_updated = 0
    try:
        raw_aggregates = _fetch_netbox_aggregates(base_url, token)
    except Exception as e:
        logger.exception("NetBox aggregates 拉取失败")
        raise HTTPException(status_code=502, detail=f"NetBox 拉取失败: {str(e)}")
    try:
        raw_prefixes = _fetch_netbox_prefixes(base_url, token)
    except Exception as e:
        logger.exception("NetBox prefixes 拉取失败")
        raise HTTPException(status_code=502, detail=f"NetBox 拉取失败: {str(e)}")

    if strategy == "replace":
        db.query(IpamPrefix).filter(IpamPrefix.aggregate_id.isnot(None)).update({IpamPrefix.aggregate_id: None})
        db.query(IpamAggregate).delete()
        db.commit()

    for item in raw_aggregates:
        nb_prefix = item.get("prefix")
        if not nb_prefix:
            continue
        rir = (item.get("rir") or {}).get("name") if isinstance(item.get("rir"), dict) else None
        date_added = item.get("date_added")
        if date_added and isinstance(date_added, str):
            try:
                date_added = datetime.strptime(date_added[:10], "%Y-%m-%d").date()
            except ValueError:
                date_added = None
        desc = item.get("description") or ""
        existing = db.query(IpamAggregate).filter(IpamAggregate.prefix == nb_prefix).first()
        if existing:
            existing.rir = rir
            existing.date_added = date_added
            existing.description = desc
            agg_updated += 1
        else:
            db.add(IpamAggregate(prefix=nb_prefix, rir=rir, date_added=date_added, description=desc))
            agg_created += 1
    db.commit()

    # 构建 aggregate prefix -> id
    agg_by_prefix = {a.prefix: a.id for a in db.query(IpamAggregate).all()}

    for item in raw_prefixes:
        nb_prefix = item.get("prefix")
        if not nb_prefix:
            continue
        status = (item.get("status") or {}).get("value") if isinstance(item.get("status"), dict) else "active"
        if status not in ("active", "reserved", "deprecated", "container"):
            status = "active"
        desc = item.get("description") or ""
        vlan_id = None
        if item.get("vlan") and isinstance(item["vlan"], dict):
            vlan_id = item["vlan"].get("vid")
        loc = None
        if item.get("site") and isinstance(item["site"], dict):
            loc = item["site"].get("name")
        aggregate_id = None
        for agg_prefix, agg_id in agg_by_prefix.items():
            try:
                if ipaddress.ip_network(nb_prefix, strict=False).subnet_of(ipaddress.ip_network(agg_prefix, strict=False)):
                    aggregate_id = agg_id
                    break
            except ValueError:
                continue
        existing = db.query(IpamPrefix).filter(IpamPrefix.prefix == nb_prefix).first()
        if existing:
            existing.status = status
            existing.description = desc
            existing.vlan_id = vlan_id
            existing.location = loc
            existing.aggregate_id = aggregate_id
            pref_updated += 1
        else:
            db.add(IpamPrefix(
                prefix=nb_prefix,
                status=status,
                description=desc,
                vlan_id=vlan_id,
                location=loc,
                aggregate_id=aggregate_id,
            ))
            pref_created += 1
    db.commit()

    return NetboxImportResult(
        aggregates_created=agg_created,
        aggregates_updated=agg_updated,
        prefixes_created=pref_created,
        prefixes_updated=pref_updated,
        message="导入完成",
    )


# ---------- DHCP WMI 采集目标 ----------
@router.get("/dhcp/wmi-targets")
def list_dhcp_wmi_targets(db=Depends(get_db)):
    """返回已配置的 WMI 采集目标列表（密码脱敏）。"""
    rows = db.query(DhcpWmiTarget).order_by(DhcpWmiTarget.id).all()
    return {"items": [r.to_dict(mask_password=True) for r in rows], "total": len(rows)}


@router.post("/dhcp/wmi-targets")
def create_dhcp_wmi_target(body: DhcpWmiTargetCreate, db=Depends(get_db)):
    """新增一条 WMI 采集目标。"""
    t = DhcpWmiTarget(
        name=body.name,
        host=body.host.strip(),
        port=body.port if body.port is not None else 5985,
        username=body.username,
        password=body.password,
        use_ssl=body.use_ssl or False,
        enabled=body.enabled if body.enabled is not None else True,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t.to_dict(mask_password=True)


@router.put("/dhcp/wmi-targets/{target_id}")
def update_dhcp_wmi_target(target_id: int, body: DhcpWmiTargetUpdate, db=Depends(get_db)):
    t = db.query(DhcpWmiTarget).filter(DhcpWmiTarget.id == target_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="采集目标不存在")
    if body.name is not None:
        t.name = body.name
    if body.host is not None:
        t.host = body.host.strip()
    if body.port is not None:
        t.port = body.port
    if body.username is not None:
        t.username = body.username
    if body.password is not None:
        t.password = body.password
    if body.use_ssl is not None:
        t.use_ssl = body.use_ssl
    if body.enabled is not None:
        t.enabled = body.enabled
    db.commit()
    db.refresh(t)
    return t.to_dict(mask_password=True)


@router.delete("/dhcp/wmi-targets/{target_id}")
def delete_dhcp_wmi_target(target_id: int, db=Depends(get_db)):
    t = db.query(DhcpWmiTarget).filter(DhcpWmiTarget.id == target_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="采集目标不存在")
    db.delete(t)
    db.commit()
    return {"message": "已删除"}


@router.post("/dhcp/sync-from-wmi")
def sync_dhcp_from_wmi(target_id: Optional[int] = Query(None, description="指定则仅同步该目标，否则同步所有启用目标"), db=Depends(get_db)):
    """使用已配置的 Windows 凭证通过 WinRM 拉取 DHCP 数据并写入本地表。"""
    result = run_dhcp_wmi_sync(db, target_id=target_id)
    return result


# ---------- DHCP Servers ----------
@router.get("/dhcp/servers")
def list_dhcp_servers(
    location: Optional[str] = Query(None),
    server_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    vlan_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    q = db.query(DhcpServer)
    if location:
        q = q.filter(DhcpServer.location.ilike(f"%{location}%"))
    if server_type:
        q = q.filter(DhcpServer.type == server_type)
    if status:
        q = q.filter(DhcpServer.status == status)
    if vlan_id is not None:
        q = q.filter(DhcpServer.vlan_id == vlan_id)
    total = q.count()
    rows = q.order_by(DhcpServer.name).offset(skip).limit(limit).all()
    return {"items": [r.to_dict() for r in rows], "total": total}


@router.get("/dhcp/servers/{server_id}/scopes", response_model=DhcpScopesListResponse)
def list_dhcp_scopes(server_id: int, db=Depends(get_db)):
    q = db.query(DhcpScope).filter(DhcpScope.dhcp_server_id == server_id)
    rows = q.order_by(DhcpScope.name).all()
    server = db.query(DhcpServer).filter(DhcpServer.id == server_id).first()
    server_name = server.name if server else None
    items = []
    for r in rows:
        d = r.to_dict()
        d["server_name"] = server_name
        items.append(d)
    return DhcpScopesListResponse(items=items, total=len(items))


@router.get("/dhcp/scopes/{scope_id}")
def get_dhcp_scope(scope_id: int, db=Depends(get_db)):
    scope = db.query(DhcpScope).filter(DhcpScope.id == scope_id).first()
    if not scope:
        raise HTTPException(status_code=404, detail="Scope 不存在")
    d = scope.to_dict()
    server = db.query(DhcpServer).filter(DhcpServer.id == scope.dhcp_server_id).first()
    d["server_name"] = server.name if server else None
    if scope.prefix_id:
        pref = db.query(IpamPrefix).filter(IpamPrefix.id == scope.prefix_id).first()
        d["prefix"] = pref.to_dict() if pref else None
    else:
        d["prefix"] = None
    return d


@router.post("/dhcp/scopes/{scope_id}/link-prefix")
def link_scope_to_prefix(scope_id: int, body: ScopeLinkPrefixBody, db=Depends(get_db)):
    scope = db.query(DhcpScope).filter(DhcpScope.id == scope_id).first()
    if not scope:
        raise HTTPException(status_code=404, detail="Scope 不存在")
    scope.prefix_id = body.prefix_id
    db.commit()
    db.refresh(scope)
    return scope.to_dict()


@router.get("/dhcp/scopes/{scope_id}/ips", response_model=DhcpLeasesListResponse)
def list_dhcp_scope_ips(
    scope_id: int,
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    q = db.query(DhcpLease).filter(DhcpLease.scope_id == scope_id)
    if status:
        q = q.filter(DhcpLease.status == status)
    total = q.count()
    rows = q.order_by(DhcpLease.ip_address).offset(skip).limit(limit).all()
    return DhcpLeasesListResponse(items=[r.to_dict() for r in rows], total=total)


@router.post("/dhcp/sync")
def dhcp_sync(body: Optional[DhcpSyncBody] = None, db=Depends(get_db)):
    """从 Agent 或手动上报同步 DHCP 数据；无 body 时仅返回提示。"""
    if not body or (not body.servers and not body.scopes and not body.leases):
        return {"message": "未提交数据。WMI 同步需由 Agent 或外部脚本调用本接口并提交 servers/scopes/leases。"}
    created = 0
    if body.servers:
        for s in body.servers:
            db.add(DhcpServer(
                name=s.name,
                type=s.type,
                ip_address=s.ip_address,
                failover_status=s.failover_status,
                location=s.location,
                vlan_id=s.vlan_id,
                num_scopes=s.num_scopes,
                total_ips=s.total_ips,
                used_ips=s.used_ips,
                available_ips=s.available_ips,
                status=s.status,
            ))
            created += 1
    if body.scopes:
        for sc in body.scopes:
            server_id = sc.dhcp_server_id
            if not server_id and sc.server_name:
                svr = db.query(DhcpServer).filter(DhcpServer.name == sc.server_name).first()
                server_id = svr.id if svr else None
            if server_id:
                db.add(DhcpScope(
                    dhcp_server_id=server_id,
                    name=sc.name,
                    network_address=sc.network_address,
                    mask_cidr=sc.mask_cidr,
                    failover_mode=sc.failover_mode,
                    enabled=sc.enabled,
                    location=sc.location,
                    vlan_id=sc.vlan_id,
                    total_ips=sc.total_ips,
                    used_ips=sc.used_ips,
                    available_ips=sc.available_ips,
                ))
                created += 1
    if body.leases:
        for le in body.leases:
            if le.scope_id:
                db.add(DhcpLease(
                    scope_id=le.scope_id,
                    ip_address=le.ip_address,
                    mac=le.mac,
                    client_name=le.client_name,
                    is_reservation=le.is_reservation or False,
                    response_time=le.response_time,
                    status=le.status,
                ))
                created += 1
    db.commit()
    return {"message": "同步完成", "created": created}
