# 配置管理模块 API：设备配置备份、配置摘要、变更模板、合规、服务终止（不修改其它功能）
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import difflib
import re
import logging

from database.session import get_db
from database.config_module_models import (
    ConfigModuleBackup,
    ConfigChangeTemplate,
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
    ChangeTemplateCreate,
    ChangeTemplateUpdate,
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
    """写入一条备份（流程节点/API 调用）。"""
    b = ConfigModuleBackup(
        device_id=body.device_id,
        device_name=body.device_name,
        device_host=body.device_host,
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


# ---------- 配置变更模板 ----------
@router.get("/change-templates")
def list_change_templates(
    device_type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None, description="标签关键词"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(ConfigChangeTemplate)
    if device_type:
        q = q.filter(ConfigChangeTemplate.device_type == device_type)
    if tag:
        q = q.filter(ConfigChangeTemplate.tags.ilike(f"%{tag}%"))
    total = q.count()
    rows = q.order_by(ConfigChangeTemplate.updated_at.desc()).offset(skip).limit(limit).all()
    return {"items": [r.to_dict(include_content=True) for r in rows], "total": total}


@router.get("/change-templates/{template_id}")
def get_change_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    t = db.query(ConfigChangeTemplate).filter(ConfigChangeTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Change template not found")
    return t.to_dict(include_content=True)


@router.post("/change-templates", status_code=201)
def create_change_template(
    body: ChangeTemplateCreate,
    db: Session = Depends(get_db),
):
    t = ConfigChangeTemplate(
        name=body.name,
        device_type=body.device_type,
        content=body.content,
        tags=body.tags,
        description=body.description,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t.to_dict(include_content=True)


@router.put("/change-templates/{template_id}")
def update_change_template(
    template_id: int,
    body: ChangeTemplateUpdate,
    db: Session = Depends(get_db),
):
    t = db.query(ConfigChangeTemplate).filter(ConfigChangeTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Change template not found")
    if body.name is not None:
        t.name = body.name
    if body.device_type is not None:
        t.device_type = body.device_type
    if body.content is not None:
        t.content = body.content
    if body.tags is not None:
        t.tags = body.tags
    if body.description is not None:
        t.description = body.description
    db.commit()
    db.refresh(t)
    return t.to_dict(include_content=True)


@router.delete("/change-templates/{template_id}", status_code=204)
def delete_change_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    t = db.query(ConfigChangeTemplate).filter(ConfigChangeTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Change template not found")
    db.delete(t)
    db.commit()
    return None


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
