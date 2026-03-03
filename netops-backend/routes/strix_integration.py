# Strix 集成 API：扫描任务创建/列表/详情/报告/取消；统一报告生成/下载/预览；OpenAPI 配置 GET/PUT
import json
import os
import shutil
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.strix_models import StrixScanTask, StrixConfig
from utils.strix_runner import run_strix_sync, get_strix_env_from_config, check_strix_activation
from routes.system_global_config import get_global_config_kv
from utils.unified_report_builder import build_unified_report, UNIFIED_REPORT_MD, UNIFIED_REPORT_HTML

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


def _find_report_html(path: str):
    """在 path 或其子目录中查找 index.html 或首个 .html 文件，返回 (绝对路径, None) 或 (None, 错误信息)。"""
    if not path or not os.path.isdir(path):
        return None, "Report not ready or path missing."
    index = os.path.join(path, "index.html")
    if os.path.isfile(index):
        return index, None
    for f in os.listdir(path):
        if f.endswith(".html"):
            return os.path.join(path, f), None
    # 兼容：report_path 可能为 strix_runs 父目录，报告在子目录（如 172-18-40-99-8080_e44c）
    for sub in os.listdir(path):
        sub_path = os.path.join(path, sub)
        if not os.path.isdir(sub_path):
            continue
        idx = os.path.join(sub_path, "index.html")
        if os.path.isfile(idx):
            return idx, None
        for f in os.listdir(sub_path):
            if f.endswith(".html"):
                return os.path.join(sub_path, f), None
    return None, f"Report directory: {path}. No HTML file found."


def _find_report_any(path: str):
    """先找 HTML，再找 penetration_test_report.md；返回 (绝对路径, media_type) 或 (None, 错误信息)。"""
    found, err = _find_report_html(path)
    if found:
        return found, "text/html"
    if not path or not os.path.isdir(path):
        return None, err or "Report not ready or path missing."
    md_name = "penetration_test_report.md"
    md_path = os.path.join(path, md_name)
    if os.path.isfile(md_path):
        return md_path, "text/markdown"
    for sub in os.listdir(path):
        sub_path = os.path.join(path, sub)
        if not os.path.isdir(sub_path):
            continue
        sub_md = os.path.join(sub_path, md_name)
        if os.path.isfile(sub_md):
            return sub_md, "text/markdown"
    return None, err or "No HTML or penetration_test_report.md found."


@router.get("/scans/{task_id}/report")
def get_scan_report(task_id: int, db: Session = Depends(get_db)):
    """返回报告目录下的 HTML 或 penetration_test_report.md；若无则返回文本说明。支持报告在子目录（strix_runs/xxx）。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    path = (task.report_path or "").strip()
    found, result = _find_report_any(path)
    if found:
        media_type = result
        return FileResponse(
            found,
            media_type=media_type,
            filename=os.path.basename(found),
        )
    err = result if isinstance(result, str) else "Report not ready."
    return PlainTextResponse(content=err, status_code=404)


# ---------- 统一渗透测试报告 ----------
@router.post("/scans/{task_id}/unified-report")
def create_unified_report(task_id: int, db: Session = Depends(get_db)):
    """触发生成统一报告（读取 Strix 输出，可选 LLM 中文化，落盘）。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    path = (task.report_path or "").strip()
    if not path or not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Report path not ready or missing")
    global_kv = get_global_config_kv(db)
    api_key = global_kv.get("GLOBAL_LLM_API_KEY")
    try:
        md_path, html_path, _ = build_unified_report(
            report_path=path,
            task_target_value=task.target_value,
            task_created_at=task.created_at.isoformat() if task.created_at else None,
            task_finished_at=task.finished_at.isoformat() if task.finished_at else None,
            api_key=api_key,
            api_base=global_kv.get("GLOBAL_LLM_API_BASE"),
            model=global_kv.get("GLOBAL_LLM_MODEL"),
            use_llm=bool(api_key),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    task.unified_report_path = md_path
    task.unified_report_generated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "unified_report_path": md_path, "ready": True}


@router.get("/scans/{task_id}/unified-report")
def get_unified_report(
    task_id: int,
    format: Optional[str] = Query(None, description="html 则返回 HTML 预览"),
    db: Session = Depends(get_db),
):
    """下载或预览统一报告。已生成则返回 .md 或 .html 文件流；未生成返回 404。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    base_path = (task.unified_report_path or "").strip()
    if not base_path or not os.path.isfile(base_path):
        raise HTTPException(status_code=404, detail="Unified report not generated. Call POST first.")
    base_dir = os.path.dirname(base_path)
    if format and format.lower() == "html":
        html_path = os.path.join(base_dir, UNIFIED_REPORT_HTML)
        if os.path.isfile(html_path):
            return FileResponse(html_path, media_type="text/html")
        raise HTTPException(status_code=404, detail="HTML version not available")
    return FileResponse(
        base_path,
        media_type="text/markdown",
        filename=os.path.basename(base_path),
    )


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


def _ensure_path_under_strix_workspace(path: str) -> bool:
    """校验 path 在 data/strix_workspace 下，避免误删系统目录。"""
    if not path or not os.path.isabs(path):
        return False
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    workspace_root = os.path.realpath(os.path.join(backend_root, "data", "strix_workspace"))
    path_real = os.path.realpath(path)
    return path_real.startswith(workspace_root + os.sep) or path_real == workspace_root


@router.delete("/scans/{task_id}")
def delete_scan(task_id: int, db: Session = Depends(get_db)):
    """删除渗透测试报告记录，并删除磁盘上的报告目录。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    report_path = (task.report_path or "").strip()
    db.delete(task)
    db.commit()
    if report_path and _ensure_path_under_strix_workspace(report_path) and os.path.isdir(report_path):
        try:
            shutil.rmtree(report_path)
            logger.info("已删除报告目录: %s", report_path)
        except OSError as e:
            logger.warning("删除报告目录失败 %s: %s", report_path, e)
    return {"id": task_id, "message": "deleted"}


# ---------- 激活状态检查 ----------
@router.get("/status")
def get_strix_status():
    """检查 Strix 是否已激活：源码目录存在且 CLI 可执行。用于部署后自检或前端展示。"""
    source_ok, cli_ok, message, cli_path = check_strix_activation()
    return {
        "source_present": source_ok,
        "cli_available": cli_ok,
        "activated": source_ok and cli_ok,
        "message": message,
        "cli_path": cli_path,
    }


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
