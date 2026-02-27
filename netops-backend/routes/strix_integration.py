# Strix 集成 API：扫描任务创建/列表/详情/报告/取消；OpenAPI 配置 GET/PUT
import json
import os
import threading
import logging
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.strix_models import StrixScanTask, StrixConfig
from utils.strix_runner import run_strix_sync, get_strix_env_from_config

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/strix",
    tags=["strix"],
    responses={404: {"description": "Not found"}},
)

# 后台任务进程句柄，用于取消：task_id -> process
_strix_processes: dict = {}
_lock = threading.Lock()


# ---------- Schemas ----------
class ScanCreate(BaseModel):
    target_type: Optional[str] = "web_url"
    target_value: Optional[str] = None
    targets: Optional[List[str]] = None
    instruction: Optional[str] = None
    instruction_file: Optional[str] = None
    scan_mode: Optional[str] = "deep"
    job_execution_id: Optional[int] = None


class StrixConfigUpdate(BaseModel):
    STRIX_LLM: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    STRIX_REASONING_EFFORT: Optional[str] = None


def _load_strix_config_kv(db: Session) -> dict:
    rows = db.query(StrixConfig).all()
    return {r.config_key: r.config_value for r in rows if r.config_value}


def _run_scan_task(task_id: int, workspace_dir: str):
    """后台线程：执行 Strix 并更新任务状态。"""
    from database.session import SessionLocal
    db = SessionLocal()
    try:
        task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
        if not task or task.status != "pending":
            return
        task.status = "running"
        db.commit()

        config_kv = _load_strix_config_kv(db)
        env = get_strix_env_from_config(config_kv)
        targets = None
        target = (task.target_value or "").strip()
        if target and target.startswith("["):
            try:
                targets = json.loads(task.target_value)
            except Exception:
                pass
        if not targets and target:
            targets = [target]

        result = run_strix_sync(
            target=target or "",
            targets=targets,
            scan_mode=task.scan_mode or "deep",
            instruction=task.instruction,
            workspace_dir=workspace_dir,
            run_name=task.run_name,
            env_override=env,
        )
        task.status = "success" if result["success"] else "failed"
        task.report_path = result.get("report_path") or ""
        from datetime import datetime
        from sqlalchemy import func
        task.finished_at = datetime.utcnow()
        if result.get("stdout") or result.get("stderr"):
            task.summary = json.dumps({"stdout": result.get("stdout", "")[:2000], "stderr": result.get("stderr", "")[:2000]})
        db.commit()
    except Exception as e:
        logger.exception("Strix task %s run error", task_id)
        try:
            task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.summary = json.dumps({"error": str(e)})
                from datetime import datetime
                task.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        with _lock:
            _strix_processes.pop(task_id, None)
        db.close()


# ---------- Scans ----------
@router.post("/scans")
def create_scan(body: ScanCreate, db: Session = Depends(get_db)):
    """创建扫描任务并异步执行。"""
    import uuid
    run_name = f"netops_{uuid.uuid4().hex[:12]}"
    task = StrixScanTask(
        target_type=body.target_type or "web_url",
        target_value=json.dumps(body.targets) if body.targets else body.target_value,
        instruction=body.instruction,
        scan_mode=body.scan_mode or "deep",
        status="pending",
        run_name=run_name,
        job_execution_id=body.job_execution_id,
        created_by="api",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workspace_dir = os.path.join(backend_root, "data", "strix_workspace")
    t = threading.Thread(target=_run_scan_task, args=(task.id, workspace_dir))
    t.daemon = True
    t.start()

    return {"id": task.id, "run_name": run_name, "status": "pending"}


@router.get("/scans")
def list_scans(
    job_execution_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """扫描任务列表，支持按 job_execution_id、status 筛选。"""
    q = db.query(StrixScanTask)
    if job_execution_id is not None:
        q = q.filter(StrixScanTask.job_execution_id == job_execution_id)
    if status:
        q = q.filter(StrixScanTask.status == status)
    total = q.count()
    items = q.order_by(StrixScanTask.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [t.to_dict() for t in items], "total": total}


@router.get("/scans/{task_id}")
def get_scan(task_id: int, db: Session = Depends(get_db)):
    """任务详情。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    return task.to_dict()


@router.get("/scans/{task_id}/report")
def get_scan_report(task_id: int, db: Session = Depends(get_db)):
    """返回报告目录下的 index.html 或首个 html 文件；若无则返回文本说明。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    path = (task.report_path or "").strip()
    if not path or not os.path.isdir(path):
        return PlainTextResponse(content="Report not ready or path missing.", status_code=404)
    index = os.path.join(path, "index.html")
    if os.path.isfile(index):
        return FileResponse(index, media_type="text/html")
    for f in os.listdir(path):
        if f.endswith(".html"):
            return FileResponse(os.path.join(path, f), media_type="text/html")
    return PlainTextResponse(content=f"Report directory: {path}. No HTML file found.")


@router.post("/scans/{task_id}/cancel")
def cancel_scan(task_id: int, db: Session = Depends(get_db)):
    """将任务标记为已取消（若在运行则仅标记，实际进程可能需超时退出）。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    if task.status not in ("pending", "running"):
        return {"id": task_id, "status": task.status, "message": "Already finished or cancelled"}
    task.status = "cancelled"
    from datetime import datetime
    task.finished_at = datetime.utcnow()
    db.commit()
    return {"id": task_id, "status": "cancelled"}


# ---------- Config (Phase 2) ----------
@router.get("/config")
def get_strix_config(db: Session = Depends(get_db)):
    """获取 Strix/LLM 配置，敏感字段脱敏。"""
    rows = db.query(StrixConfig).all()
    return [r.to_dict(mask_sensitive=True) for r in rows]


# 前端脱敏占位符，若 PUT 带此值表示未修改、不覆盖库中真实 key
_SENSITIVE_PLACEHOLDER = "********"


@router.put("/config")
def update_strix_config(body: StrixConfigUpdate, db: Session = Depends(get_db)):
    """更新 Strix/LLM 配置（键值对写入 strix_config 表）。API Key 为脱敏占位符时不覆盖。"""
    key_values = body.dict(exclude_none=True)
    for k, v in key_values.items():
        if v is None:
            continue
        # 敏感键若为脱敏占位符，表示前端未修改，不更新
        if k and "key" in k.lower() and (v == _SENSITIVE_PLACEHOLDER or v.strip() == ""):
            continue
        row = db.query(StrixConfig).filter(StrixConfig.config_key == k).first()
        if row:
            row.config_value = v
        else:
            db.add(StrixConfig(config_key=k, config_value=v))
    db.commit()
    return {"ok": True}
