from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from app.models.job import Job, JobExecution
from app.schemas.job import JobCreate, JobUpdate
from celery import shared_task

class JobService:
    def __init__(self, db: Session):
        self.db = db

    def get_jobs(
        self,
        skip: int = 0,
        limit: int = 10,
        name: Optional[str] = None,
        job_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Job]:
        """获取作业列表"""
        query = self.db.query(Job)
        
        if name:
            query = query.filter(Job.name.ilike(f"%{name}%"))
        if job_type:
            query = query.filter(Job.job_type == job_type)
        if status:
            query = query.filter(Job.status == status)
            
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
            parameters=job.parameters,
            schedule_config=job.schedule_config,
            created_by="system",  # TODO: 从当前用户获取
            updated_by="system"   # TODO: 从当前用户获取
        )
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def update_job(self, job_id: int, job: JobUpdate) -> Optional[Job]:
        """更新作业"""
        db_job = self.get_job(job_id)
        if not db_job:
            return None
            
        for key, value in job.dict(exclude_unset=True).items():
            setattr(db_job, key, value)
            
        db_job.updated_by = "system"  # TODO: 从当前用户获取
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
        """立即执行作业"""
        db_job = self.get_job(job_id)
        if not db_job:
            return False
            
        # 创建执行记录
        execution = JobExecution(
            job_id=job_id,
            status="running",
            start_time=datetime.utcnow()
        )
        self.db.add(execution)
        self.db.commit()
        
        # 异步执行作业
        execute_job_task.delay(job_id, execution.id)
        return True

    def pause_job(self, job_id: int) -> bool:
        """暂停作业"""
        db_job = self.get_job(job_id)
        if not db_job:
            return False
            
        db_job.status = "paused"
        db_job.updated_by = "system"  # TODO: 从当前用户获取
        self.db.commit()
        return True

    def resume_job(self, job_id: int) -> bool:
        """恢复作业"""
        db_job = self.get_job(job_id)
        if not db_job:
            return False
            
        db_job.status = "active"
        db_job.updated_by = "system"  # TODO: 从当前用户获取
        self.db.commit()
        return True

    def terminate_job(self, job_id: int) -> bool:
        """终止作业"""
        db_job = self.get_job(job_id)
        if not db_job:
            return False
            
        db_job.status = "terminated"
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
        return self.db.query(JobExecution)\
            .filter(JobExecution.job_id == job_id)\
            .order_by(desc(JobExecution.start_time))\
            .offset(skip)\
            .limit(limit)\
            .all()

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