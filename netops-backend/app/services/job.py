import json
import os
import subprocess
import tempfile
import time
import requests
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from typing import List, Optional, Tuple, Any
from datetime import datetime, timedelta
from app.models.job import Job, JobExecution
from app.schemas.job import JobCreate, JobUpdate, JobExecutionCreate
from app.process_designer.code_generator import CodeGenerator
from celery import shared_task
from fastapi import HTTPException

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

        # 渗透测试节点：调用后端 Strix API，轮询直至完成
        strix_base = os.environ.get("CONFIG_MODULE_API_URL", "http://127.0.0.1:8000/api").rstrip("/")
        strix_scan_ids: List[int] = []
        for pn in penetration_nodes:
            data = pn.get("data") or {}
            target_source = data.get("targetSource") or "inline"
            target_node_id = data.get("targetNodeId")
            targets = []
            if target_source == "targetNode" and target_node_id:
                target_node = next((n for n in nodes if n.get("id") == target_node_id), None)
                if target_node:
                    td = (target_node.get("data") or {}).get("targets")
                    if isinstance(td, list):
                        targets = [str(t) for t in td]
                    elif td:
                        targets = [str(td)]
            if not targets:
                inline = data.get("targets")
                if isinstance(inline, list):
                    targets = [str(t) for t in inline]
                elif inline:
                    targets = [str(inline)]
                elif data.get("targetValue"):
                    targets = [str(data["targetValue"])]
            if not targets:
                script_logs += "\n[渗透测试] 跳过节点: 无目标\n"
                continue
            try:
                r = requests.post(
                    f"{strix_base}/config-module/strix/scans",
                    json={
                        "target_type": data.get("targetType") or "web_url",
                        "targets": targets,
                        "instruction": data.get("instruction") or None,
                        "scan_mode": data.get("scanMode") or "deep",
                        "job_execution_id": execution_id,
                    },
                    timeout=30,
                )
                r.raise_for_status()
                body = r.json()
                scan_id = body.get("id")
                if scan_id is not None:
                    strix_scan_ids.append(scan_id)
                script_logs += f"\n[渗透测试] 已创建扫描 id={scan_id}\n"
                # 轮询直至非 pending/running（最多约 1 小时）
                for _ in range(360):
                    time.sleep(10)
                    r2 = requests.get(f"{strix_base}/config-module/strix/scans/{scan_id}", timeout=10)
                    r2.raise_for_status()
                    st = (r2.json() or {}).get("status") or ""
                    if st not in ("pending", "running"):
                        script_logs += f"[渗透测试] 扫描 {scan_id} 状态: {st}\n"
                        break
            except Exception as e:
                script_logs += f"\n[渗透测试] 节点执行异常: {e}\n"

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