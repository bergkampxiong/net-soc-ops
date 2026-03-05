from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database.session import get_db
from app.models.job import Job, JobExecution
from app.schemas.job import (
    JobCreate, JobUpdate, JobResponse, JobExecutionResponse,
    JobExecutionListItem, JobExecutionListResponse, JobExecutionStatsResponse,
)
from app.services.job import JobService
from auth.authentication import get_current_user

router = APIRouter()


@router.get("/job-executions", response_model=JobExecutionListResponse)
def get_job_executions_cross(
    job_id: Optional[int] = Query(None, description="按作业ID筛选"),
    status: Optional[str] = Query(None, description="执行状态: completed | failed | running"),
    start_time_from: Optional[str] = Query(None, description="开始时间起 ISO 或 YYYY-MM-DD"),
    start_time_to: Optional[str] = Query(None, description="开始时间止 ISO 或 YYYY-MM-DD"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """跨作业执行列表，供作业监控与报告使用"""
    total, rows = JobService(db).get_job_executions_cross_job(
        job_id=job_id,
        status=status,
        start_time_from=start_time_from,
        start_time_to=start_time_to,
        skip=skip,
        limit=limit,
    )
    items = []
    for ex, job_name in rows:
        items.append(JobExecutionListItem(
            id=ex.id,
            job_id=ex.job_id,
            status=ex.status,
            start_time=ex.start_time,
            end_time=ex.end_time,
            result=ex.result,
            error_message=ex.error_message,
            logs=ex.logs,
            created_at=ex.created_at,
            updated_at=ex.updated_at,
            job_name=job_name,
        ))
    return JobExecutionListResponse(total=total, items=items)


@router.get("/job-executions/stats", response_model=JobExecutionStatsResponse)
def get_job_executions_stats(
    date_from: str = Query(..., description="统计起始日期 YYYY-MM-DD"),
    date_to: str = Query(..., description="统计结束日期 YYYY-MM-DD"),
    job_id: Optional[int] = Query(None, description="按作业ID筛选，不传为全部"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """执行统计，供作业监控概览卡片使用"""
    stats = JobService(db).get_job_executions_stats(
        date_from=date_from,
        date_to=date_to,
        job_id=job_id,
    )
    return JobExecutionStatsResponse(**stats)


@router.get("/jobs", response_model=List[JobResponse])
def get_jobs(
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    run_type: Optional[str] = Query(None, description="once | scheduled"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取作业列表（默认仅返回由流程发布产生的作业）"""
    return JobService(db).get_jobs(
        skip, limit, name, job_type, status,
        run_type=run_type,
        from_published_only=True,
    )

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """获取作业详情"""
    job = JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    return job

@router.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """创建作业"""
    return JobService(db).create_job(job)

@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job: JobUpdate, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """更新作业"""
    updated_job = JobService(db).update_job(job_id, job)
    if not updated_job:
        raise HTTPException(status_code=404, detail="作业不存在")
    return updated_job

@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """删除作业"""
    success = JobService(db).delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"message": "作业已删除"}

@router.post("/jobs/{job_id}/execute")
def execute_job(job_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """立即执行作业（需作业关联流程定义）"""
    job = JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    if not getattr(job, "process_definition_id", None):
        raise HTTPException(
            status_code=400,
            detail="该作业未关联流程，无法执行",
        )
    success = JobService(db).execute_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"message": "作业已开始执行"}

@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """暂停作业"""
    success = JobService(db).pause_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在或状态不正确")
    return {"message": "作业已暂停"}

@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """恢复作业"""
    success = JobService(db).resume_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在或状态不正确")
    return {"message": "作业已恢复"}

@router.post("/jobs/{job_id}/terminate")
def terminate_job(job_id: int, db: Session = Depends(get_db), _current_user=Depends(get_current_user)):
    """终止作业"""
    success = JobService(db).terminate_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="作业不存在或状态不正确")
    return {"message": "作业已终止"}

@router.get("/jobs/{job_id}/executions", response_model=List[JobExecutionResponse])
def get_job_executions(
    job_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取作业执行历史（无记录时返回空列表）"""
    job = JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    executions = JobService(db).get_job_executions(job_id, skip, limit)
    return executions 