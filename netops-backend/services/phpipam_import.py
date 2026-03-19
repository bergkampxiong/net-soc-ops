# phpIPAM REST 拉取与写入本地 ipam_aggregates / ipam_prefixes（一次性导入）
import ipaddress
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from sqlalchemy.orm import Session

from database.ipam_models import IpamAggregate, IpamPrefix

logger = logging.getLogger(__name__)


def _resolve_aggregate_id_for_prefix(db: Session, prefix_str: str) -> Optional[int]:
    """与 ipam_router 一致：取包含该 prefix 的最小 aggregate。"""
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


def _is_truthy_folder(val: Any) -> bool:
    if val is True or val == 1:
        return True
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes")
    return False


def _row_to_cidr(row: Dict[str, Any]) -> Optional[str]:
    """phpIPAM subnet + mask -> 规范 CIDR 字符串。"""
    subnet = row.get("subnet")
    mask = row.get("mask")
    if subnet is None or mask is None:
        return None
    try:
        mask_int = int(mask)
    except (TypeError, ValueError):
        return None
    s = str(subnet).strip()
    if not s:
        return None
    cidr = f"{s}/{mask_int}"
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        return str(net)
    except ValueError:
        return None


def _phpipam_location_to_str(loc: Any) -> Optional[str]:
    if loc is None:
        return None
    if isinstance(loc, str):
        t = loc.strip()[:256]
        return t or None
    if isinstance(loc, dict):
        t = (loc.get("name") or loc.get("display") or loc.get("title") or "").strip()[:256]
        return t or None
    t = str(loc).strip()[:256]
    return t or None


def _phpipam_status_to_str(row: Dict[str, Any]) -> str:
    """将 phpIPAM 子网状态映射为本地 status 短字符串。"""
    raw = row.get("status") or row.get("state")
    if isinstance(raw, dict):
        raw = raw.get("name") or raw.get("value") or raw.get("label")
    if raw is not None and str(raw).strip():
        return str(raw).strip()[:32]
    # 常见：无显式状态，按是否停用等推断
    if _is_truthy_folder(row.get("disableScan")):
        return "deprecated"
    return "active"


def _phpipam_description(row: Dict[str, Any]) -> Optional[str]:
    d = row.get("description")
    if d is None:
        return None
    if isinstance(d, str):
        t = d.strip()
        return t or None
    return str(d).strip() or None


def _phpipam_vlan_id(row: Dict[str, Any]) -> Optional[int]:
    vid = row.get("vlanId") or row.get("vlan_id") or row.get("vlan")
    if vid is None:
        return None
    if isinstance(vid, dict):
        vid = vid.get("vlanId") or vid.get("id") or vid.get("number")
    try:
        return int(vid)
    except (TypeError, ValueError):
        return None


def fetch_phpipam_subnets(api_base_url: str, token: str) -> List[Dict[str, Any]]:
    """
    拉取 phpIPAM 全部子网。api_base_url 为应用 API 根，如 https://host/api/my_app（可无末尾斜杠）。
    使用官方支持的 token 请求头。
    """
    base = api_base_url.rstrip("/")
    headers = {
        "token": token,
        "phpipam-token": token,
    }
    last_error: Optional[Exception] = None
    for path in ("/subnets/all/", "/subnets/"):
        url = base + path
        try:
            resp = requests.get(url, headers=headers, timeout=120)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            last_error = e
            logger.warning("phpIPAM 请求失败 %s: %s", url, e)
            continue
        if not isinstance(payload, dict):
            continue
        code = payload.get("code")
        if code is not None and int(code) != 200:
            msg = payload.get("message") or str(payload)
            raise RuntimeError(f"phpIPAM 返回错误 code={code}: {msg}")
        data = payload.get("data")
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # 部分版本可能返回单对象
            return [data]
    if last_error:
        raise RuntimeError(f"phpIPAM 拉取失败: {last_error}") from last_error
    return []


def apply_phpipam_subnets_to_db(db: Session, raw_items: List[Dict[str, Any]]) -> Tuple[int, int, int, int]:
    """
    将 phpIPAM 子网列表写入 ipam_aggregates（folder）与 ipam_prefixes（非 folder）。
    返回 (agg_created, agg_updated, pref_created, pref_updated)。
    """
    folder_rows: List[Dict[str, Any]] = []
    leaf_rows: List[Dict[str, Any]] = []
    for row in raw_items:
        if not isinstance(row, dict):
            continue
        cidr = _row_to_cidr(row)
        if not cidr:
            continue
        if _is_truthy_folder(row.get("isFolder")):
            folder_rows.append(row)
        else:
            leaf_rows.append(row)

    agg_created = agg_updated = pref_created = pref_updated = 0

    for row in folder_rows:
        p = _row_to_cidr(row)
        if not p:
            continue
        try:
            ipaddress.ip_network(p, strict=False)
        except ValueError:
            continue
        existing = db.query(IpamAggregate).filter(IpamAggregate.prefix == p).first()
        desc = _phpipam_description(row)
        if existing:
            if desc is not None:
                existing.description = desc or existing.description
            agg_updated += 1
        else:
            db.add(IpamAggregate(prefix=p, rir=None, date_added=None, description=desc))
            agg_created += 1

    db.commit()

    for row in leaf_rows:
        p = _row_to_cidr(row)
        if not p:
            continue
        try:
            ipaddress.ip_network(p, strict=False)
        except ValueError:
            continue
        status = _phpipam_status_to_str(row)
        desc = _phpipam_description(row)
        vlan_id = _phpipam_vlan_id(row)
        location = _phpipam_location_to_str(row.get("location")) or _phpipam_location_to_str(row.get("location_name"))
        aggregate_id = _resolve_aggregate_id_for_prefix(db, p)
        existing = db.query(IpamPrefix).filter(IpamPrefix.prefix == p).first()
        if existing:
            existing.status = status
            if desc is not None:
                existing.description = desc or existing.description
            if vlan_id is not None:
                existing.vlan_id = vlan_id
            if location is not None:
                existing.location = location
            if aggregate_id is not None:
                existing.aggregate_id = aggregate_id
            pref_updated += 1
        else:
            db.add(
                IpamPrefix(
                    prefix=p,
                    status=status,
                    description=desc,
                    is_pool=False,
                    mark_utilized=False,
                    vlan_id=vlan_id,
                    location=location,
                    aggregate_id=aggregate_id,
                )
            )
            pref_created += 1

    db.commit()
    return agg_created, agg_updated, pref_created, pref_updated
