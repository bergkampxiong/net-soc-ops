from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database.session import get_db
from app.models.job import Job, JobExecution
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobExecutionResponse
from app.services.job import JobService

router = APIRouter()

@router.get("/jobs", response_model=List[JobResponse])
def get_jobs(
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取作业列表"""
    return JobService(db).get_jobs(skip, limit, name, job_type, status)

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """获取作业详情"""
    job = JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    return job

@router.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    """创建作业"""
    return JobService(db).create_job(job)

@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job: JobUpdate, db: Session = Depends(get_db)):
    """更新作业"""
    updated_job = JobService(db).update_job(job_id, job)
    if not updated_job:
        raise HTTPException(status_code=404, detail="作业不存在")
    return updated_job

@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """删除作业"""
    success = JobService(db).delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"message": "作业已删除"}

@router.post("/jobs/{job_id}/execute")
def execute_job(job_id: int, db: Session = Depends(get_db)):
    """立即执行作业"""
    success = JobService(db).execute_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"message": "作业已开始执行"}

@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: int, db: Session = Depends(get_db)):
    """暂停作业"""
    success = JobService(db).pause_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"message": "作业已暂停"}

@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: int, db: Session = Depends(get_db)):
    """恢复作业"""
    success = JobService(db).resume_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"message": "作业已恢复"}

@router.post("/jobs/{job_id}/terminate")
def terminate_job(job_id: int, db: Session = Depends(get_db)):
    """终止作业"""
    success = JobService(db).terminate_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"message": "作业已终止"}

@router.get("/jobs/{job_id}/executions", response_model=List[JobExecutionResponse])
def get_job_executions(
    job_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取作业执行历史"""
    executions = JobService(db).get_job_executions(job_id, skip, limit)
    if not executions:
        raise HTTPException(status_code=404, detail="作业不存在")
    return executions 