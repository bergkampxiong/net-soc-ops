# Strix 集成 API：扫描任务创建/列表/详情/报告/取消；统一报告生成/下载/预览；OpenAPI 配置 GET/PUT
import json
import os
import shutil
import subprocess
import threading
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.strix_models import StrixScanTask, StrixConfig
from utils.strix_runner import run_strix_sync, get_strix_env_from_config, check_strix_activation, test_llm_config
from utils.datetime_utils import utc_to_beijing_str
from routes.system_global_config import get_global_config_kv
from utils.unified_report_builder import build_unified_report, UNIFIED_REPORT_MD, UNIFIED_REPORT_HTML

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/strix",
    tags=["strix"],
    responses={404: {"description": "Not found"}},
)

# 后台任务进程句柄，用于取消：task_id -> process（API 创建的任务与作业脚本运行的任务均可注册）
_strix_processes: dict = {}
_lock = threading.Lock()
# progress 接口短期缓存，减轻频繁读盘：task_id -> (expiry_ts, payload)
_progress_cache: dict = {}
_PROGRESS_CACHE_TTL_SEC = 2
# 仅内存：task_id -> 带真实密码的 instruction，供 _run_scan_task 使用一次后即删，不落库
_task_runtime_instruction: dict = {}


def register_strix_process(task_id: int, proc) -> None:
    """供作业服务等调用：将 Strix 进程注册到全局表，便于 POST /scans/{id}/cancel 杀进程。"""
    with _lock:
        _strix_processes[task_id] = proc


def unregister_strix_process(task_id: int) -> None:
    """脚本/任务结束后从全局表移除，避免 cancel 误杀。"""
    with _lock:
        _strix_processes.pop(task_id, None)


# ---------- Schemas ----------
class ScanCreate(BaseModel):
    target_type: Optional[str] = "web_url"
    target_value: Optional[str] = None
    targets: Optional[List[str]] = None
    instruction: Optional[str] = None
    instruction_file: Optional[str] = None
    scan_mode: Optional[str] = "deep"
    job_execution_id: Optional[int] = None
    # 可选：测试账号密码，仅用于本次扫描拼入 instruction 传给 Strix，不落库（存库用脱敏版）
    test_username: Optional[str] = None
    test_password: Optional[str] = None


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

        # 若有运行时 instruction（含真实密码），仅用于本次调用，不落库
        instruction = _task_runtime_instruction.pop(task_id, None) or task.instruction

        result = run_strix_sync(
            target=target or "",
            targets=targets,
            scan_mode=task.scan_mode or "deep",
            instruction=instruction,
            workspace_dir=workspace_dir,
            run_name=task.run_name,
            env_override=env,
            process_holder=_strix_processes,
            task_id=task.id,
        )
        task.status = "success" if result["success"] else "failed"
        task.report_path = result.get("report_path") or ""
        from datetime import datetime
        from sqlalchemy import func
        task.finished_at = datetime.utcnow()
        if result.get("stdout") or result.get("stderr"):
            def _ensure_str(v):
                if v is None:
                    return ""
                if isinstance(v, bytes):
                    return v.decode("utf-8", errors="replace")
                return str(v)
            sout = _ensure_str(result.get("stdout"))[:2000]
            serr = _ensure_str(result.get("stderr"))[:2000]
            task.summary = json.dumps({"stdout": sout, "stderr": serr})
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
def _build_instruction_with_credentials(
    instruction: Optional[str],
    test_username: Optional[str],
    test_password: Optional[str],
    mask_password: bool,
) -> str:
    """拼装带凭据的 instruction；mask_password 为 True 时密码显示为 [已配置]（用于存库/日志）。"""
    if not test_username and not test_password:
        return instruction or ""
    parts = []
    if test_username:
        parts.append(f"用户名 {test_username}")
    if test_password:
        parts.append("密码 [已配置]" if mask_password else f"密码 {test_password}")
    cred_prefix = "使用以下测试账号进行已认证扫描：" + "，".join(parts) + "。请先登录后再进行需认证的接口与页面测试。"
    return f"{cred_prefix}\n\n{instruction}" if instruction else cred_prefix


@router.post("/scans")
def create_scan(body: ScanCreate, db: Session = Depends(get_db)):
    """已停用：不再通过 API 创建扫描任务，请通过作业执行渗透任务创建。"""
    raise HTTPException(
        status_code=410,
        detail="API 创建已停用，请通过作业执行渗透任务创建扫描。",
    )


@router.get("/scans")
def list_scans(
    job_execution_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None, description="任务来源，如 job 表示作业执行"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """扫描任务列表，支持按 job_execution_id、status、created_by 筛选。"""
    q = db.query(StrixScanTask)
    if job_execution_id is not None:
        q = q.filter(StrixScanTask.job_execution_id == job_execution_id)
    if status:
        q = q.filter(StrixScanTask.status == status)
    if created_by and created_by.strip():
        q = q.filter(StrixScanTask.created_by == created_by.strip())
    total = q.count()
    items = q.order_by(StrixScanTask.created_at.desc()).offset(skip).limit(limit).all()
    # PRD：列表不返回 summary，仅保留任务元信息
    result = []
    for t in items:
        d = t.to_dict()
        d["summary"] = None
        result.append(d)
    return {"items": result, "total": total}


# 接口返回的 summary 中 stdout/stderr 单字段最大字符数，避免列表/详情一次传输过大导致性能问题
SUMMARY_DISPLAY_MAX_CHARS = 1024  # 1K，单次接口返回的 stdout/stderr 展示长度


def _trim_summary_for_display(summary: Any) -> Any:
    """对 summary 的 stdout/stderr 做尾部截断，避免接口返回超大 JSON。返回副本，不修改入参。"""
    if not summary or not isinstance(summary, dict):
        return summary
    out = summary.get("stdout")
    err = summary.get("stderr")
    need_trim = (
        (isinstance(out, str) and len(out) > SUMMARY_DISPLAY_MAX_CHARS)
        or (isinstance(err, str) and len(err) > SUMMARY_DISPLAY_MAX_CHARS)
    )
    if not need_trim:
        return summary
    res = dict(summary)
    if isinstance(out, str) and len(out) > SUMMARY_DISPLAY_MAX_CHARS:
        res["stdout"] = out[-SUMMARY_DISPLAY_MAX_CHARS:]
    if isinstance(err, str) and len(err) > SUMMARY_DISPLAY_MAX_CHARS:
        res["stderr"] = err[-SUMMARY_DISPLAY_MAX_CHARS:]
    return res


def _strip_ansi(text: str) -> str:
    """去掉 PTY 输出的 ANSI 转义序列，便于正则匹配与展示。"""
    import re
    if not text or not isinstance(text, str):
        return text
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def _parse_strix_stdout_stats(stdout: str) -> dict:
    """从 stdout 中解析 Model、Vulnerabilities、Agents、Tools；解析前先去除 ANSI 码。"""
    import re
    if not stdout or not isinstance(stdout, str):
        return {}
    out = _strip_ansi(stdout)
    stats = {}
    m = re.search(r"Model\s+(\S+)", out)
    if m:
        stats["model"] = _sanitize_model_display(_strip_ansi(m.group(1)).strip())
    # Vulnerabilities：取最后一次数字；Agents/Tools：取关键词后第一个数字，多行时取最后一次出现
    m = re.search(r"Vulnerabilities.*(\d+)", out)
    if m:
        stats["vulnerabilities"] = int(m.group(1))
    agents_m = re.findall(r"Agents\s+[\s·]*(\d+)", out)
    if agents_m:
        stats["agents"] = int(agents_m[-1])
    tools_m = re.findall(r"Tools\s+[\s·]*(\d+)", out)
    if tools_m:
        stats["tools"] = int(tools_m[-1])
    return stats


@router.get("/scans/{task_id}")
def get_scan(task_id: int, db: Session = Depends(get_db)):
    """任务详情。仅返回基础信息与 strix_stats（4 项），不返回 summary 原文（PRD）。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    d = task.to_dict()
    summary = d.get("summary")
    if summary and isinstance(summary, dict):
        stdout = summary.get("stdout") or ""
        strix_stats = _parse_strix_stdout_stats(stdout)
        if strix_stats:
            d["strix_stats"] = strix_stats
        # 展示用：若输出含 "Penetration test completed" 则视为成功（兼容旧记录及非零退出码）
        if d.get("status") == "failed" and "Penetration test completed" in (stdout + (summary.get("stderr") or "")):
            d["status"] = "success"
    # 优先用 progress.json 的最终统计（任务结束时写入），避免 summary 截断或顺序导致数字不对
    run_name = (task.run_name or "").strip()
    if run_name:
        backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        workspace_root = os.path.realpath(os.path.join(backend_root, "data", "strix_workspace"))
        file_stats = _read_progress_payload(task_id, run_name, workspace_root)
        if any(file_stats.get(k) is not None for k in ("model", "vulnerabilities", "agents", "tools")):
            merged = dict(d.get("strix_stats") or {})
            for k, v in file_stats.items():
                if v is not None:
                    merged[k] = v
            d["strix_stats"] = merged
    d["summary"] = None
    return d


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


def _resolve_report_base_path(task) -> str:
    """解析报告根目录：优先 task.report_path，否则用 data/strix_workspace/{run_name}。"""
    path = (task.report_path or "").strip()
    if path and os.path.isdir(path):
        return path
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workspace_root = os.path.realpath(os.path.join(backend_root, "data", "strix_workspace"))
    run_name = (task.run_name or "").strip()
    if run_name:
        return os.path.join(workspace_root, run_name)
    return path or ""


@router.get("/scans/{task_id}/report")
def get_scan_report(task_id: int, db: Session = Depends(get_db)):
    """返回报告目录下的 HTML 或 penetration_test_report.md；若无则返回文本说明。支持报告在子目录（strix_runs/xxx）。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    path = _resolve_report_base_path(task)
    if not path:
        return PlainTextResponse(
            content="Report path not set and run_name missing.",
            status_code=404,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
    found, result = _find_report_any(path)
    if found:
        media_type = result
        if "charset=" not in (media_type or ""):
            media_type = (media_type or "application/octet-stream") + "; charset=utf-8"
        return FileResponse(
            found,
            media_type=media_type,
            filename=os.path.basename(found),
        )
    err = result if isinstance(result, str) else "Report not ready."
    return PlainTextResponse(content=err, status_code=404, headers={"Content-Type": "text/plain; charset=utf-8"})


# ---------- 统一渗透测试报告 ----------
@router.post("/scans/{task_id}/unified-report")
def create_unified_report(task_id: int, db: Session = Depends(get_db)):
    """触发生成统一报告（读取 Strix 输出，可选 LLM 中文化，落盘）。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    path = _resolve_report_base_path(task)
    if not path or not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Report path not ready or missing")
    global_kv = get_global_config_kv(db)
    api_key = global_kv.get("GLOBAL_LLM_API_KEY")
    try:
        md_path, html_path, _ = build_unified_report(
            report_path=path,
            task_target_value=task.target_value,
            task_created_at=utc_to_beijing_str(task.created_at),
            task_finished_at=utc_to_beijing_str(task.finished_at),
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
            return FileResponse(html_path, media_type="text/html; charset=utf-8")
        raise HTTPException(status_code=404, detail="HTML version not available")
    return FileResponse(
        base_path,
        media_type="text/markdown; charset=utf-8",
        filename=os.path.basename(base_path),
    )


def _sanitize_model_display(model: Optional[str]) -> Optional[str]:
    """展示用：去除模型名中的 strix 字样。"""
    if not model or not isinstance(model, str):
        return model
    return model.replace("strix", "").replace("STRIX", "").strip() or model


def _read_progress_payload(task_id: int, run_name: str, workspace_root: str) -> dict:
    """从 progress.json 读取 payload；不抛错，读不到返回空值 dict。返回 model、vulnerabilities、agents、tools。"""
    empty = {"model": None, "vulnerabilities": None, "agents": None, "tools": None}
    if not run_name or not (workspace_root + os.sep):
        return empty
    progress_path = os.path.realpath(os.path.join(workspace_root, run_name, "progress.json"))
    if progress_path != workspace_root and not progress_path.startswith(workspace_root + os.sep):
        return empty
    if not os.path.isfile(progress_path):
        return empty
    try:
        with open(progress_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        model = data.get("model")
        if isinstance(model, str):
            model = _sanitize_model_display(_strip_ansi(model))
        return {
            "model": model,
            "vulnerabilities": data.get("vulnerabilities"),
            "agents": data.get("agents"),
            "tools": data.get("tools"),
        }
    except (json.JSONDecodeError, OSError):
        return empty


@router.get("/scans/{task_id}/progress")
def get_scan_progress(task_id: int, db: Session = Depends(get_db)):
    """运行中读取当前 vulnerabilities、agents、tools（从 progress.json 解析）；仅对 running/pending 任务做短期缓存减轻读盘。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    run_name = (task.run_name or "").strip()
    if not run_name:
        return {"model": None, "vulnerabilities": None, "agents": None, "tools": None}
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workspace_root = os.path.realpath(os.path.join(backend_root, "data", "strix_workspace"))
    only_cache_when_running = task.status in ("running", "pending")
    now = time.time()
    with _lock:
        if not only_cache_when_running:
            _progress_cache.pop(task_id, None)
        elif only_cache_when_running:
            cached = _progress_cache.get(task_id)
            if cached and cached[0] > now:
                return cached[1]
    payload = _read_progress_payload(task_id, run_name, workspace_root)
    if only_cache_when_running:
        with _lock:
            _progress_cache[task_id] = (now + _PROGRESS_CACHE_TTL_SEC, payload)
    return payload


# 运行回显接口：返回 live_echo.txt 尾部内容，便于前端展示与终端类似的实时输出
ECHO_DEFAULT_TAIL_CHARS = 100_000


@router.get("/scans/{task_id}/echo")
def get_scan_echo(
    task_id: int,
    tail: int = Query(ECHO_DEFAULT_TAIL_CHARS, ge=0, le=500_000, description="返回最后 N 个字符"),
    db: Session = Depends(get_db),
):
    """运行中或结束后读取本次任务的实时回显（stdout+stderr 写入的 live_echo.txt）尾部，供前端展示。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    run_name = (task.run_name or "").strip()
    if not run_name:
        raise HTTPException(status_code=404, detail="No run_name for this task")
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workspace_root = os.path.realpath(os.path.join(backend_root, "data", "strix_workspace"))
    echo_path = os.path.realpath(os.path.join(workspace_root, run_name, "live_echo.txt"))
    if echo_path != workspace_root and not echo_path.startswith(workspace_root + os.sep):
        raise HTTPException(status_code=404, detail="Invalid path")
    if not os.path.isfile(echo_path):
        return PlainTextResponse(content="", media_type="text/plain; charset=utf-8")
    try:
        with open(echo_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size <= tail:
                f.seek(0)
                content = f.read().decode("utf-8", errors="replace")
            else:
                f.seek(-tail, 2)
                content = f.read().decode("utf-8", errors="replace")
        content = _strip_ansi(content)
        return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")
    except OSError:
        return PlainTextResponse(content="", media_type="text/plain; charset=utf-8")


def _kill_process_and_children(proc) -> None:
    """终止进程及其子进程（减少 Strix 未干活时的 token 消耗）。"""
    try:
        if proc is None:
            return
        if os.name != "nt":
            try:
                import signal
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception as e:
        logger.warning("终止 Strix 进程时异常: %s", e)


@router.post("/scans/{task_id}/cancel")
def cancel_scan(task_id: int, db: Session = Depends(get_db)):
    """将任务标记为已取消；若在运行则终止 Strix 主进程及子进程，减少 token 消耗。"""
    task = db.query(StrixScanTask).filter(StrixScanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scan task not found")
    if task.status not in ("pending", "running"):
        return {"id": task_id, "status": task.status, "message": "Already finished or cancelled"}
    with _lock:
        proc = _strix_processes.pop(task_id, None)
    if proc is not None:
        _kill_process_and_children(proc)
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


def _check_docker_sandbox() -> tuple[bool, str]:
    """检查 Docker 是否可用且 strix-sandbox 镜像存在；代理模式与认证扫描依赖沙箱。"""
    try:
        import subprocess
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").lower()
            if "permission denied" in err or "permission" in err and "socket" in err:
                return False, "当前运行后端的用户无权限访问 Docker，请将用户加入 docker 组后重启后端: sudo usermod -aG docker <运行后端的用户名>"
            return False, "Docker 未运行或不可用，Strix 将仅以请求模式运行（无法使用浏览器/代理与完整认证扫描）"
        r2 = subprocess.run(
            ["docker", "image", "inspect", "ghcr.io/usestrix/strix-sandbox:0.1.12"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r2.returncode != 0:
            return False, "未找到 strix-sandbox 镜像，请执行: docker pull ghcr.io/usestrix/strix-sandbox:0.1.12"
        return True, "Docker 与沙箱镜像就绪，可进行代理模式与认证扫描"
    except FileNotFoundError:
        return False, "未安装 Docker，Strix 将仅以请求模式运行（无法使用浏览器/代理与完整认证扫描）"
    except Exception as e:
        return False, f"Docker 检查异常: {e}"


# ---------- 激活状态检查 ----------
@router.get("/status")
def get_strix_status():
    """检查 Strix 是否已激活：CLI 可执行；并检查 Docker 沙箱是否就绪（代理/认证扫描依赖）。"""
    source_ok, cli_ok, message, cli_path = check_strix_activation()
    sandbox_ok, sandbox_message = _check_docker_sandbox()
    return {
        "source_present": source_ok,
        "cli_available": cli_ok,
        "activated": source_ok and cli_ok,
        "message": message,
        "cli_path": cli_path,
        "sandbox_available": sandbox_ok,
        "sandbox_message": sandbox_message,
    }


# ---------- Config (Phase 2) ----------
@router.post("/test-llm")
def test_strix_llm(db: Session = Depends(get_db)):
    """使用当前已保存的 Strix/LLM 配置发起一次最小请求，验证 API Key 是否可用。"""
    config_kv = _load_strix_config_kv(db)
    ok, message = test_llm_config(config_kv)
    return {"ok": ok, "message": message}


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
