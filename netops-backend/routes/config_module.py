# 配置管理模块 API：设备配置备份、配置摘要、变更模板、合规、服务终止（不修改其它功能）
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import difflib
import re
import logging

from database.session import get_db
from database.cmdb_models import Asset as AssetModel
from utils.datetime_utils import utc_to_beijing_str
from database.config_module_models import (
    ConfigModuleBackup,
    ConfigCompliancePolicy,
    ConfigComplianceResult,
    ConfigEosInfo,
)
from schemas.config_module import (
    BackupCreate,
    BackupResponse,
    BackupListResponse,
    DiffResponse,
    SummaryStatsResponse,
    CompliancePolicyCreate,
    CompliancePolicyUpdate,
    ComplianceRunRequest,
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
    """根据 device_host 查 CMDB，为 result 中每项补充 cmdb_name、cmdb_model、cmdb_vendor。"""
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
                    cmdb_map[ip] = {
                        "cmdb_name": a.name,
                        "cmdb_model": nd.device_model if nd else None,
                        "cmdb_vendor": vendor_name,
                    }
            for x in result:
                host = (x.get("device_host") or "").strip()
                if host and host in cmdb_map:
                    x.update(cmdb_map[host])
        finally:
            cmdb_db.close()
    except Exception as e:
        logger.warning("CMDB 查询失败，设备列表不补充 CMDB 信息: %s", e)


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
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(ConfigCompliancePolicy)
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
    db.commit()
    db.refresh(p)
    return p.to_dict()


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


@router.post("/compliance/run")
def run_compliance(
    body: ComplianceRunRequest,
    db: Session = Depends(get_db),
):
    """对指定 backup_id 或 device_id（取最新备份）执行策略，写入结果。"""
    backup = None
    if body.backup_id:
        backup = db.query(ConfigModuleBackup).filter(ConfigModuleBackup.id == body.backup_id).first()
    elif body.device_id:
        backup = (
            db.query(ConfigModuleBackup)
            .filter(ConfigModuleBackup.device_id == body.device_id)
            .order_by(ConfigModuleBackup.created_at.desc())
            .first()
        )
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    policies = db.query(ConfigCompliancePolicy)
    if body.policy_ids:
        policies = policies.filter(ConfigCompliancePolicy.id.in_(body.policy_ids))
    policies = policies.all()
    if not policies:
        return {"message": "无策略可执行", "results": []}
    results = []
    for p in policies:
        passed, detail = _run_policy_on_content(p, backup.content or "")
        r = ConfigComplianceResult(
            policy_id=p.id,
            backup_id=backup.id,
            device_id=backup.device_id,
            passed=passed,
            detail=detail,
        )
        db.add(r)
        results.append({"policy_id": p.id, "policy_name": p.name, "passed": passed, "detail": detail})
    db.commit()
    return {"message": "执行完成", "results": results}


@router.get("/compliance/results")
def list_compliance_results(
    device_id: Optional[str] = Query(None),
    policy_id: Optional[int] = Query(None),
    passed: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(ConfigComplianceResult)
    if device_id:
        q = q.filter(ConfigComplianceResult.device_id == device_id)
    if policy_id is not None:
        q = q.filter(ConfigComplianceResult.policy_id == policy_id)
    if passed is not None:
        q = q.filter(ConfigComplianceResult.passed == passed)
    total = q.count()
    rows = q.order_by(ConfigComplianceResult.executed_at.desc()).offset(skip).limit(limit).all()
    return {"items": [r.to_dict() for r in rows], "total": total}


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
