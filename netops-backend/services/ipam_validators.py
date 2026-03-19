# IPAM 校验：供 ipam_router 与表格导入共用
import ipaddress
from typing import Optional

from sqlalchemy.orm import Session

from database.ipam_models import IpamAggregate


def validate_cidr_format(cidr: str) -> str:
    """校验并返回规范化 CIDR 字符串。"""
    if cidr is None or not str(cidr).strip():
        raise ValueError("网段不能为空")
    net = ipaddress.ip_network(str(cidr).strip(), strict=False)
    return str(net)


def ipam_aggregate_overlaps_existing(db: Session, prefix_str: str, exclude_id: Optional[int] = None) -> bool:
    """检查 prefix_str 是否与库中已有 Aggregate 重叠（排除 exclude_id）。"""
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


def check_prefix_in_aggregate(db: Session, prefix_str: str, aggregate_id: Optional[int]) -> None:
    """若 aggregate_id 非空，校验 prefix 完全落在该 Aggregate 内；否则不校验。失败抛出 ValueError。"""
    if aggregate_id is None:
        return
    agg = db.query(IpamAggregate).filter(IpamAggregate.id == aggregate_id).first()
    if not agg or not agg.prefix:
        raise ValueError("所选 Aggregate 不存在或无效")
    try:
        prefix_net = ipaddress.ip_network(prefix_str.strip(), strict=False)
        agg_net = ipaddress.ip_network(agg.prefix, strict=False)
    except ValueError:
        raise ValueError("无效 CIDR")
    if not prefix_net.subnet_of(agg_net):
        raise ValueError("Prefix 不在所选 Aggregate 范围内")
