# 配置管理模块 API：设备配置备份、配置摘要、变更模板、合规、服务终止（不修改其它功能）
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import difflib
import re
import logging
import json
import io
import os
import csv
import xml.etree.ElementTree as ET

from database.session import get_db
from database.cmdb_models import Asset as AssetModel, DeviceType as CMDBDeviceType
from utils.datetime_utils import utc_to_beijing_str
from database.config_module_models import (
    ConfigModuleBackup,
    ConfigCompliancePolicy,
    ConfigComplianceReport,
    ConfigComplianceReportPolicy,
    ConfigComplianceResult,
    ConfigComplianceSchedule,
    ConfigEosInfo,
)
from schemas.config_module import (
    CompliancePolicyBulkEnabledByGroup,
    BackupCreate,
    BackupResponse,
    BackupListResponse,
    DiffResponse,
    SummaryStatsResponse,
    CompliancePolicyCreate,
    CompliancePolicyUpdate,
    ComplianceRunRequest,
    ComplianceReportCreate,
    ComplianceReportUpdate,
    ComplianceReportEnabledUpdate,
    ComplianceScheduleCreate,
    ComplianceScheduleUpdate,
    ComplianceResultBatchDelete,
    EosInfoCreate,
    EosInfoUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["config-module"],
    responses={404: {"description": "Not found"}},
)


def _backup_to_response(b: ConfigModuleBackup, include_content: bool = False) -> dict:
    return b.to_dict(include_content=include_content)


def _device_key(device_host: Optional[str], device_id: str) -> str:
    """同一设备：device_host 非空用 device_host，否则用 device_id。"""
    if device_host and (device_host := (device_host or "").strip()):
        return device_host
    return device_id or ""


# ---------- 备份列表（须在 /backups/{id} 之前定义，避免 path 冲突）----------
@router.get("/backups", response_model=BackupListResponse)
def list_backups(
    device_id: Optional[str] = Query(None, description="设备标识"),
    device_host: Optional[str] = Query(None, description="设备 IP/主机名"),
    keyword: Optional[str] = Query(None, description="关键词：设备名、主机、备注"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO8601"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """分页列表 + 筛选。keyword 仅检索 device_name、device_host、remark。"""
    q = db.query(ConfigModuleBackup)
    if device_id:
        q = q.filter(ConfigModuleBackup.device_id == device_id)
    if device_host:
        q = q.filter(ConfigModuleBackup.device_host.ilike(f"%{device_host}%"))
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(
                ConfigModuleBackup.device_name.ilike(kw),
                ConfigModuleBackup.device_host.ilike(kw),
                ConfigModuleBackup.remark.ilike(kw),
            )
        )
    if start_time:
        try:
            t = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            q = q.filter(ConfigModuleBackup.created_at >= t)
        except ValueError:
            pass
    if end_time:
        try:
            t = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            q = q.filter(ConfigModuleBackup.created_at <= t)
        except ValueError:
            pass
    total = q.count()
    rows = q.order_by(ConfigModuleBackup.created_at.desc()).offset(skip).limit(limit).all()
    return BackupListResponse(
        items=[_backup_to_response(r, include_content=False) for r in rows],
        total=total,
    )


def _enrich_devices_with_cmdb(result: list) -> None:
    """根据 device_host 查 CMDB，为 result 中每项补充 cmdb_name、cmdb_model、cmdb_vendor、cmdb_device_type。"""
    hosts = list({x["device_host"].strip() for x in result if x.get("device_host") and (x["device_host"] or "").strip()})
    if not hosts:
        return
    try:
        from database.cmdb_session import get_cmdb_db
        cmdb_db = next(get_cmdb_db())
        try:
            assets = (
                cmdb_db.query(AssetModel)
                .filter(AssetModel.ip_address.in_(hosts))
                .options(
                    joinedload(AssetModel.network_device),
                    joinedload(AssetModel.vendor),
                    joinedload(AssetModel.device_type),
                )
                .all()
            )
            cmdb_map = {}
            for a in assets:
                if not a.ip_address:
                    continue
                ip = (a.ip_address or "").strip()
                if ip not in cmdb_map:
                    nd = a.network_device
                    vendor_name = a.vendor.name if a.vendor else None
                    device_type_name = a.device_type.name if a.device_type else None
                    cmdb_map[ip] = {
                        "cmdb_name": a.name,
                        "cmdb_model": nd.device_model if nd else None,
                        "cmdb_vendor": vendor_name,
                        "cmdb_device_type": device_type_name,
                    }
            for x in result:
                host = (x.get("device_host") or "").strip()
                if host and host in cmdb_map:
                    x.update(cmdb_map[host])
        finally:
            cmdb_db.close()
    except Exception as e:
        logger.warning("CMDB 查询失败，设备列表不补充 CMDB 信息: %s", e)


def _get_backup_devices_filtered_by_device_type(db: Session, device_type: str) -> List[Tuple[str, str]]:
    """返回设备类型与 device_type 一致且存在最新配置备份的设备列表，每项 (device_host or '', device_id)。"""
    if not (device_type or (device_type := (device_type or "").strip())):
        return []
    rows = (
        db.query(ConfigModuleBackup)
        .order_by(ConfigModuleBackup.created_at.desc())
        .all()
    )
    groups: dict = {}
    for r in rows:
        key = _device_key(r.device_host, r.device_id)
        if key not in groups:
            groups[key] = r
    result = [{"device_key": k, "device_id": v.device_id, "device_host": v.device_host} for k, v in groups.items()]
    _enrich_devices_with_cmdb(result)
    matched = [x for x in result if (x.get("cmdb_device_type") or "").strip().lower() == device_type.strip().lower()]
    return [(x.get("device_host") or "", x.get("device_id") or "") for x in matched]


@router.get("/backups/devices")
def list_backup_devices(
    keyword: Optional[str] = Query(None, description="关键词（综合）"),
    device_name: Optional[str] = Query(None, description="设备名称"),
    device_host: Optional[str] = Query(None, description="IP 地址"),
    model: Optional[str] = Query(None, description="设备型号"),
    vendor: Optional[str] = Query(None, description="厂商"),
    db: Session = Depends(get_db),
):
    """按设备聚合：同一设备一行，返回设备名、IP、备份数、最近备份时间；优先用 CMDB 补充设备名称、型号、厂商。支持多条件筛选。"""
    rows = (
        db.query(ConfigModuleBackup)
        .order_by(ConfigModuleBackup.created_at.desc())
        .all()
    )
    groups: dict = {}
    for r in rows:
        key = _device_key(r.device_host, r.device_id)
        if key not in groups:
            groups[key] = []
        groups[key].append(r)
    result = []
    for key, group in groups.items():
        latest = group[0]
        result.append({
            "device_key": key,
            "device_id": latest.device_id,
            "device_host": latest.device_host,
            "device_name": latest.device_name,
            "backup_count": len(group),
            "latest_created_at": utc_to_beijing_str(latest.created_at),
        })
    _enrich_devices_with_cmdb(result)
    # 多条件筛选：device_name / device_host / model / vendor 任一传入则按条件 AND 过滤
    dn = (device_name or "").strip()
    if dn:
        dn_lower = dn.lower()
        result = [
            x for x in result
            if dn_lower in (x.get("device_name") or "").lower()
            or dn_lower in (x.get("cmdb_name") or "").lower()
        ]
    dh = (device_host or "").strip()
    if dh:
        result = [x for x in result if dh.lower() in (x.get("device_host") or "").lower()]
    mdl = (model or "").strip()
    if mdl:
        result = [x for x in result if mdl.lower() in (x.get("cmdb_model") or "").lower()]
    vnd = (vendor or "").strip()
    if vnd:
        result = [x for x in result if vnd.lower() in (x.get("cmdb_vendor") or "").lower()]
    # 未使用分项条件时保留关键词综合搜索
    if not any([dn, dh, mdl, vnd]) and keyword and (keyword := (keyword or "").strip()):
        kw = keyword.lower()
        result = [
            x
            for x in result
            if kw in (x.get("device_name") or "").lower()
            or kw in (x.get("device_host") or "").lower()
            or kw in (x.get("device_id") or "").lower()
            or kw in (x.get("cmdb_name") or "").lower()
            or kw in (x.get("cmdb_model") or "").lower()
            or kw in (x.get("cmdb_vendor") or "").lower()
        ]
    result.sort(key=lambda x: x["latest_created_at"] or "", reverse=True)
    return {"items": result, "total": len(result)}


@router.get("/backups/device-history")
def device_history_query(
    device_host: Optional[str] = Query(None, description="设备 IP/主机名"),
    device_id: Optional[str] = Query(None, description="设备标识（device_host 为空时用）"),
    limit: int = Query(90, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """单设备备份历史，按时间倒序，不含 content。传 device_host 或 device_id 其一。"""
    if device_host and (device_host := (device_host or "").strip()):
        q = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.device_host == device_host)
    elif device_id:
        q = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.device_id == device_id)
    else:
        raise HTTPException(status_code=400, detail="device_host or device_id required")
    rows = (
        q.order_by(ConfigModuleBackup.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_backup_to_response(r, include_content=False) for r in rows]


@router.get("/backups/device/{device_id}/history")
def device_history(
    device_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """单设备版本历史，按时间倒序，不含 content。"""
    rows = (
        db.query(ConfigModuleBackup)
        .filter(ConfigModuleBackup.device_id == device_id)
        .order_by(ConfigModuleBackup.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_backup_to_response(r, include_content=False) for r in rows]


@router.get("/backups/diff", response_model=DiffResponse)
def backups_diff(
    id_a: int = Query(..., description="备份 A 的 id"),
    id_b: int = Query(..., description="备份 B 的 id"),
    db: Session = Depends(get_db),
):
    """两版本文本 diff。"""
    a = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.id == id_a).first()
    b = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.id == id_b).first()
    if not a or not b:
        raise HTTPException(status_code=404, detail="Backup not found")
    lines_a = (a.content or "").splitlines()
    lines_b = (b.content or "").splitlines()
    diff_text = "\n".join(
        difflib.unified_diff(lines_a, lines_b, lineterm="", fromfile="version_a", tofile="version_b")
    )
    return DiffResponse(diff_text=diff_text, id_a=id_a, id_b=id_b)


@router.post("/backups", response_model=BackupResponse, status_code=201)
def create_backup(
    body: BackupCreate,
    db: Session = Depends(get_db),
):
    """写入一条备份（流程节点/API 调用）。同一设备最多保留 90 条，超出则删除最早一条再插入。"""
    key = _device_key(body.device_host, body.device_id)
    if not key:
        raise HTTPException(status_code=400, detail="device_id or device_host required")
    # 按设备统计：device_host 非空按 device_host，否则按 device_id
    if body.device_host and (body.device_host or "").strip():
        q = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.device_host == (body.device_host or "").strip())
    else:
        q = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.device_id == body.device_id)
    count = q.count()
    if count >= 90:
        oldest = q.order_by(ConfigModuleBackup.created_at.asc()).first()
        if oldest:
            db.delete(oldest)
            db.flush()
    b = ConfigModuleBackup(
        device_id=body.device_id,
        device_name=body.device_name,
        device_host=body.device_host,
        job_execution_id=body.job_execution_id,
        content=body.content,
        source=body.source or "api",
        remark=body.remark,
        created_by="system",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return BackupResponse(**_backup_to_response(b, include_content=True))


@router.get("/backups/{backup_id}", response_model=BackupResponse)
def get_backup(
    backup_id: int,
    db: Session = Depends(get_db),
):
    """单条备份详情（含 content）。"""
    b = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.id == backup_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Backup not found")
    return BackupResponse(**_backup_to_response(b, include_content=True))


@router.delete("/backups/{backup_id}", status_code=204)
def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db),
):
    """删除一条备份。"""
    b = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.id == backup_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Backup not found")
    db.delete(b)
    db.commit()
    return None


# ---------- 配置摘要 ----------
@router.get("/summary/stats", response_model=SummaryStatsResponse)
def summary_stats(db: Session = Depends(get_db)):
    """配置摘要统计。首版无失败数，backup_*_fail 为 0。"""
    now = datetime.utcnow()
    t24 = now - timedelta(hours=24)
    t7d = now - timedelta(days=7)
    device_count = (
        db.query(func.count(func.distinct(ConfigModuleBackup.device_id)))
        .scalar() or 0
    )
    backup_24h = (
        db.query(func.count(ConfigModuleBackup.id))
        .filter(ConfigModuleBackup.created_at >= t24)
        .scalar() or 0
    )
    backup_7d = (
        db.query(func.count(ConfigModuleBackup.id))
        .filter(ConfigModuleBackup.created_at >= t7d)
        .scalar() or 0
    )
    return SummaryStatsResponse(
        device_count=device_count,
        backup_24h_success=backup_24h,
        backup_24h_fail=0,
        backup_7d_success=backup_7d,
        backup_7d_fail=0,
        change_count_7d=backup_7d,
        compliance_pass_rate=None,
    )


@router.get("/summary/backups-by-day")
def summary_backups_by_day(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """按日统计最近 N 天备份数，用于趋势图。返回 [{ date: 'YYYY-MM-DD', count: n }, ...]。"""
    now = datetime.utcnow()
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.query(ConfigModuleBackup.created_at)
        .filter(ConfigModuleBackup.created_at >= start)
        .all()
    )
    from collections import defaultdict
    by_day: dict = defaultdict(int)
    for (created_at,) in rows:
        if created_at:
            key = created_at.strftime("%Y-%m-%d") if hasattr(created_at, "strftime") else str(created_at)[:10]
            by_day[key] += 1
    result = []
    for i in range(days):
        d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result.append({"date": d, "count": by_day.get(d, 0)})
    return result


@router.get("/summary/backups-by-source")
def summary_backups_by_source(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """按来源统计最近 N 天备份数，用于饼图。返回 [{ name: 'workflow', value: n }, ...]。"""
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    rows = (
        db.query(ConfigModuleBackup.source, func.count(ConfigModuleBackup.id))
        .filter(ConfigModuleBackup.created_at >= start)
        .group_by(ConfigModuleBackup.source)
        .all()
    )
    name_map = {"workflow": "流程", "manual": "手动", "api": "API"}
    return [
        {"name": name_map.get((s or "api").lower(), s or "其他"), "value": c}
        for s, c in rows
    ]


@router.get("/summary/recent-backups")
def recent_backups(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """最近备份列表（元数据，不含 content）。"""
    rows = (
        db.query(ConfigModuleBackup)
        .order_by(ConfigModuleBackup.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_backup_to_response(r, include_content=False) for r in rows]


# ---------- 合规策略 ----------
@router.get("/compliance/policies")
def list_compliance_policies(
    group: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    report_id: Optional[int] = Query(None, description="规则集(报告)ID，仅返回该规则集下的策略"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """策略列表；支持按 group、enabled、report_id（规则集）筛选。"""
    q = db.query(ConfigCompliancePolicy)
    if group is not None and (group := (group or "").strip()):
        q = q.filter(ConfigCompliancePolicy.group == group)
    if enabled is not None:
        q = q.filter(ConfigCompliancePolicy.enabled == enabled)
    if report_id is not None:
        total = db.query(ConfigComplianceReportPolicy).filter(ConfigComplianceReportPolicy.report_id == report_id).count()
        links = db.query(ConfigComplianceReportPolicy).filter(ConfigComplianceReportPolicy.report_id == report_id).order_by(ConfigComplianceReportPolicy.sort_order).offset(skip).limit(limit).all()
        policy_ids = [x.policy_id for x in links]
        if not policy_ids:
            return {"items": [], "total": total}
        rows = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id.in_(policy_ids)).all()
        id_to_row = {r.id: r for r in rows}
        rows = [id_to_row[pid] for pid in policy_ids if pid in id_to_row]
        return {"items": [r.to_dict() for r in rows], "total": total}
    total = q.count()
    rows = q.order_by(ConfigCompliancePolicy.id).offset(skip).limit(limit).all()
    return {"items": [r.to_dict() for r in rows], "total": total}


@router.get("/compliance/policies/{policy_id}")
def get_compliance_policy(
    policy_id: int,
    db: Session = Depends(get_db),
):
    p = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id == policy_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    return p.to_dict()


@router.post("/compliance/policies", status_code=201)
def create_compliance_policy(
    body: CompliancePolicyCreate,
    db: Session = Depends(get_db),
):
    p = ConfigCompliancePolicy(
        name=body.name,
        rule_type=body.rule_type,
        rule_content=body.rule_content,
        device_type=body.device_type,
        description=body.description,
        group=body.group,
        enabled=body.enabled if body.enabled is not None else True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.put("/compliance/policies/{policy_id}")
def update_compliance_policy(
    policy_id: int,
    body: CompliancePolicyUpdate,
    db: Session = Depends(get_db),
):
    p = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id == policy_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    if body.name is not None:
        p.name = body.name
    if body.rule_type is not None:
        p.rule_type = body.rule_type
    if body.rule_content is not None:
        p.rule_content = body.rule_content
    if body.device_type is not None:
        p.device_type = body.device_type
    if body.description is not None:
        p.description = body.description
    if body.group is not None:
        p.group = body.group
    if body.enabled is not None:
        p.enabled = body.enabled
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.patch("/compliance/policies/{policy_id}/enabled")
def update_compliance_policy_enabled(
    policy_id: int,
    body: ComplianceReportEnabledUpdate,
    db: Session = Depends(get_db),
):
    """策略启用/停用。"""
    p = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id == policy_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    p.enabled = body.enabled
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.patch("/compliance/policies/bulk-enabled-by-group")
def bulk_update_compliance_policies_enabled_by_group(
    body: CompliancePolicyBulkEnabledByGroup,
    db: Session = Depends(get_db),
):
    """按分组统一设置启用状态（一个文件导入为一组，前端按组显示、一组一个开关）。"""
    q = db.query(ConfigCompliancePolicy)
    if body.group is None or (isinstance(body.group, str) and not body.group.strip()):
        q = q.filter(or_(ConfigCompliancePolicy.group.is_(None), ConfigCompliancePolicy.group == ""))
    else:
        q = q.filter(ConfigCompliancePolicy.group == body.group.strip())
    updated = q.update({ConfigCompliancePolicy.enabled: body.enabled}, synchronize_session=False)
    db.commit()
    return {"updated": updated}


@router.delete("/compliance/policies/by-group", status_code=200)
def delete_compliance_policies_by_group(
    group: Optional[str] = Query(None, description="分组名，不传或空表示删除未分组的策略"),
    db: Session = Depends(get_db),
):
    """按分组删除全部策略（删除整组/整份导入）。"""
    q = db.query(ConfigCompliancePolicy)
    if group is None or (isinstance(group, str) and not group.strip()):
        q = q.filter(or_(ConfigCompliancePolicy.group.is_(None), ConfigCompliancePolicy.group == ""))
    else:
        q = q.filter(ConfigCompliancePolicy.group == group.strip())
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}


@router.delete("/compliance/policies/{policy_id}", status_code=204)
def delete_compliance_policy(
    policy_id: int,
    db: Session = Depends(get_db),
):
    p = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id == policy_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(p)
    db.commit()
    return None


def _find_el(parent, *tag_candidates):
    """在 parent 下按标签名查找子元素（兼容无命名空间或带命名空间）。"""
    for tag in tag_candidates:
        el = parent.find(tag)
        if el is not None:
            return el
    if parent.tag and "}" in parent.tag:
        ns = parent.tag.split("}", 1)[0] + "}"
        for tag in tag_candidates:
            el = parent.find(ns + tag)
            if el is not None:
                return el
    return None


def _findall_el(parent, tag):
    """在 parent 下按标签名查找所有子元素。"""
    out = parent.findall(tag)
    if out:
        return out
    if parent.tag and "}" in parent.tag:
        ns = parent.tag.split("}", 1)[0] + "}"
        return parent.findall(ns + tag)
    return []


def _text(el):
    return (el.text or "").strip() if el is not None else ""


def _parse_policies_from_xml(content: str) -> Tuple[str, list]:
    """从 XML 解析策略列表，返回 (规则集名称, 策略列表)。支持本系统导出与 NCM 规则集格式。"""
    root = ET.fromstring(content)
    rule_set_name = (root.get("name") or root.get("Name") or _text(_find_el(root, "Name")) or _text(_find_el(root, "Group")) or "").strip()
    assn = _find_el(root, "AssignedPolicies", "AssignedPolicy")
    if assn is None:
        return rule_set_name, []
    out = []
    for pol in _findall_el(assn, "Policy"):
        rcontent = pol.get("rule_content") or pol.get("RuleContent") or pol.get("SimplePatternText") or ""
        if rcontent:
            out.append({
                "name": pol.get("name") or pol.get("Name") or "策略",
                "rule_type": pol.get("rule_type") or pol.get("RuleType") or "must_contain",
                "rule_content": rcontent,
                "device_type": pol.get("device_type") or pol.get("DeviceType"),
                "group": rule_set_name or pol.get("group") or pol.get("Group"),
            })
            continue
        policy_group = _text(_find_el(pol, "PolicyName")) or rule_set_name or "策略"
        rules_el = _find_el(pol, "AssignedPolicyRules")
        if rules_el is None:
            continue
        for rule in _findall_el(rules_el, "PolicyRule"):
            simple_text = _text(_find_el(rule, "SimplePatternText"))
            if not simple_text:
                continue
            rule_name = _text(_find_el(rule, "RuleName")) or simple_text[:50]
            pattern_type = (_text(_find_el(rule, "PatternType")) or "").lower()
            rule_type = "regex" if "regex" in pattern_type else "must_contain"
            out.append({
                "name": rule_name,
                "rule_type": rule_type,
                "rule_content": simple_text,
                "device_type": None,
                "group": policy_group or rule_set_name,
            })
    return rule_set_name, out


@router.post("/compliance/policies/import")
def import_compliance_policies(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """策略管理导入：仅创建策略（不创建报告）。支持 JSON 与 XML（含 NCM 格式）；可用文档名作为策略分组便于筛选。"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="请上传文件")
        content = file.file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        content_stripped = content.strip()
        policies_data: list = []
        doc_group = ""
        if content_stripped.startswith("<"):
            doc_group, policies_data = _parse_policies_from_xml(content)
        else:
            data = json.loads(content)
            policies_data = data.get("policies") if isinstance(data, dict) else data
            if not isinstance(policies_data, list):
                raise HTTPException(status_code=400, detail="JSON 需包含 policies 数组")
        if not (doc_group or "").strip():
            doc_group = (os.path.splitext(file.filename or "")[0] or "").strip()
        created = 0
        for item in policies_data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            rule_content = item.get("rule_content")
            if not name or not rule_content:
                continue
            p = ConfigCompliancePolicy(
                name=name,
                rule_type=item.get("rule_type", "must_contain"),
                rule_content=rule_content,
                device_type=item.get("device_type"),
                description=item.get("description"),
                group=item.get("group") or doc_group or None,
                enabled=item.get("enabled", True),
            )
            db.add(p)
            created += 1
        db.commit()
        return {"message": "导入完成", "created": created}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}")
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"XML 解析失败: {e}")


@router.get("/compliance/policies/export")
def export_compliance_policies(
    ids: Optional[str] = Query(None, description="策略 id 逗号分隔，不传则导出全部"),
    db: Session = Depends(get_db),
):
    """导出策略为 JSON。"""
    q = db.query(ConfigCompliancePolicy)
    if ids and (id_list := [int(x.strip()) for x in ids.split(",") if x.strip()]):
        q = q.filter(ConfigCompliancePolicy.id.in_(id_list))
    rows = q.order_by(ConfigCompliancePolicy.id).all()
    data = {"policies": [r.to_dict() for r in rows]}
    return data


# ---------- 合规报告（报告为模板，不绑定设备；执行时指定目标）----------
def _report_to_item(db: Session, r: ConfigComplianceReport) -> dict:
    """报告项含 policy_ids、policy_count。"""
    d = r.to_dict()
    links = db.query(ConfigComplianceReportPolicy).filter(ConfigComplianceReportPolicy.report_id == r.id).order_by(ConfigComplianceReportPolicy.sort_order, ConfigComplianceReportPolicy.id).all()
    d["policy_ids"] = [x.policy_id for x in links]
    d["policy_count"] = len(links)
    return d


@router.get("/compliance/reports")
def list_compliance_reports(
    group: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """报告列表；支持按 group 筛选。"""
    q = db.query(ConfigComplianceReport)
    if group is not None and (group := (group or "").strip()):
        q = q.filter(ConfigComplianceReport.group == group)
    total = q.count()
    rows = q.order_by(ConfigComplianceReport.updated_at.desc()).offset(skip).limit(limit).all()
    return {"items": [_report_to_item(db, r) for r in rows], "total": total}


@router.get("/compliance/reports/{report_id}")
def get_compliance_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """报告详情，含关联策略列表。"""
    r = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_item(db, r)


def _set_report_policies(db: Session, report_id: int, policy_ids: Optional[List[int]]) -> None:
    """覆盖报告的关联策略（policy_ids 为 None 则不修改）。"""
    if policy_ids is None:
        return
    db.query(ConfigComplianceReportPolicy).filter(ConfigComplianceReportPolicy.report_id == report_id).delete()
    for i, pid in enumerate(policy_ids or []):
        db.add(ConfigComplianceReportPolicy(report_id=report_id, policy_id=pid, sort_order=i))
    db.flush()


@router.post("/compliance/reports", status_code=201)
def create_compliance_report(
    body: ComplianceReportCreate,
    db: Session = Depends(get_db),
):
    """创建报告。"""
    r = ConfigComplianceReport(
        name=body.name,
        group=body.group,
        comments=body.comments,
        device_type=body.device_type,
        enabled=body.enabled if body.enabled is not None else True,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    _set_report_policies(db, r.id, body.policy_ids)
    db.commit()
    return _report_to_item(db, r)


@router.put("/compliance/reports/{report_id}")
def update_compliance_report(
    report_id: int,
    body: ComplianceReportUpdate,
    db: Session = Depends(get_db),
):
    """更新报告。"""
    r = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    if body.name is not None:
        r.name = body.name
    if body.group is not None:
        r.group = body.group
    if body.comments is not None:
        r.comments = body.comments
    if body.device_type is not None:
        r.device_type = body.device_type
    if body.enabled is not None:
        r.enabled = body.enabled
    _set_report_policies(db, r.id, body.policy_ids)
    db.commit()
    db.refresh(r)
    return _report_to_item(db, r)


@router.patch("/compliance/reports/{report_id}/enabled")
def update_compliance_report_enabled(
    report_id: int,
    body: ComplianceReportEnabledUpdate,
    db: Session = Depends(get_db),
):
    """启用/禁用报告。"""
    r = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    r.enabled = body.enabled
    db.commit()
    db.refresh(r)
    return _report_to_item(db, r)


@router.delete("/compliance/reports/{report_id}", status_code=204)
def delete_compliance_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """删除报告及报告-策略关联，不删除策略本身。"""
    r = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    db.query(ConfigComplianceReportPolicy).filter(ConfigComplianceReportPolicy.report_id == report_id).delete()
    db.delete(r)
    db.commit()
    return None


@router.get("/compliance/reports/{report_id}/export")
def export_compliance_report_xml(
    report_id: int,
    db: Session = Depends(get_db),
):
    """导出报告为 XML（含关联策略）。"""
    r = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    links = db.query(ConfigComplianceReportPolicy).filter(ConfigComplianceReportPolicy.report_id == report_id).order_by(ConfigComplianceReportPolicy.sort_order).all()
    policy_ids = [x.policy_id for x in links]
    policies = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id.in_(policy_ids)).all() if policy_ids else []
    root = ET.Element("PolicyReport")
    root.set("name", r.name or "")
    root.set("group", r.group or "")
    root.set("device_type", r.device_type or "")
    root.set("enabled", "true" if r.enabled else "false")
    comm = ET.SubElement(root, "Comments")
    comm.text = (r.comments or "").strip()
    assn = ET.SubElement(root, "AssignedPolicies")
    for p in policies:
        pol = ET.SubElement(assn, "Policy")
        pol.set("name", p.name or "")
        pol.set("rule_type", p.rule_type or "")
        pol.set("rule_content", (p.rule_content or "")[:500])
        pol.set("device_type", p.device_type or "")
    xml_str = ET.tostring(root, encoding="unicode", default_namespace="")
    return {"xml": xml_str, "filename": f"report_{report_id}_{r.name or 'export'}.xml"}


def _parse_report_policies_from_root(root) -> List[Tuple[str, str, str, Optional[str]]]:
    """从已解析的 report 根节点解析出策略列表：(name, rule_type, rule_content, device_type)。支持属性式 Policy 与 NCM 风格 AssignedPolicyRules/PolicyRule。"""
    assn = _find_el(root, "AssignedPolicies", "AssignedPolicy")
    if assn is None:
        return []
    out: List[Tuple[str, str, str, Optional[str]]] = []
    for pol in _findall_el(assn, "Policy"):
        rcontent = pol.get("rule_content") or pol.get("RuleContent") or pol.get("SimplePatternText") or ""
        if rcontent:
            out.append((
                pol.get("name") or pol.get("Name") or "策略",
                pol.get("rule_type") or pol.get("RuleType") or "must_contain",
                rcontent,
                pol.get("device_type") or pol.get("DeviceType"),
            ))
            continue
        rules_el = _find_el(pol, "AssignedPolicyRules")
        if rules_el is None:
            continue
        for rule in _findall_el(rules_el, "PolicyRule"):
            simple_text = _text(_find_el(rule, "SimplePatternText"))
            if not simple_text:
                continue
            rule_name = _text(_find_el(rule, "RuleName")) or simple_text[:50]
            pattern_type = (_text(_find_el(rule, "PatternType")) or "").lower()
            rule_type = "regex" if "regex" in pattern_type else "must_contain"
            out.append((rule_name, rule_type, simple_text, None))
    return out


@router.post("/compliance/reports/import")
def import_compliance_report_xml(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """从 XML 导入报告（规则集）及策略（创建新策略并关联）。支持本系统导出格式与 NCM 风格（PolicyReport + AssignedPolicyRules/PolicyRule）。"""
    try:
        content = file.file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        root = ET.fromstring(content)
        name = root.get("name") or root.get("Name") or _text(_find_el(root, "Name")) or "导入报告"
        group = root.get("group") or root.get("Group") or _text(_find_el(root, "Group")) or ""
        device_type = root.get("device_type") or root.get("DeviceType") or _text(_find_el(root, "DeviceType")) or ""
        enabled_val = root.get("enabled") or _text(_find_el(root, "ReportStatus")) or "true"
        enabled = enabled_val.lower() == "true" or enabled_val.lower() == "enabled"
        comments_el = _find_el(root, "Comments")
        comments = _text(comments_el) or ""
        r = ConfigComplianceReport(name=name, group=group or None, comments=comments or None, device_type=device_type or None, enabled=enabled)
        db.add(r)
        db.flush()
        policy_ids = []
        for pname, rtype, rcontent, pdevice in _parse_report_policies_from_root(root):
            p = ConfigCompliancePolicy(name=pname, rule_type=rtype, rule_content=rcontent, device_type=pdevice, enabled=True)
            db.add(p)
            db.flush()
            policy_ids.append(p.id)
        for i, pid in enumerate(policy_ids):
            db.add(ConfigComplianceReportPolicy(report_id=r.id, policy_id=pid, sort_order=i))
        db.commit()
        db.refresh(r)
        return _report_to_item(db, r)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"XML 解析失败: {e}")


def _run_policy_on_content(policy: ConfigCompliancePolicy, content: str) -> Tuple[bool, str]:
    """对配置内容执行单条策略，返回 (passed, detail)。"""
    text = content or ""
    rule = (policy.rule_content or "").strip()
    if policy.rule_type == "must_contain":
        passed = rule in text
        return passed, "包含" if passed else "未包含"
    if policy.rule_type == "must_not_contain":
        passed = rule not in text
        return passed, "未包含(通过)" if passed else "包含(不通过)"
    if policy.rule_type == "regex":
        try:
            m = re.search(rule, text, re.MULTILINE | re.DOTALL)
            passed = m is not None
            return passed, m.group(0)[:200] if m else "未匹配"
        except re.error:
            return False, "正则表达式错误"
    return False, "未知规则类型"


def _resolve_backups_for_run(
    db: Session,
    backup_id: Optional[int],
    device_id: Optional[str],
    device_ids: Optional[List[str]],
    report_id: Optional[int],
    target_by_device_type: Optional[bool],
    request_policy_ids: Optional[List[int]],
) -> Tuple[List[ConfigModuleBackup], Optional[ConfigComplianceReport], List[ConfigCompliancePolicy], Optional[int]]:
    """
    解析执行目标与策略。返回 (backups, report_or_none, policies, report_id_for_result)。
    若按报告执行且 target_by_device_type=True，则根据报告 device_type 解析设备列表并取最新备份。
    """
    report: Optional[ConfigComplianceReport] = None
    report_id_for_result: Optional[int] = None
    policies: List[ConfigCompliancePolicy] = []
    backups: List[ConfigModuleBackup] = []

    if report_id:
        report = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        report_id_for_result = report.id
        link_rows = (
            db.query(ConfigComplianceReportPolicy)
            .filter(ConfigComplianceReportPolicy.report_id == report_id)
            .order_by(ConfigComplianceReportPolicy.sort_order, ConfigComplianceReportPolicy.id)
            .all()
        )
        policy_ids_from_report = [x.policy_id for x in link_rows]
        if policy_ids_from_report:
            policies = db.query(ConfigCompliancePolicy).filter(
                ConfigCompliancePolicy.id.in_(policy_ids_from_report),
                ConfigCompliancePolicy.enabled == True,
            ).all()
            pid_order = {pid: i for i, pid in enumerate(policy_ids_from_report)}
            policies.sort(key=lambda p: pid_order.get(p.id, 999))

    if report_id and report and not report.enabled:
        raise HTTPException(status_code=400, detail="报告未启用，无法执行")

    if target_by_device_type and report and report.device_type:
        device_keys = _get_backup_devices_filtered_by_device_type(db, report.device_type)
        for dh, did in device_keys:
            if dh and (dh := (dh or "").strip()):
                b = (
                    db.query(ConfigModuleBackup)
                    .filter(ConfigModuleBackup.device_host == dh)
                    .order_by(ConfigModuleBackup.created_at.desc())
                    .first()
                )
            else:
                b = (
                    db.query(ConfigModuleBackup)
                    .filter(ConfigModuleBackup.device_id == did)
                    .order_by(ConfigModuleBackup.created_at.desc())
                    .first()
                )
            if b:
                backups.append(b)
        if report_id and not policies:
            raise HTTPException(status_code=400, detail="报告下无策略")
        return backups, report, policies, report_id_for_result

    if device_ids:
        for did in device_ids:
            if not (did := (did or "").strip()):
                continue
            b = (
                db.query(ConfigModuleBackup)
                .filter(ConfigModuleBackup.device_id == did)
                .order_by(ConfigModuleBackup.created_at.desc())
                .first()
            )
            if b:
                backups.append(b)
        if not backups:
            raise HTTPException(status_code=404, detail="未找到指定设备的备份")
        if report_id and not policies:
            raise HTTPException(status_code=400, detail="报告下无策略")
        if not policies and request_policy_ids:
            policies = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id.in_(request_policy_ids)).all()
        if not policies:
            policies = db.query(ConfigCompliancePolicy).all()
        return backups, report, policies, report_id_for_result

    if backup_id:
        backup = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.id == backup_id).first()
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        backups = [backup]
    elif device_id:
        backup = (
            db.query(ConfigModuleBackup)
            .filter(ConfigModuleBackup.device_id == device_id)
            .order_by(ConfigModuleBackup.created_at.desc())
            .first()
        )
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")
        backups = [backup]
    else:
        if report_id:
            raise HTTPException(status_code=400, detail="按报告执行须指定目标：target_by_device_type 或 backup_id/device_id/device_ids")
        raise HTTPException(status_code=400, detail="请指定 backup_id、device_id 或 device_ids")

    if not policies and request_policy_ids:
        policies = db.query(ConfigCompliancePolicy).filter(ConfigCompliancePolicy.id.in_(request_policy_ids)).all()
    if not policies:
        policies = db.query(ConfigCompliancePolicy).all()
    return backups, report, policies, report_id_for_result


@router.post("/compliance/run")
def run_compliance(
    body: ComplianceRunRequest,
    db: Session = Depends(get_db),
):
    """对指定 backup_id/device_id/device_ids 或按报告+目标执行策略，写入结果。不传 report_id 时行为与原有一致。"""
    backups, _report, policies, report_id_for_result = _resolve_backups_for_run(
        db,
        body.backup_id,
        body.device_id,
        body.device_ids,
        body.report_id,
        body.target_by_device_type,
        body.policy_ids,
    )
    if not policies:
        return {"message": "无策略可执行", "results": [], "device_count": 0}
    results = []
    for backup in backups:
        for p in policies:
            passed, detail = _run_policy_on_content(p, backup.content or "")
            r = ConfigComplianceResult(
                policy_id=p.id,
                backup_id=backup.id,
                device_id=backup.device_id,
                report_id=report_id_for_result,
                passed=passed,
                detail=detail,
            )
            db.add(r)
            results.append({"policy_id": p.id, "policy_name": p.name, "passed": passed, "detail": detail})
    db.commit()
    return {
        "message": "执行完成",
        "results": results,
        "device_count": len(backups),
        "report_id": report_id_for_result,
    }


@router.get("/compliance/results")
def list_compliance_results(
    device_id: Optional[str] = Query(None),
    policy_id: Optional[int] = Query(None),
    passed: Optional[bool] = Query(None),
    report_id: Optional[int] = Query(None),
    executed_at_from: Optional[str] = Query(None, description="执行时间起 YYYY-MM-DD"),
    executed_at_to: Optional[str] = Query(None, description="执行时间止 YYYY-MM-DD"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """结果列表；可选按 report_id、时间范围等筛选。"""
    q = db.query(ConfigComplianceResult)
    if device_id:
        q = q.filter(ConfigComplianceResult.device_id == device_id)
    if policy_id is not None:
        q = q.filter(ConfigComplianceResult.policy_id == policy_id)
    if passed is not None:
        q = q.filter(ConfigComplianceResult.passed == passed)
    if report_id is not None:
        q = q.filter(ConfigComplianceResult.report_id == report_id)
    if executed_at_from:
        q = q.filter(ConfigComplianceResult.executed_at >= executed_at_from)
    if executed_at_to:
        q = q.filter(ConfigComplianceResult.executed_at <= executed_at_to + " 23:59:59")
    total = q.count()
    rows = q.order_by(ConfigComplianceResult.executed_at.desc()).offset(skip).limit(limit).all()
    return {"items": [r.to_dict() for r in rows], "total": total}


@router.delete("/compliance/results/{result_id}", status_code=204)
def delete_compliance_result(
    result_id: int,
    db: Session = Depends(get_db),
):
    """删除单条结果。"""
    r = db.query(ConfigComplianceResult).filter(ConfigComplianceResult.id == result_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Result not found")
    db.delete(r)
    db.commit()
    return None


@router.post("/compliance/results/batch-delete")
def batch_delete_compliance_results(
    body: ComplianceResultBatchDelete,
    db: Session = Depends(get_db),
):
    """批量删除结果。"""
    if not body.ids:
        return {"deleted": 0}
    deleted = db.query(ConfigComplianceResult).filter(ConfigComplianceResult.id.in_(body.ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}


@router.get("/compliance/results/export")
def export_compliance_results(
    device_id: Optional[str] = Query(None),
    policy_id: Optional[int] = Query(None),
    passed: Optional[bool] = Query(None),
    report_id: Optional[int] = Query(None),
    limit: int = Query(5000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    """按筛选条件导出结果为 CSV。"""
    q = db.query(ConfigComplianceResult)
    if device_id:
        q = q.filter(ConfigComplianceResult.device_id == device_id)
    if policy_id is not None:
        q = q.filter(ConfigComplianceResult.policy_id == policy_id)
    if passed is not None:
        q = q.filter(ConfigComplianceResult.passed == passed)
    if report_id is not None:
        q = q.filter(ConfigComplianceResult.report_id == report_id)
    rows = q.order_by(ConfigComplianceResult.executed_at.desc()).limit(limit).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "policy_id", "backup_id", "device_id", "report_id", "passed", "detail", "executed_at"])
    for r in rows:
        writer.writerow([r.id, r.policy_id, r.backup_id, r.device_id, r.report_id, r.passed, r.detail or "", utc_to_beijing_str(r.executed_at)])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=compliance_results.csv"})


# ---------- 合规执行计划 ----------
@router.get("/compliance/schedules")
def list_compliance_schedules(
    report_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(ConfigComplianceSchedule)
    if report_id is not None:
        q = q.filter(ConfigComplianceSchedule.report_id == report_id)
    total = q.count()
    rows = q.order_by(ConfigComplianceSchedule.updated_at.desc()).offset(skip).limit(limit).all()
    return {"items": [r.to_dict() for r in rows], "total": total}


@router.get("/compliance/schedules/{schedule_id}")
def get_compliance_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    s = db.query(ConfigComplianceSchedule).filter(ConfigComplianceSchedule.id == schedule_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return s.to_dict()


@router.post("/compliance/schedules", status_code=201)
def create_compliance_schedule(
    body: ComplianceScheduleCreate,
    db: Session = Depends(get_db),
):
    report = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == body.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    target_ids_json = json.dumps(body.target_device_ids) if body.target_device_ids else None
    s = ConfigComplianceSchedule(
        name=body.name,
        report_id=body.report_id,
        target_type=body.target_type,
        target_device_ids=target_ids_json,
        cron_expr=body.cron_expr,
        interval_seconds=body.interval_seconds,
        enabled=body.enabled if body.enabled is not None else True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.put("/compliance/schedules/{schedule_id}")
def update_compliance_schedule(
    schedule_id: int,
    body: ComplianceScheduleUpdate,
    db: Session = Depends(get_db),
):
    s = db.query(ConfigComplianceSchedule).filter(ConfigComplianceSchedule.id == schedule_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if body.name is not None:
        s.name = body.name
    if body.target_type is not None:
        s.target_type = body.target_type
    if body.target_device_ids is not None:
        s.target_device_ids = json.dumps(body.target_device_ids)
    if body.cron_expr is not None:
        s.cron_expr = body.cron_expr
    if body.interval_seconds is not None:
        s.interval_seconds = body.interval_seconds
    if body.enabled is not None:
        s.enabled = body.enabled
    db.commit()
    db.refresh(s)
    return s.to_dict()


@router.delete("/compliance/schedules/{schedule_id}", status_code=204)
def delete_compliance_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    s = db.query(ConfigComplianceSchedule).filter(ConfigComplianceSchedule.id == schedule_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(s)
    db.commit()
    return None


@router.post("/compliance/schedules/{schedule_id}/run")
def run_compliance_schedule_now(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """立即执行一次该计划（按报告+目标执行，更新 last_run_at）。"""
    s = db.query(ConfigComplianceSchedule).filter(ConfigComplianceSchedule.id == schedule_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found")
    report = db.query(ConfigComplianceReport).filter(ConfigComplianceReport.id == s.report_id).first()
    if not report or not report.enabled:
        raise HTTPException(status_code=400, detail="报告不存在或未启用")
    device_ids = json.loads(s.target_device_ids) if s.target_device_ids else None
    target_by_device_type = s.target_type == "by_device_type"
    backups, _, policies, report_id_for_result = _resolve_backups_for_run(
        db, None, None, device_ids, s.report_id, target_by_device_type, None
    )
    if not policies:
        return {"message": "报告下无策略", "device_count": 0}
    for backup in backups:
        for p in policies:
            passed, detail = _run_policy_on_content(p, backup.content or "")
            db.add(ConfigComplianceResult(
                policy_id=p.id, backup_id=backup.id, device_id=backup.device_id,
                report_id=report_id_for_result, passed=passed, detail=detail,
            ))
    s.last_run_at = datetime.utcnow()
    db.commit()
    return {"message": "执行完成", "device_count": len(backups)}


# ---------- 服务终止 ----------
@router.get("/eos")
def list_eos(
    status: Optional[str] = Query(None, description="upcoming / passed 即将EOS / 已EOS"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(ConfigEosInfo)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if status == "upcoming":
        q = q.filter(ConfigEosInfo.eos_date >= today)
    elif status == "passed":
        q = q.filter(ConfigEosInfo.eos_date < today)
    total = q.count()
    rows = q.order_by(ConfigEosInfo.eos_date.asc()).offset(skip).limit(limit).all()
    return {"items": [r.to_dict() for r in rows], "total": total}


@router.get("/eos/{eos_id}")
def get_eos(
    eos_id: int,
    db: Session = Depends(get_db),
):
    e = db.query(ConfigEosInfo).filter(ConfigEosInfo.id == eos_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="EOS info not found")
    return e.to_dict()


@router.post("/eos", status_code=201)
def create_eos(
    body: EosInfoCreate,
    db: Session = Depends(get_db),
):
    e = ConfigEosInfo(
        device_or_model=body.device_or_model,
        eos_date=body.eos_date,
        description=body.description,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.put("/eos/{eos_id}")
def update_eos(
    eos_id: int,
    body: EosInfoUpdate,
    db: Session = Depends(get_db),
):
    e = db.query(ConfigEosInfo).filter(ConfigEosInfo.id == eos_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="EOS info not found")
    if body.device_or_model is not None:
        e.device_or_model = body.device_or_model
    if body.eos_date is not None:
        e.eos_date = body.eos_date
    if body.description is not None:
        e.description = body.description
    db.commit()
    db.refresh(e)
    return e.to_dict()


@router.delete("/eos/{eos_id}", status_code=204)
def delete_eos(
    eos_id: int,
    db: Session = Depends(get_db),
):
    e = db.query(ConfigEosInfo).filter(ConfigEosInfo.id == eos_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="EOS info not found")
    db.delete(e)
    db.commit()
    return None
