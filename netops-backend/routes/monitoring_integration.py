# 监控系统集成：Webhook 管理 + 告警接收 + 告警列表/详情
# 设计见 docs/监控系统集成_设计说明.md

import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import Response
from sqlalchemy import func
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import MonitoringWebhook, MonitoringAlertEvent
from auth.authentication import get_current_active_user
from database.models import User

router = APIRouter(prefix="/api/monitoring-integration", tags=["监控系统集成"])


# ---------- Schemas ----------
class WebhookCreate(BaseModel):
    name: str
    remark: Optional[str] = None


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    remark: Optional[str] = None
    enabled: Optional[bool] = None


def _color_to_severity(color: Optional[str]) -> str:
    if not color:
        return "info"
    c = (color or "").upper()
    if "#FF0000" in c or "RED" in c:
        return "critical"
    if "#FF8C00" in c or "#FFA500" in c or "ORANGE" in c:
        return "warning"
    if "#FFD700" in c or "YELLOW" in c:
        return "warning"
    return "info"


def _parse_entity_interface(fallback: Optional[str]) -> Optional[str]:
    """从 fallback 解析：'流量告警: A - B' -> 'A - B'"""
    if not fallback or not isinstance(fallback, str):
        return None
    m = re.match(r"流量告警[：:]\s*(.+)", fallback.strip())
    return m.group(1).strip() if m else None


def _parse_node_interface(entity_interface: Optional[str]) -> tuple:
    """从 entity_interface 解析节点与接口，支持多种分隔符：' - '、' | '、','，得到 (节点/IP/主机名, 接口名)"""
    if not entity_interface:
        return (None, None)
    s = entity_interface.strip()
    for sep in (" - ", " | ", ","):
        if sep in s:
            parts = s.split(sep, 1)
            a = parts[0].strip() or None
            b = parts[1].strip() if len(parts) > 1 else None
            if b:
                return (a, b)
            return (a, None)
    return (s or None, None)


def _simplify_alert_title(pretext: str) -> Optional[str]:
    """根据文档 JSON 精简标题：去掉首尾星号、空格及括号及括号内内容"""
    if not pretext or not isinstance(pretext, str):
        return None
    s = re.sub(r"^\s*\*+\s*|\s*\*+\s*$", "", pretext).strip()  # 去掉首尾星号（多个）
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()  # 去掉末尾 (xxx)
    return s or None


def _parse_solarwinds_payload(body: dict) -> dict:
    """按设计说明 4.3 解析 SolarWinds JSON -> 告警字段"""
    att = (body.get("attachments") or [{}])[0] if isinstance(body.get("attachments"), list) else {}
    if not att:
        att = body
    pretext = att.get("pretext") or att.get("pre_text") or ""
    fallback = att.get("fallback") or att.get("message") or ""
    color = att.get("color")
    alert_title = _simplify_alert_title(pretext)
    message = fallback if isinstance(fallback, str) else (json.dumps(fallback) if fallback else None)
    entity_interface = _parse_entity_interface(message)
    node_ip, interface_name = _parse_node_interface(entity_interface)
    severity = _color_to_severity(color)
    metadata = {}
    if node_ip is not None:
        metadata["node_ip"] = node_ip
    if interface_name is not None:
        metadata["interface_name"] = interface_name
    return {
        "alert_title": alert_title,
        "message": message,
        "color": color if isinstance(color, str) else None,
        "entity_interface": entity_interface,
        "node_ip": node_ip,
        "interface_name": interface_name,
        "metadata_json": json.dumps(metadata) if metadata else None,
        "severity": severity,
        "status": body.get("status") or "triggered",
    }


# ---------- Webhook 管理（需登录） ----------
@router.post("/webhooks")
def create_webhook(
    payload: WebhookCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建 Webhook，生成唯一 URL（无 token）"""
    path_slug = uuid.uuid4().hex
    wh = MonitoringWebhook(
        name=payload.name,
        path_slug=path_slug,
        enabled=True,
        remark=payload.remark,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    base = str(request.base_url).rstrip("/")
    url = f"{base}/api/monitoring-integration/webhook/{wh.path_slug}"
    return {
        "id": wh.id,
        "name": wh.name,
        "path_slug": wh.path_slug,
        "enabled": wh.enabled,
        "remark": wh.remark,
        "created_at": wh.created_at.isoformat() if wh.created_at else None,
        "webhook_url": url,
    }


@router.get("/webhooks")
def list_webhooks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Webhook 列表，含完整 URL"""
    base = str(request.base_url).rstrip("/")
    rows = db.query(MonitoringWebhook).order_by(MonitoringWebhook.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "path_slug": r.path_slug,
            "enabled": r.enabled,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "webhook_url": f"{base}/api/monitoring-integration/webhook/{r.path_slug}",
        }
        for r in rows
    ]


@router.get("/webhooks/{webhook_id}")
def get_webhook(
    webhook_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """单条 Webhook 详情（id 为数字主键）"""
    wh = db.query(MonitoringWebhook).filter(MonitoringWebhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    base = str(request.base_url).rstrip("/")
    return {
        "id": wh.id,
        "name": wh.name,
        "path_slug": wh.path_slug,
        "enabled": wh.enabled,
        "remark": wh.remark,
        "created_at": wh.created_at.isoformat() if wh.created_at else None,
        "webhook_url": f"{base}/api/monitoring-integration/webhook/{wh.path_slug}",
    }


@router.patch("/webhooks/{webhook_id}")
def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新名称、备注、启用/禁用"""
    wh = db.query(MonitoringWebhook).filter(MonitoringWebhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if payload.name is not None:
        wh.name = payload.name
    if payload.remark is not None:
        wh.remark = payload.remark
    if payload.enabled is not None:
        wh.enabled = payload.enabled
    db.commit()
    db.refresh(wh)
    return {"id": wh.id, "name": wh.name, "enabled": wh.enabled, "remark": wh.remark}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除 Webhook（该 URL 不再接收，历史告警保留）"""
    wh = db.query(MonitoringWebhook).filter(MonitoringWebhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(wh)
    db.commit()
    return {"detail": "deleted"}


# ---------- 接收告警（无需登录，不校验 token） ----------
@router.post("/webhook/{webhook_id}")
async def receive_webhook(webhook_id: str, request: Request, db: Session = Depends(get_db)):
    """接收 SolarWinds POST 的告警 JSON；仅校验 webhook_id 存在且 enabled"""
    wh = db.query(MonitoringWebhook).filter(
        MonitoringWebhook.path_slug == webhook_id,
        MonitoringWebhook.enabled == True,
    ).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found or disabled")
    try:
        body = await request.json()
    except Exception:
        try:
            raw = await request.body()
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}
    if not isinstance(body, dict):
        body = {}
    raw_payload = json.dumps(body, ensure_ascii=False)
    now = datetime.utcnow()
    parsed = _parse_solarwinds_payload(body)
    evt = MonitoringAlertEvent(
        webhook_id=webhook_id,
        source="solarwinds",
        alert_title=parsed.get("alert_title"),
        message=parsed.get("message"),
        color=parsed.get("color"),
        entity_interface=parsed.get("entity_interface"),
        severity=parsed.get("severity"),
        status=parsed.get("status", "triggered"),
        raw_payload=raw_payload,
        triggered_at=now,
        created_at=now,
        metadata_=parsed.get("metadata_json"),
    )
    db.add(evt)
    db.commit()
    return {"status": "ok", "id": evt.id}


# ---------- 告警列表与详情（需登录） ----------
@router.get("/alerts")
def list_alerts(
    source: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """告警列表，分页与筛选"""
    q = db.query(MonitoringAlertEvent)
    if source:
        q = q.filter(MonitoringAlertEvent.source == source)
    if severity:
        q = q.filter(MonitoringAlertEvent.severity == severity)
    if status:
        q = q.filter(MonitoringAlertEvent.status == status)
    if keyword:
        k = f"%{keyword}%"
        q = q.filter(
            (MonitoringAlertEvent.alert_title.ilike(k))
            | (MonitoringAlertEvent.message.ilike(k))
            | (MonitoringAlertEvent.entity_interface.ilike(k))
        )
    total = q.count()
    rows = q.order_by(MonitoringAlertEvent.created_at.desc()).offset(skip).limit(limit).all()
    items = []
    for r in rows:
        meta = {}
        if getattr(r, "metadata_", None):
            try:
                meta = json.loads(r.metadata_) or {}
            except Exception:
                pass
        node_ip = meta.get("node_ip")
        interface_name = meta.get("interface_name")
        # 老数据无 metadata 时从 entity_interface 解析或整段回填，保证节点信息有展示
        if (node_ip is None or interface_name is None) and r.entity_interface:
            ni, iface = _parse_node_interface(r.entity_interface)
            if node_ip is None:
                node_ip = ni or r.entity_interface
            if interface_name is None:
                interface_name = iface
        alert_time = r.triggered_at or r.created_at
        items.append({
            "id": r.id,
            "webhook_id": r.webhook_id,
            "source": r.source,
            "alert_title": r.alert_title,
            "message": r.message,
            "color": r.color,
            "entity_interface": r.entity_interface,
            "node_ip": node_ip,
            "interface_name": interface_name,
            "severity": r.severity,
            "status": r.status,
            "alert_time": alert_time.isoformat() if alert_time else None,
            "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"total": total, "items": items}


def _alert_row_to_dict(r: MonitoringAlertEvent) -> dict:
    """将告警行转为与详情接口一致的字典（含 node_ip/interface_name/alert_time/raw_payload）"""
    meta = {}
    if getattr(r, "metadata_", None):
        try:
            meta = json.loads(r.metadata_) or {}
        except Exception:
            pass
    node_ip = meta.get("node_ip")
    interface_name = meta.get("interface_name")
    if (node_ip is None or interface_name is None) and r.entity_interface:
        ni, iface = _parse_node_interface(r.entity_interface)
        if node_ip is None:
            node_ip = ni or r.entity_interface
        if interface_name is None:
            interface_name = iface
    alert_time = r.triggered_at or r.created_at
    return {
        "id": r.id,
        "webhook_id": r.webhook_id,
        "source": r.source,
        "alert_title": r.alert_title,
        "message": r.message,
        "color": r.color,
        "entity_interface": r.entity_interface,
        "node_ip": node_ip,
        "interface_name": interface_name,
        "severity": r.severity,
        "status": r.status,
        "raw_payload": r.raw_payload,
        "alert_time": alert_time.isoformat() if alert_time else None,
        "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "metadata": getattr(r, "metadata_", None),
    }


@router.get("/alerts/{alert_id}")
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """告警详情（含 raw_payload）"""
    r = db.query(MonitoringAlertEvent).filter(MonitoringAlertEvent.id == alert_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_row_to_dict(r)


# ---------- 事件归档：按告警时间导出 / 按天数删除 ----------
def _archive_cutoff(days: int) -> datetime:
    """归档截止时间：当前时间往前 days 天（UTC）"""
    return datetime.utcnow() - timedelta(days=days)


@router.get("/alerts/archive/count")
def archive_count(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """统计告警时间早于 N 天前的记录数（用于归档预览）"""
    cutoff = _archive_cutoff(days)
    q = db.query(MonitoringAlertEvent).filter(
        func.coalesce(MonitoringAlertEvent.triggered_at, MonitoringAlertEvent.created_at) < cutoff
    )
    return {"count": q.count()}


@router.get("/alerts/archive/export")
def archive_export(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """导出告警时间早于 N 天前的记录为 JSON 文件（不删除，仅导出）"""
    cutoff = _archive_cutoff(days)
    rows = db.query(MonitoringAlertEvent).filter(
        func.coalesce(MonitoringAlertEvent.triggered_at, MonitoringAlertEvent.created_at) < cutoff
    ).order_by(MonitoringAlertEvent.created_at.asc()).all()
    items = [_alert_row_to_dict(r) for r in rows]
    filename = f"alerts_archive_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    body = json.dumps({"days": days, "cutoff": cutoff.isoformat(), "count": len(items), "items": items}, ensure_ascii=False, indent=2)
    return Response(
        content=body.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/alerts/archive/delete-by-days")
def archive_delete_by_days(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """按告警时间删除早于 N 天前的记录（默认 90 天）"""
    d = days
    cutoff = _archive_cutoff(d)
    q = db.query(MonitoringAlertEvent).filter(
        func.coalesce(MonitoringAlertEvent.triggered_at, MonitoringAlertEvent.created_at) < cutoff
    )
    deleted = q.delete()
    db.commit()
    return {"deleted": deleted}


@router.post("/alerts/clear")
def alerts_clear(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """清空全部告警事件（不可恢复）"""
    deleted = db.query(MonitoringAlertEvent).delete()
    db.commit()
    return {"deleted": deleted}
