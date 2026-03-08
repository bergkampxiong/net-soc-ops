# IP 管理模块 API：Aggregates、Prefixes、NetBox 导入、DHCP（PRD-IP管理功能）
# 挂载前缀 /api/config-module
import ipaddress
import logging
from datetime import datetime, date
from typing import Optional, List

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from database.session import get_db
from database.ipam_models import (
    IpamAggregate,
    IpamPrefix,
    DhcpServer,
    DhcpScope,
    DhcpLease,
    NetboxImportConfig,
    DhcpWmiTarget,
)
from database.category_models import Credential, CredentialType
from schemas.ipam_schemas import (
    AggregateCreate,
    AggregateUpdate,
    AggregateListResponse,
    AvailableRangesResponse,
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


def _prefix_in_aggregate(db, prefix_str: str, aggregate_id: Optional[int]) -> None:
    """若提供了 aggregate_id，校验 prefix 的 CIDR 完全落在该 Aggregate 范围内，否则抛 HTTPException。"""
    if aggregate_id is None:
        return
    agg = db.query(IpamAggregate).filter(IpamAggregate.id == aggregate_id).first()
    if not agg or not agg.prefix:
        raise HTTPException(status_code=400, detail="所选 Aggregate 不存在或无效")
    try:
        prefix_net = ipaddress.ip_network(prefix_str, strict=False)
        agg_net = ipaddress.ip_network(agg.prefix, strict=False)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效 CIDR")
    if not prefix_net.subnet_of(agg_net):
        raise HTTPException(status_code=400, detail="Prefix 不在所选 Aggregate 范围内")


def _address_range_to_cidrs(start: ipaddress.IPv4Address, end: ipaddress.IPv4Address) -> List[str]:
    """将 [start, end] 覆盖为最简 CIDR 列表（仅 IPv4）。"""
    if start > end:
        return []
    out = []
    addr = int(start)
    end_int = int(end)
    while addr <= end_int:
        remaining = end_int - addr + 1
        size = 1
        while size * 2 <= remaining and (addr % (size * 2)) == 0:
            size *= 2
        prefix_len = 33 - size.bit_length()
        net = ipaddress.ip_network(f"{ipaddress.IPv4Address(addr)}/{prefix_len}", strict=False)
        out.append(str(net))
        addr += size
    return out


def _aggregate_available_ranges(db, agg: IpamAggregate) -> List[str]:
    """计算该 Aggregate 下未被任何 Prefix 覆盖的 IPv4 区间，返回 CIDR 字符串列表。"""
    try:
        agg_net = ipaddress.ip_network(agg.prefix or "", strict=False)
    except ValueError:
        return []
    if agg_net.version != 4:
        return []
    prefixes = db.query(IpamPrefix).filter(IpamPrefix.aggregate_id == agg.id).all()
    subnets = []
    for p in prefixes:
        if not p.prefix:
            continue
        try:
            n = ipaddress.ip_network(p.prefix, strict=False)
            if n.version == 4 and n.subnet_of(agg_net):
                subnets.append(n)
        except ValueError:
            continue
    subnets.sort(key=lambda x: (x.network_address, x.num_addresses))
    gaps = []
    low = agg_net.network_address
    for s in subnets:
        if low < s.network_address:
            gaps.append((low, ipaddress.IPv4Address(int(s.network_address) - 1)))
        low = ipaddress.IPv4Address(int(s.broadcast_address) + 1)
        if low > agg_net.broadcast_address:
            break
    if low <= agg_net.broadcast_address:
        gaps.append((low, agg_net.broadcast_address))
    result = []
    for a, b in gaps:
        result.extend(_address_range_to_cidrs(a, b))
    return result


def _aggregate_utilization(db, agg: IpamAggregate) -> tuple:
    """计算该 Aggregate 下的 prefix 数量与利用率。返回 (prefix_count, utilization_pct)。IPv6 暂返回 (count, 0.0)。"""
    prefixes = db.query(IpamPrefix).filter(IpamPrefix.aggregate_id == agg.id).all()
    prefix_count = len(prefixes)
    try:
        agg_net = ipaddress.ip_network(agg.prefix or "", strict=False)
    except ValueError:
        return prefix_count, 0.0
    if agg_net.version != 4:
        return prefix_count, 0.0
    total = agg_net.num_addresses
    if total == 0:
        return prefix_count, 0.0
    used = 0
    for p in prefixes:
        if not p.prefix:
            continue
        try:
            p_net = ipaddress.ip_network(p.prefix, strict=False)
            if p_net.version == 4:
                used += p_net.num_addresses
        except ValueError:
            continue
    utilization_pct = min(100.0, round(used / total * 100, 1))
    return prefix_count, utilization_pct


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
    items = []
    for r in rows:
        d = r.to_dict()
        cnt, pct = _aggregate_utilization(db, r)
        d["prefix_count"] = cnt
        d["utilization_pct"] = pct
        items.append(d)
    return AggregateListResponse(items=items, total=total)


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
    d = agg.to_dict()
    cnt, pct = _aggregate_utilization(db, agg)
    d["prefix_count"] = cnt
    d["utilization_pct"] = pct
    return d


@router.get("/ipam/aggregates/{agg_id}/available-ranges", response_model=AvailableRangesResponse)
def get_aggregate_available_ranges(agg_id: int, db=Depends(get_db)):
    """返回该 Aggregate 下未被任何 Prefix 占用的 IPv4 CIDR 列表。"""
    agg = db.query(IpamAggregate).filter(IpamAggregate.id == agg_id).first()
    if not agg:
        raise HTTPException(status_code=404, detail="Aggregate 不存在")
    items = _aggregate_available_ranges(db, agg)
    return AvailableRangesResponse(items=items)


@router.get("/ipam/aggregates/{agg_id}")
def get_aggregate(agg_id: int, db=Depends(get_db)):
    agg = db.query(IpamAggregate).filter(IpamAggregate.id == agg_id).first()
    if not agg:
        raise HTTPException(status_code=404, detail="Aggregate 不存在")
    d = agg.to_dict()
    cnt, pct = _aggregate_utilization(db, agg)
    d["prefix_count"] = cnt
    d["utilization_pct"] = pct
    return d


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
    d = agg.to_dict()
    cnt, pct = _aggregate_utilization(db, agg)
    d["prefix_count"] = cnt
    d["utilization_pct"] = pct
    return d


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
    _prefix_in_aggregate(db, body.prefix.strip(), body.aggregate_id)
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
    agg_id = body.aggregate_id if body.aggregate_id is not None else p.aggregate_id
    if body.prefix is not None or body.aggregate_id is not None:
        _prefix_in_aggregate(db, p.prefix, agg_id)
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


# ---------- NetBox 配置与导入 ----------
@router.get("/import/netbox-config")
def get_netbox_config(db=Depends(get_db)):
    """返回 NetBox 配置，仅含 base_url 与 api_credential_id，不含 api_token。"""
    row = db.query(NetboxImportConfig).first()
    if not row:
        return {"data": {"base_url": "", "api_credential_id": None}}
    return {"data": {"base_url": row.base_url, "api_credential_id": row.api_credential_id}}


@router.post("/import/netbox-config")
def save_netbox_config(body: NetboxConfigBody, db=Depends(get_db)):
    """仅接收并持久化 base_url、api_credential_id，不再接收或更新 api_token。"""
    row = db.query(NetboxImportConfig).first()
    if not row:
        row = NetboxImportConfig(base_url=body.base_url.strip(), api_credential_id=body.api_credential_id)
        db.add(row)
    else:
        row.base_url = body.base_url.strip()
        row.api_credential_id = body.api_credential_id
    db.commit()
    db.refresh(row)
    return {"data": {"base_url": row.base_url, "api_credential_id": row.api_credential_id}}


def _netbox_rir_to_str(rir) -> Optional[str]:
    """将 NetBox 返回的 rir（可能为对象 dict）转为可写入 VARCHAR 的字符串。"""
    if rir is None:
        return None
    if isinstance(rir, str):
        return rir.strip() or None
    if isinstance(rir, dict):
        return (rir.get("name") or rir.get("display") or rir.get("slug") or "").strip() or None
    return str(rir)[:128] if rir else None


def _netbox_date_to_date(value) -> Optional[date]:
    """将 NetBox 返回的 date_added（字符串或 None）转为 date 或 None。"""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if hasattr(value, "date") and callable(getattr(value, "date")):
        return value.date()
    s = str(value).strip() if value else ""
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _netbox_scope_to_str(scope) -> Optional[str]:
    """将 NetBox prefix 的 scope/location 对象转为字符串，用于 location 列。"""
    if scope is None:
        return None
    if isinstance(scope, str):
        return scope.strip()[:256] or None
    if isinstance(scope, dict):
        return (scope.get("display") or scope.get("name") or str(scope))[:256].strip() or None
    return str(scope)[:256] if scope else None


def _resolve_aggregate_id_for_prefix(db, prefix_str: str):
    """根据 prefix 所属网段解析出本库中应关联的 aggregate_id（取包含该 prefix 的最小子网 aggregate）。"""
    try:
        prefix_net = ipaddress.ip_network(prefix_str, strict=False)
    except ValueError:
        return None
    candidates = db.query(IpamAggregate).filter(IpamAggregate.prefix.isnot(None)).all()
    best = None
    best_net = None
    for agg in candidates:
        if not agg.prefix:
            continue
        try:
            agg_net = ipaddress.ip_network(agg.prefix, strict=False)
        except ValueError:
            continue
        if prefix_net.subnet_of(agg_net):
            if best_net is None or agg_net.num_addresses < best_net.num_addresses:
                best = agg.id
                best_net = agg_net
    return best


def _fetch_netbox_paginated(base_url: str, token: str, path: str) -> List[dict]:
    """请求 NetBox 列表接口并跟随 next 分页拉取全部结果（默认每页 50 条）。"""
    url = base_url.rstrip("/") + path
    headers = {"Authorization": f"Token {token}"} if token else {}
    all_results: List[dict] = []
    while url:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            break
        page = data.get("results")
        if isinstance(page, list):
            all_results.extend(page)
        url = data.get("next")  # 下一页完整 URL，无则 None
    return all_results


def _fetch_netbox_aggregates(base_url: str, token: str) -> List[dict]:
    return _fetch_netbox_paginated(base_url, token, "/api/ipam/aggregates/")


def _fetch_netbox_prefixes(base_url: str, token: str) -> List[dict]:
    return _fetch_netbox_paginated(base_url, token, "/api/ipam/prefixes/")


@router.post("/import/netbox", response_model=NetboxImportResult)
def netbox_import(body: NetboxImportBody, db=Depends(get_db)):
    cfg = db.query(NetboxImportConfig).first()
    if not cfg or not cfg.base_url:
        raise HTTPException(status_code=400, detail="请先配置 NetBox 地址")
    token = cfg.api_token or ""
    if cfg.api_credential_id:
        cred = db.query(Credential).filter(Credential.id == cfg.api_credential_id, Credential.credential_type == CredentialType.API_KEY).first()
        if cred and getattr(cred, "api_secret", None):
            token = cred.api_secret or token
    if not token:
        raise HTTPException(status_code=400, detail="请先选择 API 凭证")
    try:
        raw_aggs = _fetch_netbox_aggregates(cfg.base_url, token)
        raw_prefixes = _fetch_netbox_prefixes(cfg.base_url, token)
    except Exception as e:
        logger.exception("NetBox 拉取失败")
        raise HTTPException(status_code=502, detail="NetBox 拉取失败: " + str(e))
    agg_created = agg_updated = pref_created = pref_updated = 0
    for a in raw_aggs:
        p = (a.get("prefix") or "").strip()
        if not p:
            continue
        try:
            ipaddress.ip_network(p, strict=False)
        except ValueError:
            continue
        existing = db.query(IpamAggregate).filter(IpamAggregate.prefix == p).first()
        rir_str = _netbox_rir_to_str(a.get("rir"))
        desc = a.get("description")
        if desc is not None and isinstance(desc, dict):
            desc = (desc.get("name") or desc.get("display") or str(desc)).strip() or None
        elif desc is not None:
            desc = (str(desc).strip() or None)
        date_added = _netbox_date_to_date(a.get("date_added"))
        if existing:
            existing.rir = rir_str or existing.rir
            existing.description = desc or existing.description
            if date_added is not None:
                existing.date_added = date_added
            agg_updated += 1
        else:
            db.add(IpamAggregate(prefix=p, rir=rir_str, date_added=date_added, description=desc))
            agg_created += 1
    db.commit()
    for item in raw_prefixes:
        p = (item.get("prefix") or "").strip()
        if not p:
            continue
        try:
            ipaddress.ip_network(p, strict=False)
        except ValueError:
            continue
        status = item.get("status")
        if isinstance(status, dict):
            status = status.get("value") or status.get("label") or "active"
        else:
            status = (status or "active")
        status = str(status)[:32]
        desc = item.get("description")
        if desc is not None and isinstance(desc, dict):
            desc = (desc.get("name") or desc.get("display") or str(desc)).strip() or None
        elif desc is not None:
            desc = (str(desc).strip() or None)
        is_pool = bool(item.get("is_pool")) if item.get("is_pool") is not None else None
        mark_utilized = bool(item.get("mark_utilized")) if item.get("mark_utilized") is not None else None
        vlan_obj = item.get("vlan")
        vlan_id = None
        if vlan_obj is not None and isinstance(vlan_obj, dict):
            vlan_id = vlan_obj.get("vid") or vlan_obj.get("id")
        if vlan_id is not None:
            try:
                vlan_id = int(vlan_id)
            except (TypeError, ValueError):
                vlan_id = None
        location = (
            _netbox_scope_to_str(item.get("scope"))
            or _netbox_scope_to_str(item.get("site"))
            or (item.get("location") or "").strip()[:256]
            or None
        )
        if location is not None and not location:
            location = None
        aggregate_id = _resolve_aggregate_id_for_prefix(db, p)
        existing = db.query(IpamPrefix).filter(IpamPrefix.prefix == p).first()
        if existing:
            existing.status = status
            existing.description = desc or existing.description
            if is_pool is not None:
                existing.is_pool = is_pool
            if mark_utilized is not None:
                existing.mark_utilized = mark_utilized
            if vlan_id is not None:
                existing.vlan_id = vlan_id
            if location is not None:
                existing.location = location
            if aggregate_id is not None:
                existing.aggregate_id = aggregate_id
            pref_updated += 1
        else:
            db.add(IpamPrefix(
                prefix=p,
                status=status,
                description=desc,
                is_pool=is_pool if is_pool is not None else False,
                mark_utilized=mark_utilized if mark_utilized is not None else False,
                vlan_id=vlan_id,
                location=location,
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


# ---------- DHCP ----------
@router.get("/dhcp/servers")
def list_dhcp_servers(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db=Depends(get_db)):
    total = db.query(DhcpServer).count()
    rows = db.query(DhcpServer).offset(skip).limit(limit).all()
    return {"data": {"items": [r.to_dict() for r in rows], "total": total}}


@router.post("/dhcp/sync-from-wmi")
def dhcp_sync_from_wmi(db=Depends(get_db)):
    result = run_dhcp_wmi_sync(db)
    return {"data": result}


@router.get("/dhcp/servers/{server_id}/scopes", response_model=DhcpScopesListResponse)
def list_dhcp_scopes(server_id: int, db=Depends(get_db)):
    rows = db.query(DhcpScope).filter(DhcpScope.dhcp_server_id == server_id).all()
    return DhcpScopesListResponse(items=[r.to_dict() for r in rows], total=len(rows))


@router.get("/dhcp/scopes/{scope_id}")
def get_dhcp_scope(scope_id: int, db=Depends(get_db)):
    s = db.query(DhcpScope).filter(DhcpScope.id == scope_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scope 不存在")
    return s.to_dict()


@router.get("/dhcp/scopes/{scope_id}/ips")
def list_dhcp_scope_ips(scope_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db=Depends(get_db)):
    rows = db.query(DhcpLease).filter(DhcpLease.scope_id == scope_id).offset(skip).limit(limit).all()
    total = db.query(DhcpLease).filter(DhcpLease.scope_id == scope_id).count()
    return {"data": {"items": [r.to_dict() for r in rows], "total": total}}


@router.post("/dhcp/scopes/{scope_id}/link-prefix")
def link_scope_prefix(scope_id: int, body: ScopeLinkPrefixBody, db=Depends(get_db)):
    s = db.query(DhcpScope).filter(DhcpScope.id == scope_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scope 不存在")
    s.prefix_id = body.prefix_id
    db.commit()
    db.refresh(s)
    return s.to_dict()


# ---------- DHCP WMI 目标 ----------
@router.get("/dhcp/wmi-targets")
def list_wmi_targets(db=Depends(get_db)):
    rows = db.query(DhcpWmiTarget).all()
    return {"data": [r.to_dict() for r in rows]}


@router.post("/dhcp/wmi-targets")
def create_wmi_target(body: DhcpWmiTargetCreate, db=Depends(get_db)):
    t = DhcpWmiTarget(
        name=body.name,
        host=body.host,
        port=body.port or 5985,
        username=body.username,
        password=body.password,
        use_ssl=body.use_ssl or False,
        enabled=body.enabled if body.enabled is not None else True,
        windows_credential_id=body.windows_credential_id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t.to_dict()


@router.put("/dhcp/wmi-targets/{target_id}")
def update_wmi_target(target_id: int, body: DhcpWmiTargetUpdate, db=Depends(get_db)):
    t = db.query(DhcpWmiTarget).filter(DhcpWmiTarget.id == target_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="目标不存在")
    if body.name is not None:
        t.name = body.name
    if body.host is not None:
        t.host = body.host
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
    if body.windows_credential_id is not None:
        t.windows_credential_id = body.windows_credential_id
    db.commit()
    db.refresh(t)
    return t.to_dict()


@router.delete("/dhcp/wmi-targets/{target_id}")
def delete_wmi_target(target_id: int, db=Depends(get_db)):
    t = db.query(DhcpWmiTarget).filter(DhcpWmiTarget.id == target_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="目标不存在")
    db.delete(t)
    db.commit()
    return {"message": "已删除"}
