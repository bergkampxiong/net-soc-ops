import json
import os
import subprocess
import tempfile
import threading
import time
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from typing import List, Optional, Tuple, Any
from datetime import datetime, timedelta
from app.models.job import Job, JobExecution
from app.schemas.job import JobCreate, JobUpdate, JobExecutionCreate
from app.process_designer.code_generator import CodeGenerator
from celery import shared_task
from fastapi import HTTPException
from database.strix_models import StrixScanTask
from routes.strix_integration import register_strix_process, unregister_strix_process, _load_strix_config_kv
from utils.strix_runner import _parse_stdout_stats, get_strix_env_from_config

class JobService:
    def __init__(self, db: Session):
        self.db = db

    def get_jobs(
        self,
        skip: int = 0,
        limit: int = 10,
        name: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None,
        run_type: Optional[str] = None,
        from_published_only: bool = True,
    ) -> List[Job]:
        """获取作业列表。默认仅返回由流程发布产生的作业（process_definition_id 非空）。"""
        query = self.db.query(Job)
        if from_published_only:
            query = query.filter(Job.process_definition_id.isnot(None))
        if name:
            query = query.filter(Job.name.ilike(f"%{name}%"))
        if job_type:
            query = query.filter(Job.job_type == job_type)
        if status:
            query = query.filter(Job.status == status)
        if run_type:
            query = query.filter(Job.run_type == run_type)
        return query.order_by(desc(Job.created_at)).offset(skip).limit(limit).all()

    def get_job(self, job_id: int) -> Optional[Job]:
        """获取作业详情"""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def create_job(self, job: JobCreate) -> Job:
        """创建作业"""
        db_job = Job(
            name=job.name,
            description=job.description,
            job_type=job.job_type,
            process_definition_id=job.process_definition_id,
            run_type=job.run_type or "once",
            parameters=job.parameters,
            schedule_config=job.schedule_config.dict() if job.schedule_config else None,
            status="created",
            created_by="system",
            updated_by="system",
        )
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def get_job_by_process_definition_id(self, process_definition_id: str) -> Optional[Job]:
        """按流程定义 ID 查询作业（用于发布时幂等）"""
        return (
            self.db.query(Job)
            .filter(Job.process_definition_id == process_definition_id)
            .first()
        )

    def update_job(self, job_id: int, job: JobUpdate) -> Optional[Job]:
        """更新作业（含 run_type、schedule_config，转为定期时需带 schedule_config）"""
        db_job = self.get_job(job_id)
        if not db_job:
            return None
        update_data = job.dict(exclude_unset=True)
        if "schedule_config" in update_data and update_data["schedule_config"] is not None:
            update_data["schedule_config"] = (
                update_data["schedule_config"].dict()
                if hasattr(update_data["schedule_config"], "dict")
                else update_data["schedule_config"]
            )
        for key, value in update_data.items():
            if hasattr(db_job, key):
                setattr(db_job, key, value)
        db_job.updated_by = "system"
        db_job.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def delete_job(self, job_id: int) -> bool:
        """删除作业"""
        db_job = self.get_job(job_id)
        if not db_job:
            return False
            
        self.db.delete(db_job)
        self.db.commit()
        return True

    def execute_job(self, job_id: int) -> bool:
        """执行作业：若有 process_definition_id 则生成并执行流程代码，否则仅创建执行记录"""
        db_job = self.get_job(job_id)
        if not db_job:
            return False

        execution = JobExecution(
            job_id=job_id,
            status="running",
            start_time=datetime.utcnow(),
        )
        self.db.add(execution)
        self.db.flush()
        execution_id = execution.id
        db_job.status = "active"
        db_job.last_run_at = datetime.utcnow()
        self.db.commit()

        if not getattr(db_job, "process_definition_id", None):
            execution = self.db.query(JobExecution).filter(JobExecution.id == execution_id).first()
            if execution:
                execution.status = "completed"
                execution.end_time = datetime.utcnow()
                execution.result = {"message": "无关联流程，仅记录执行"}
            self.db.commit()
            return True

        # 拉取流程定义
        try:
            row = (
                self.db.execute(
                    text(
                        "SELECT * FROM process_definitions WHERE id = :id AND deleted_at IS NULL"
                    ),
                    {"id": db_job.process_definition_id},
                )
            ).mappings().first()
            if not row:
                self._set_execution_failed(
                    execution_id,
                    "流程定义不存在或已删除",
                )
                return True
            process = dict(getattr(row, "_mapping", row))
            for key in ("nodes", "edges", "variables"):
                if key not in process or process[key] is None:
                    process[key] = [] if key != "variables" else {}
                elif isinstance(process[key], str):
                    process[key] = json.loads(process[key]) if process[key] else ([] if key != "variables" else {})
        except Exception as e:
            self._set_execution_failed(execution_id, str(e))
            return True

        nodes = process.get("nodes", [])
        has_traditional = any(
            n.get("type") in ("deviceConnect", "configBackup", "configDeploy") for n in nodes
        )
        penetration_nodes = [n for n in nodes if n.get("type") == "penetrationTest"]
        script_logs = ""
        execution_failed = False
        script_returncode = 0

        # 若有设备/配置节点：生成并执行 Python 脚本
        if has_traditional:
            try:
                gen = CodeGenerator(process)
                val = gen.validate()
                if not val.get("isValid"):
                    self._set_execution_failed(
                        execution_id,
                        "流程校验失败: " + "; ".join(val.get("errors", [])),
                    )
                    return True
                code = gen.generate_code()
            except Exception as e:
                self._set_execution_failed(execution_id, str(e))
                return True

            backend_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            fd, path = tempfile.mkstemp(suffix=".py", prefix="job_")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(code)
                env = os.environ.copy()
                env["PYTHONPATH"] = backend_root
                result = subprocess.run(
                    [os.environ.get("PYTHON_EXE", "python"), path],
                    cwd=backend_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                script_logs = (result.stdout or "") + (result.stderr or "")
                script_returncode = result.returncode
                if result.returncode != 0:
                    execution_failed = True
                    script_logs += f"\n[脚本退出码: {result.returncode}]"
            except subprocess.TimeoutExpired:
                self._set_execution_failed(execution_id, "执行超时")
                return True
            except Exception as e:
                self._set_execution_failed(execution_id, str(e))
                return True
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            if execution_failed:
                execution = self.db.query(JobExecution).filter(JobExecution.id == execution_id).first()
                if execution:
                    execution.end_time = datetime.utcnow()
                    execution.logs = script_logs
                    execution.status = "failed"
                    execution.error_message = "脚本执行失败"
                    execution.result = {"returncode": result.returncode}
                self.db.commit()
                job = self.db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "created"
                self.db.commit()
                return True

        # 渗透测试节点：生成本地脚本并按 strix -n --target "{URL}" --scan-mode {} --instruction "{}" 格式执行
        # summary 中 stdout/stderr 单字段最大保留字符数，避免截断过短导致解析或排查 BUG（见 API 优化 PRD）
        STRIX_SUMMARY_MAX_CHARS = 1_000_000  # 1000K
        backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        _strix_fixed = "/app/net-soc-ops/netops-backend/strix/bin/strix"
        _strix_rel = os.path.join(backend_root, "strix", "bin", "strix")
        strix_bin = _strix_fixed if os.path.isfile(_strix_fixed) else _strix_rel
        workspace_root = os.path.join(backend_root, "data", "strix_workspace")
        try:
            os.makedirs(workspace_root, exist_ok=True)
        except OSError:
            pass
        strix_scan_ids: List[int] = []
        for idx, pn in enumerate(penetration_nodes):
            data = pn.get("data") or {}
            target_source = data.get("targetSource") or "inline"
            target_node_id = data.get("targetNodeId")
            targets = []
            target_type = data.get("targetType") or "web_url"
            static_only = False
            if target_source == "targetNode" and target_node_id:
                target_node = next((n for n in nodes if n.get("id") == target_node_id), None)
                if target_node:
                    tn_data = target_node.get("data") or {}
                    td = tn_data.get("targets")
                    if isinstance(td, list):
                        targets = [str(t) for t in td]
                    elif td:
                        targets = [str(td)]
                    elif tn_data.get("targetValue"):
                        targets = [str(tn_data["targetValue"])]
                    target_type = tn_data.get("targetType") or target_type
                    static_only = bool(tn_data.get("staticOnly"))
            if not targets and target_source != "targetNode":
                inline = data.get("targets")
                if isinstance(inline, list):
                    targets = [str(t) for t in inline]
                elif inline:
                    targets = [str(inline)]
                elif data.get("targetValue"):
                    targets = [str(data["targetValue"])]
            if not targets:
                script_logs += "\n[渗透测试] 跳过节点: 无目标（请从扫描目标节点选择目标）\n"
                continue
            url = targets[0]
            scan_mode = data.get("scanMode") or "deep"
            instruction = (data.get("instruction") or "").strip()
            if static_only:
                instruction = "仅做静态代码审计，不要尝试运行应用。Perform static code analysis only; do not attempt to run the application.\n\n" + instruction
            if not instruction:
                instruction = ""
            run_name = f"job_{execution_id}_{idx}"
            run_dir = os.path.join(workspace_root, run_name)
            try:
                os.makedirs(run_dir, exist_ok=True)
            except OSError as e:
                script_logs += f"\n[渗透测试] 无法创建目录 {run_dir}: {e}\n"
                continue
            # 创建扫描任务记录，便于 API 列表/详情/进度/取消 与脚本回显关联
            task = StrixScanTask(
                target_type=target_type,
                target_value=json.dumps([url]),
                instruction=instruction or None,
                scan_mode=scan_mode,
                status="running",
                run_name=run_name,
                job_execution_id=execution_id,
                report_path=run_dir,
                created_by="job",
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            task_id = task.id
            script_logs += f"\n[渗透测试] 扫描任务 id={task_id}，run_name={run_name}\n"
            script_path = os.path.join(run_dir, "run_strix.sh")
            heredoc_end = "ENDINST_" + str(execution_id) + "_" + str(idx)
            try:
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write("#!/bin/bash\n")
                    # 使用 BASH_SOURCE[0] 取脚本所在目录，避免用 source 执行时 $0 为 -bash 导致 dirname 报错
                    f.write('SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"\n')
                    f.write('cd "$SCRIPT_DIR"\n')
                    f.write("INSTRUCTION=$(cat << '" + heredoc_end + "'\n")
                    f.write(instruction or "")
                    f.write("\n" + heredoc_end + "\n)\n")
                    f.write(f'exec "{strix_bin}" -n --target "{url.replace(chr(34), chr(92)+chr(34))}" --scan-mode "{scan_mode}" --instruction "$INSTRUCTION"\n')
                os.chmod(script_path, 0o755)
            except OSError as e:
                script_logs += f"\n[渗透测试] 写入脚本失败: {e}\n"
                task.status = "failed"
                task.finished_at = datetime.utcnow()
                task.summary = json.dumps({"error": str(e)})
                self.db.commit()
                continue
            script_logs += f"[渗透测试] 已生成脚本: {script_path}\n"
            script_logs += f"[渗透测试] 执行: {strix_bin} -n --target \"{url}\" --scan-mode {scan_mode} --instruction \"{{instruction 全文}}\"\n"
            proc = None
            stdout_chunks = []
            stderr_chunks = []
            stdout_lock = threading.Lock()
            stderr_lock = threading.Lock()
            # 共享回显缓冲：供定时写入（1/3/5 分钟）与结束时写 live_echo.txt + progress.json 使用
            shared_echo_chunks = []
            echo_lock = threading.Lock()
            latest_stats = {}
            progress_file = os.path.join(run_dir, "progress.json")
            live_echo_path = os.path.join(run_dir, "live_echo.txt")
            read_chunk_size = 8192

            def write_echo_and_progress(content_str: str) -> None:
                """覆盖写 live_echo.txt，解析 4 项并写 progress.json（PRD：仅在此处与定时写更新 progress）。"""
                if not content_str:
                    return
                try:
                    with open(live_echo_path, "w", encoding="utf-8") as f:
                        f.write(content_str)
                except OSError:
                    pass
                stats = _parse_stdout_stats(content_str)
                if stats:
                    latest_stats.update(stats)
                    try:
                        with open(progress_file, "w", encoding="utf-8") as f:
                            json.dump(latest_stats, f, ensure_ascii=False)
                    except OSError:
                        pass

            def run_scheduled_writes(proc_ref):
                """第 1、3、5 分钟各覆盖写一次 live_echo.txt 并更新 progress.json。"""
                for wait_sec in (60, 120, 120):  # 1min, 再 2min 到 3min, 再 2min 到 5min
                    time.sleep(wait_sec)
                    if proc_ref is None or proc_ref.poll() is not None:
                        return
                    with echo_lock:
                        content = "".join(shared_echo_chunks)
                    write_echo_and_progress(content)

            def read_from_pty(master_fd):
                """从 PTY master 读，使 Strix 认为有 TTY；只收集到 shared_echo_chunks，不在此处写 progress。"""
                pty_chunks = []
                try:
                    while True:
                        try:
                            data = os.read(master_fd, read_chunk_size)
                        except OSError:
                            break
                        if not data:
                            break
                        chunk = data.decode("utf-8", errors="replace")
                        pty_chunks.append(chunk)
                        with echo_lock:
                            shared_echo_chunks.append(chunk)
                finally:
                    with stdout_lock:
                        stdout_chunks.extend(pty_chunks)
                    try:
                        os.close(master_fd)
                    except OSError:
                        pass

            def read_stdout(pipe):
                try:
                    while True:
                        chunk = pipe.read(read_chunk_size)
                        if not chunk:
                            break
                        with stdout_lock:
                            stdout_chunks.append(chunk)
                        with echo_lock:
                            shared_echo_chunks.append(chunk)
                finally:
                    try:
                        pipe.close()
                    except OSError:
                        pass

            def read_stderr(pipe):
                try:
                    while True:
                        chunk = pipe.read(read_chunk_size)
                        if not chunk:
                            break
                        with stderr_lock:
                            stderr_chunks.append(chunk)
                        with echo_lock:
                            shared_echo_chunks.append(chunk)
                finally:
                    try:
                        pipe.close()
                    except OSError:
                        pass

            # 将 Strix/LLM 配置注入子进程环境，使脚本内的 strix 能使用配置的 API（不写入脚本文件，避免密钥落盘）
            config_kv = _load_strix_config_kv(self.db)
            strix_env = get_strix_env_from_config(config_kv)
            use_pty = os.name != "nt"
            t_pty, t_out, t_err = None, None, None
            try:
                if use_pty:
                    try:
                        import pty
                        master_fd, slave_fd = pty.openpty()
                        proc = subprocess.Popen(
                            ["/bin/bash", script_path],
                            cwd=run_dir,
                            env=strix_env,
                            stdout=slave_fd,
                            stderr=subprocess.STDOUT,
                            start_new_session=True,
                        )
                        os.close(slave_fd)
                        register_strix_process(task_id, proc)
                        t_pty = threading.Thread(target=read_from_pty, args=(master_fd,))
                        t_pty.daemon = True
                        t_pty.start()
                        t_timer = threading.Thread(target=run_scheduled_writes, args=(proc,))
                        t_timer.daemon = True
                        t_timer.start()
                        proc.wait(timeout=3600)
                        t_pty.join(timeout=5)
                    except ImportError:
                        use_pty = False
                if not use_pty:
                    proc = subprocess.Popen(
                        ["/bin/bash", script_path],
                        cwd=run_dir,
                        env=strix_env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        start_new_session=os.name != "nt",
                    )
                    register_strix_process(task_id, proc)
                    t_out = threading.Thread(target=read_stdout, args=(proc.stdout,))
                    t_err = threading.Thread(target=read_stderr, args=(proc.stderr,))
                    t_out.daemon = True
                    t_err.daemon = True
                    t_out.start()
                    t_err.start()
                    t_timer = threading.Thread(target=run_scheduled_writes, args=(proc,))
                    t_timer.daemon = True
                    t_timer.start()
                    proc.wait(timeout=3600)
                    t_out.join(timeout=5)
                    t_err.join(timeout=5)
                with stdout_lock:
                    full_stdout = "".join(stdout_chunks)
                with stderr_lock:
                    full_stderr = "".join(stderr_chunks)
                # 结束时再写一次 live_echo.txt + progress.json（PRD）
                full_echo = (full_stdout or "") + "\n" + (full_stderr or "")
                write_echo_and_progress(full_echo)
                script_logs += full_echo
                # Strix 可能非零退出仍为“完成”：以输出中是否含 "Penetration test completed" 判定成功
                if "Penetration test completed" in full_echo:
                    task.status = "success"
                else:
                    task.status = "success" if proc.returncode == 0 else "failed"
                task.summary = json.dumps({
                    "stdout": (full_stdout or "")[:STRIX_SUMMARY_MAX_CHARS],
                    "stderr": (full_stderr or "")[:STRIX_SUMMARY_MAX_CHARS],
                })
                if proc.returncode != 0:
                    script_logs += f"\n[渗透测试] 脚本退出码: {proc.returncode}\n"
                else:
                    script_logs += "\n[渗透测试] 扫描脚本执行完成\n"
                strix_scan_ids.append(task_id)
            except subprocess.TimeoutExpired:
                script_logs += "\n[渗透测试] 执行超时（1 小时）\n"
                if proc:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                if t_pty is not None:
                    t_pty.join(timeout=2)
                if t_out is not None:
                    t_out.join(timeout=2)
                if t_err is not None:
                    t_err.join(timeout=2)
                with stdout_lock:
                    full_stdout = "".join(stdout_chunks)
                with stderr_lock:
                    full_stderr = "".join(stderr_chunks)
                write_echo_and_progress((full_stdout or "") + "\n" + (full_stderr or ""))
                task.status = "failed"
                task.summary = json.dumps({
                    "error": "执行超时",
                    "stdout": (full_stdout or "")[:STRIX_SUMMARY_MAX_CHARS],
                    "stderr": (full_stderr or "")[:STRIX_SUMMARY_MAX_CHARS],
                })
            except Exception as e:
                script_logs += f"\n[渗透测试] 执行异常: {e}\n"
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                if t_pty is not None:
                    t_pty.join(timeout=2)
                if t_out is not None:
                    t_out.join(timeout=2)
                if t_err is not None:
                    t_err.join(timeout=2)
                with stdout_lock:
                    full_stdout = "".join(stdout_chunks)
                with stderr_lock:
                    full_stderr = "".join(stderr_chunks)
                write_echo_and_progress((full_stdout or "") + "\n" + (full_stderr or ""))
                task.status = "failed"
                task.summary = json.dumps({"error": str(e)})
            finally:
                unregister_strix_process(task_id)
                task.finished_at = datetime.utcnow()
                self.db.commit()

        execution = self.db.query(JobExecution).filter(JobExecution.id == execution_id).first()
        if execution:
            execution.end_time = datetime.utcnow()
            execution.logs = (execution.logs or "") + script_logs
            if not execution_failed:
                execution.status = "completed"
                execution.result = {"returncode": script_returncode, "strix_scan_ids": strix_scan_ids}

        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "created"
            job.last_run_at = datetime.utcnow()
        self.db.commit()
        return True

    def _set_execution_failed(self, execution_id: int, error_message: str):
        execution = self.db.query(JobExecution).filter(JobExecution.id == execution_id).first()
        if execution:
            execution.status = "failed"
            execution.end_time = datetime.utcnow()
            execution.error_message = error_message
        self.db.commit()

    def pause_job(self, job_id: int) -> bool:
        """暂停作业"""
        db_job = self.get_job(job_id)
        if not db_job or db_job.status != "active":
            return False
            
        db_job.status = "paused"
        db_job.updated_at = datetime.utcnow()
        db_job.updated_by = "system"  # TODO: 从当前用户获取
        
        self.db.commit()
        return True

    def resume_job(self, job_id: int) -> bool:
        """恢复作业"""
        db_job = self.get_job(job_id)
        if not db_job or db_job.status != "paused":
            return False
            
        db_job.status = "active"
        db_job.updated_at = datetime.utcnow()
        db_job.updated_by = "system"  # TODO: 从当前用户获取
        
        self.db.commit()
        return True

    def terminate_job(self, job_id: int) -> bool:
        """终止作业"""
        db_job = self.get_job(job_id)
        if not db_job or db_job.status == "terminated":
            return False
            
        db_job.status = "terminated"
        db_job.updated_at = datetime.utcnow()
        db_job.updated_by = "system"  # TODO: 从当前用户获取
        
        self.db.commit()
        return True

    def get_job_executions(
        self,
        job_id: int,
        skip: int = 0,
        limit: int = 10
    ) -> List[JobExecution]:
        """获取作业执行历史"""
        return (
            self.db.query(JobExecution)
            .filter(JobExecution.job_id == job_id)
            .order_by(desc(JobExecution.start_time))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_job_executions_cross_job(
        self,
        job_id: Optional[int] = None,
        status: Optional[str] = None,
        start_time_from: Optional[str] = None,
        start_time_to: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[int, List[Tuple[JobExecution, str]]]:
        """跨作业查询执行列表，返回 (total, [(execution, job_name), ...])"""
        q = self.db.query(JobExecution).join(Job, JobExecution.job_id == Job.id)
        if job_id is not None:
            q = q.filter(JobExecution.job_id == job_id)
        if status:
            q = q.filter(JobExecution.status == status)
        if start_time_from:
            try:
                dt_from = datetime.fromisoformat(start_time_from.replace("Z", "+00:00"))
                q = q.filter(JobExecution.start_time >= dt_from)
            except (ValueError, TypeError):
                pass
        if start_time_to:
            try:
                dt_to = datetime.fromisoformat(start_time_to.replace("Z", "+00:00"))
                q = q.filter(JobExecution.start_time <= dt_to)
            except (ValueError, TypeError):
                pass
        total = q.count()
        rows = (
            q.order_by(desc(JobExecution.start_time))
            .offset(skip)
            .limit(limit)
            .all()
        )
        out = []
        for ex in rows:
            name = ex.job.name if ex.job else ""
            out.append((ex, name))
        return total, out

    def get_job_executions_stats(
        self,
        date_from: str,
        date_to: str,
        job_id: Optional[int] = None,
    ) -> dict:
        """按日期范围统计执行：total, success, failed, running, success_rate。日期格式 YYYY-MM-DD。"""
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            dt_to = datetime.strptime(date_to, "%Y-%m-%d")
            dt_to_end = dt_to + timedelta(days=1)
        except (ValueError, TypeError):
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "running": 0,
                "success_rate": 0.0,
            }
        q = self.db.query(JobExecution).filter(
            JobExecution.start_time >= dt_from,
            JobExecution.start_time < dt_to_end,
        )
        if job_id is not None:
            q = q.filter(JobExecution.job_id == job_id)
        total = q.count()
        if total == 0:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "running": 0,
                "success_rate": 0.0,
            }
        completed = q.filter(JobExecution.status == "completed").count()
        failed = q.filter(JobExecution.status == "failed").count()
        running = q.filter(JobExecution.status == "running").count()
        success_rate = round(completed / total * 100.0, 1) if total else 0.0
        return {
            "total": total,
            "success": completed,
            "failed": failed,
            "running": running,
            "success_rate": success_rate,
        }

@shared_task
def execute_job_task(job_id: int, execution_id: int):
    """异步执行作业任务"""
    from database.session import SessionLocal
    
    db = SessionLocal()
    try:
        # 获取作业和执行记录
        job = db.query(Job).filter(Job.id == job_id).first()
        execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
        
        if not job or not execution:
            return
            
        try:
            # TODO: 根据作业类型执行相应的任务
            # 这里需要实现具体的任务执行逻辑
            
            # 更新执行记录
            execution.status = "completed"
            execution.end_time = datetime.utcnow()
            execution.result = {"message": "执行成功"}
            
        except Exception as e:
            # 更新执行记录
            execution.status = "failed"
            execution.end_time = datetime.utcnow()
            execution.error_message = str(e)
            
        # 更新作业状态
        job.last_run_at = execution.end_time
        job.status = "active"
        
        db.commit()
        
    finally:
        db.close() 