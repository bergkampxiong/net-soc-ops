# IPAM 聚合/网段 CSV 表格导入（固定中文表头，与 docs/IPAM表格导入格式.md 一致）
import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database.ipam_models import IpamAggregate, IpamPrefix
from services.ipam_validators import (
    validate_cidr_format,
    ipam_aggregate_overlaps_existing,
    check_prefix_in_aggregate,
)

logger = logging.getLogger(__name__)

# 表头顺序必须与模板、文档完全一致
AGGREGATE_CSV_HEADERS: List[str] = ["网段", "分配机构", "分配日期", "描述"]
PREFIX_CSV_HEADERS: List[str] = ["网段", "状态", "描述", "地址池", "标记已用", "VLAN", "位置", "所属聚合网段", "聚合ID"]

ALLOWED_PREFIX_STATUS = frozenset({"active", "reserved", "deprecated", "container"})


def aggregate_template_csv() -> str:
    """UTF-8 BOM + 表头行，供前端下载与后端校验一致"""
    return "\ufeff" + ",".join(AGGREGATE_CSV_HEADERS) + "\n"


def prefix_template_csv() -> str:
    return "\ufeff" + ",".join(PREFIX_CSV_HEADERS) + "\n"


def _strip_bom(text: str) -> str:
    return (text or "").lstrip("\ufeff")


def _validate_and_read_rows(content: str, expected_headers: List[str]) -> List[Tuple[int, Dict[str, str]]]:
    raw = _strip_bom(content or "")
    if not raw.strip():
        raise ValueError("CSV 内容为空")
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        raise ValueError("CSV 无表头")
    got = [(h or "").strip() for h in reader.fieldnames]
    if got != expected_headers:
        raise ValueError("表头列名或顺序不正确，请使用系统「下载模板」。期望: " + "，".join(expected_headers))
    out: List[Tuple[int, Dict[str, str]]] = []
    for row_idx, row in enumerate(reader, start=2):
        if not row:
            continue
        cleaned: Dict[str, str] = {}
        for k, v in row.items():
            key = (k or "").strip()
            cleaned[key] = (v or "").strip() if isinstance(v, str) else (str(v) if v is not None else "")
        if all(not str(v).strip() for v in cleaned.values()):
            continue
        out.append((row_idx, cleaned))
    return out


def _parse_date_optional(s: str) -> Optional[Any]:
    t = (s or "").strip()
    if not t:
        return None
    try:
        return datetime.strptime(t[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("分配日期须为 YYYY-MM-DD")


def _find_aggregate_by_normalized(db: Session, norm: str) -> Optional[IpamAggregate]:
    for a in db.query(IpamAggregate).all():
        if not a.prefix:
            continue
        try:
            if validate_cidr_format(a.prefix) == norm:
                return a
        except ValueError:
            continue
    return None


def _find_prefix_by_normalized(db: Session, norm: str) -> Optional[IpamPrefix]:
    for p in db.query(IpamPrefix).all():
        if not p.prefix:
            continue
        try:
            if validate_cidr_format(p.prefix) == norm:
                return p
        except ValueError:
            continue
    return None


def _parse_bool_cell(val: Any, *, required: bool) -> bool:
    s = str(val if val is not None else "").strip().lower()
    if not s:
        if required:
            raise ValueError("布尔列不能为空")
        return False
    if s in ("1", "true", "yes", "是", "y"):
        return True
    if s in ("0", "false", "no", "否", "n"):
        return False
    raise ValueError(f"无法解析布尔值: {val}")


def _resolve_aggregate_id_from_row(db: Session, row: Dict[str, str]) -> Optional[int]:
    id_cell = (row.get("聚合ID") or "").strip()
    pfx_cell = (row.get("所属聚合网段") or "").strip()
    if id_cell:
        try:
            aid = int(id_cell)
        except ValueError:
            raise ValueError("聚合ID 必须为整数")
        agg = db.query(IpamAggregate).filter(IpamAggregate.id == aid).first()
        if not agg:
            raise ValueError(f"聚合ID {aid} 不存在")
        return aid
    if pfx_cell:
        norm = validate_cidr_format(pfx_cell)
        a = _find_aggregate_by_normalized(db, norm)
        if not a:
            raise ValueError(f"未找到所属聚合网段: {norm}")
        return a.id
    return None


def import_aggregates_csv(db: Session, content: str) -> Tuple[int, int, int, List[str]]:
    """返回 (imported, updated, failed, errors)"""
    rows = _validate_and_read_rows(content, AGGREGATE_CSV_HEADERS)
    imported = updated = failed = 0
    errors: List[str] = []
    seen_norm: set = set()

    for row_num, row in rows:
        try:
            raw_p = (row.get("网段") or "").strip()
            if not raw_p:
                failed += 1
                errors.append(f"第{row_num}行: 网段不能为空")
                continue
            norm = validate_cidr_format(raw_p)
            if norm in seen_norm:
                failed += 1
                errors.append(f"第{row_num}行: 文件内重复网段 {norm}")
                continue
            seen_norm.add(norm)

            existing = _find_aggregate_by_normalized(db, norm)
            date_val = _parse_date_optional(row.get("分配日期") or "")

            if existing:
                if (row.get("分配机构") or "").strip():
                    existing.rir = row["分配机构"].strip()
                if date_val is not None:
                    existing.date_added = date_val
                if (row.get("描述") or "").strip():
                    existing.description = row["描述"].strip()
                db.commit()
                updated += 1
            else:
                if ipam_aggregate_overlaps_existing(db, norm):
                    failed += 1
                    errors.append(f"第{row_num}行: 网段与已有聚合重叠 {norm}")
                    continue
                rir = (row.get("分配机构") or "").strip() or None
                desc = (row.get("描述") or "").strip() or None
                db.add(
                    IpamAggregate(
                        prefix=norm,
                        rir=rir,
                        date_added=date_val,
                        description=desc,
                    )
                )
                db.commit()
                imported += 1
        except ValueError as e:
            db.rollback()
            failed += 1
            errors.append(f"第{row_num}行: {e}")
        except Exception as e:
            db.rollback()
            logger.exception("聚合导入第%s行失败", row_num)
            failed += 1
            errors.append(f"第{row_num}行: {e}")

    return imported, updated, failed, errors


def import_prefixes_csv(db: Session, content: str) -> Tuple[int, int, int, List[str]]:
    rows = _validate_and_read_rows(content, PREFIX_CSV_HEADERS)
    imported = updated = failed = 0
    errors: List[str] = []
    seen_norm: set = set()

    for row_num, row in rows:
        try:
            raw_p = (row.get("网段") or "").strip()
            if not raw_p:
                failed += 1
                errors.append(f"第{row_num}行: 网段不能为空")
                continue
            norm = validate_cidr_format(raw_p)
            if norm in seen_norm:
                failed += 1
                errors.append(f"第{row_num}行: 文件内重复网段 {norm}")
                continue
            seen_norm.add(norm)

            st_raw = (row.get("状态") or "").strip().lower()
            if not st_raw or st_raw not in ALLOWED_PREFIX_STATUS:
                failed += 1
                errors.append(f"第{row_num}行: 状态须为 active/reserved/deprecated/container")
                continue

            agg_id = _resolve_aggregate_id_from_row(db, row)
            check_prefix_in_aggregate(db, norm, agg_id)

            vlan_raw = (row.get("VLAN") or "").strip()
            vlan_id: Optional[int] = None
            if vlan_raw:
                try:
                    vlan_id = int(vlan_raw)
                except ValueError:
                    raise ValueError("VLAN 须为整数")

            location = (row.get("位置") or "").strip() or None

            existing = _find_prefix_by_normalized(db, norm)

            if existing:
                existing.status = st_raw
                if (row.get("描述") or "").strip():
                    existing.description = row["描述"].strip()
                if (row.get("地址池") or "").strip():
                    existing.is_pool = _parse_bool_cell(row.get("地址池"), required=False)
                if (row.get("标记已用") or "").strip():
                    existing.mark_utilized = _parse_bool_cell(row.get("标记已用"), required=False)
                if vlan_raw:
                    existing.vlan_id = vlan_id
                if (row.get("位置") or "").strip():
                    existing.location = location
                existing.aggregate_id = agg_id
                db.commit()
                updated += 1
            else:
                is_pool = _parse_bool_cell(row.get("地址池"), required=False)
                mark_u = _parse_bool_cell(row.get("标记已用"), required=False)
                desc = (row.get("描述") or "").strip() or None
                db.add(
                    IpamPrefix(
                        prefix=norm,
                        status=st_raw,
                        description=desc,
                        is_pool=is_pool,
                        mark_utilized=mark_u,
                        vlan_id=vlan_id,
                        location=location,
                        aggregate_id=agg_id,
                    )
                )
                db.commit()
                imported += 1
        except ValueError as e:
            db.rollback()
            failed += 1
            errors.append(f"第{row_num}行: {e}")
        except Exception as e:
            db.rollback()
            logger.exception("网段导入第%s行失败", row_num)
            failed += 1
            errors.append(f"第{row_num}行: {e}")

    return imported, updated, failed, errors
