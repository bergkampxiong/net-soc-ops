# 监控系统集成：Webhook 管理 + 告警接收 + 告警列表/详情
# 设计见 docs/监控系统集成_设计说明.md

import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import Response
from sqlalchemy import func, or_
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
    s = re.sub(r"^\s*\*+\s*|\s*\*+\s*$", "", pretext).strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    return s or None


def _extract_alert_type_from_fallback(fallback: Optional[str]) -> Optional[str]:
    """从 fallback 提取告警类型：冒号前的中文部分，如 '流量告警: xxx' -> '流量告警'"""
    if not fallback or not isinstance(fallback, str):
        return None
    s = fallback.strip()
    if ":" in s:
        return s.split(":", 1)[0].strip() or None
    return s[:64] if s else None


# fields 中 title 到展示键的映射（文档 告警事件解析.md）
_FIELD_TITLE_TO_KEY = {
    "节点/设备": "node_name",
    "节点名称": "node_name",
    "设备名称": "node_name",
    "主机名称": "node_name",
    "机器名称": "node_name",
    "集群名称": "node_name",
    "IP 地址": "ip_address",
    "邻居 IP 地址": "ip_address",
    "接口名称": "interface_name",
    "接口": "interface_name",
    "当前使用率": "utilization",
    "发送利用率": "utilization",
    "当前利用率": "utilization",
    "内存利用率": "utilization",
    "当前已用百分比": "utilization",
    "当前使用百分比": "utilization",
    "磁盘分区": "disk",
    "LUN 名称": "disk",
    "存储名称": "disk",
    "作用域名称": "disk",
    "所在城市": "city",
}


def _fields_to_display_map(fields: List[dict]) -> dict:
    """从 fields 列表提取展示用键值（节点名称、IP、接口、利用率、磁盘、城市等）"""
    out = {}
    for f in fields or []:
        if not isinstance(f, dict):
            continue
        title = (f.get("title") or "").strip()
        value = f.get("value")
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)
        key = _FIELD_TITLE_TO_KEY.get(title)
        if key and value:
            # 同一 key 只保留第一个有值的（如多个利用率取第一个）
            if key not in out:
                out[key] = value
    return out


def _parse_solarwinds_payload(body: dict) -> dict:
    """按 docs/告警事件解析.md 解析：告警类型(fallback 冒号前)、fields 存储与展示映射"""
    att = (body.get("attachments") or [{}])[0] if isinstance(body.get("attachments"), list) else {}
    if not att:
        att = body
    pretext = att.get("pretext") or att.get("pre_text") or ""
    fallback = att.get("fallback") or att.get("message") or ""
    fallback = fallback if isinstance(fallback, str) else (json.dumps(fallback) if fallback else "")
    color = att.get("color")
    alert_title = _simplify_alert_title(pretext)
    message = fallback or None
    severity = _color_to_severity(color)

    # 1. 告警类型：fallback 中冒号前的中文部分
    alert_type = _extract_alert_type_from_fallback(fallback)

    # 2. fields 原始列表（SolarWinds 发送时已替换变量为实际值）
    raw_fields = att.get("fields")
    if not isinstance(raw_fields, list):
        raw_fields = []
    fields_for_storage = [{"title": f.get("title"), "value": f.get("value")} for f in raw_fields if isinstance(f, dict)]

    # 3. 从 fields 提取展示用：节点名称、IP、接口、利用率、磁盘、城市
    display_map = _fields_to_display_map(raw_fields)
    node_name = display_map.get("node_name")
    ip_address = display_map.get("ip_address")
    interface_name = display_map.get("interface_name")
    utilization = display_map.get("utilization")
    disk = display_map.get("disk")
    city = display_map.get("city")

    # 4. 兼容老逻辑：无 fields 时仍从 fallback 解析 entity_interface / node_ip / interface_name
    entity_interface = _parse_entity_interface(fallback)
    node_ip_legacy, interface_legacy = _parse_node_interface(entity_interface)
    if not node_name and (node_ip_legacy or entity_interface):
        node_name = node_ip_legacy or entity_interface
    if not interface_name and interface_legacy:
        interface_name = interface_legacy

    metadata = {
        "fields": fields_for_storage,
        "node_name": node_name,
        "ip_address": ip_address,
        "interface_name": interface_name,
        "utilization": utilization,
        "disk": disk,
        "city": city,
        "node_ip": node_ip_legacy or ip_address or node_name,  # 列表展示用
    }
    return {
        "alert_type": alert_type,
        "alert_title": alert_title,
        "message": message,
        "color": color if isinstance(color, str) else None,
        "entity_interface": entity_interface,
        "metadata_json": json.dumps(metadata, ensure_ascii=False),
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
        alert_type=parsed.get("alert_type"),
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
        keyword_conds = [
            MonitoringAlertEvent.alert_title.ilike(k),
            MonitoringAlertEvent.message.ilike(k),
            MonitoringAlertEvent.entity_interface.ilike(k),
        ]
        if hasattr(MonitoringAlertEvent, "alert_type"):
            keyword_conds.append(MonitoringAlertEvent.alert_type.ilike(k))
        q = q.filter(or_(*keyword_conds))
    total = q.count()
    rows = q.order_by(MonitoringAlertEvent.created_at.desc()).offset(skip).limit(limit).all()
    items = [_alert_row_to_list_item(r) for r in rows]
    return {"total": total, "items": items}


def _get_meta(r: MonitoringAlertEvent) -> dict:
    meta = {}
    if getattr(r, "metadata_", None):
        try:
            meta = json.loads(r.metadata_) or {}
        except Exception:
            pass
    return meta


def _display_value(v: Optional[str]) -> Optional[str]:
    """若为 SolarWinds 模板变量（如 ${N=SwisEntity;M=Node.Caption}），提取 M= 后的短名便于展示"""
    if not v or not isinstance(v, str):
        return v
    s = v.strip()
    if s.startswith("${") and ";M=" in s:
        m = re.search(r";M=([^};]+)", s)
        return m.group(1).strip() if m else v
    if s.startswith("${") and "}" in s:
        m = re.search(r"\$\{([^}]+)\}", s)
        return m.group(1).strip() if m else v
    return v


def _enrich_from_raw_payload(r: MonitoringAlertEvent) -> tuple:
    """当 metadata 为空或缺少展示字段时，从 raw_payload 重新解析并合并。返回 (meta, alert_type)。"""
    meta = _get_meta(r)
    alert_type = getattr(r, "alert_type", None)
    has_display = any(meta.get(k) for k in ("node_name", "node_ip", "ip_address", "interface_name", "utilization", "disk"))
    if has_display and alert_type:
        return (meta, alert_type)
    if not getattr(r, "raw_payload", None):
        if not alert_type and r.message and ":" in r.message:
            alert_type = (r.message.split(":", 1)[0].strip() or None)[:128]
        return (meta, alert_type)
    try:
        body = json.loads(r.raw_payload)
        parsed = _parse_solarwinds_payload(body)
        meta_parsed = {}
        if parsed.get("metadata_json"):
            try:
                meta_parsed = json.loads(parsed["metadata_json"]) or {}
            except Exception:
                pass
        for k, v in meta_parsed.items():
            if v is not None and v != "" and not meta.get(k):
                meta[k] = v
        if not alert_type:
            alert_type = parsed.get("alert_type") or (r.message.split(":", 1)[0].strip()[:128] if r.message and ":" in r.message else None)
    except Exception:
        if not alert_type and r.message and ":" in r.message:
            alert_type = (r.message.split(":", 1)[0].strip() or None)[:128]
    return (meta, alert_type)


def _alert_row_to_list_item(r: MonitoringAlertEvent) -> dict:
    """列表项：告警类型、节点名称、IP、接口/磁盘、利用率等（缺则从 raw_payload 回填）"""
    meta, alert_type = _enrich_from_raw_payload(r)
    node_name = meta.get("node_name") or meta.get("node_ip")
    ip_address = meta.get("ip_address")
    interface_name = meta.get("interface_name")
    utilization = meta.get("utilization")
    disk = meta.get("disk")
    city = meta.get("city")
    if (node_name is None or interface_name is None) and r.entity_interface:
        ni, iface = _parse_node_interface(r.entity_interface)
        if node_name is None:
            node_name = ni or r.entity_interface
        if interface_name is None:
            interface_name = iface
    alert_time = r.triggered_at or r.created_at
    return {
        "id": r.id,
        "webhook_id": r.webhook_id,
        "source": r.source,
        "alert_type": alert_type,
        "alert_title": r.alert_title,
        "message": r.message,
        "color": r.color,
        "entity_interface": r.entity_interface,
        "node_name": _display_value(node_name),
        "ip_address": _display_value(ip_address),
        "interface_name": _display_value(interface_name),
        "utilization": _display_value(utilization),
        "disk": _display_value(disk),
        "city": _display_value(city),
        "severity": r.severity,
        "status": r.status,
        "alert_time": alert_time.isoformat() if alert_time else None,
        "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _alert_row_to_dict(r: MonitoringAlertEvent) -> dict:
    """详情：含 raw_payload、fields 列表及展示用 node_name/ip_address 等（缺则从 raw_payload 回填）"""
    meta, alert_type = _enrich_from_raw_payload(r)
    node_name = meta.get("node_name") or meta.get("node_ip")
    ip_address = meta.get("ip_address")
    interface_name = meta.get("interface_name")
    utilization = meta.get("utilization")
    disk = meta.get("disk")
    city = meta.get("city")
    fields = meta.get("fields")
    if not isinstance(fields, list):
        fields = []
    if (node_name is None or interface_name is None) and r.entity_interface:
        ni, iface = _parse_node_interface(r.entity_interface)
        if node_name is None:
            node_name = ni or r.entity_interface
        if interface_name is None:
            interface_name = iface
    alert_time = r.triggered_at or r.created_at
    return {
        "id": r.id,
        "webhook_id": r.webhook_id,
        "source": r.source,
        "alert_type": alert_type,
        "alert_title": r.alert_title,
        "message": r.message,
        "color": r.color,
        "entity_interface": r.entity_interface,
        "node_name": _display_value(node_name),
        "ip_address": _display_value(ip_address),
        "interface_name": _display_value(interface_name),
        "utilization": _display_value(utilization),
        "disk": _display_value(disk),
        "city": _display_value(city),
        "fields": [{"title": f.get("title"), "value": _display_value(f.get("value")) if isinstance(f.get("value"), str) else f.get("value")} for f in fields] if fields else [],
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
