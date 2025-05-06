from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class JobBase(BaseModel):
    """作业基础模型"""
    name: str
    description: Optional[str] = None
    job_type: str
    parameters: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None

class JobCreate(JobBase):
    """创建作业模型"""
    pass

class JobUpdate(JobBase):
    """更新作业模型"""
    status: Optional[str] = None

class JobResponse(JobBase):
    """作业响应模型"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_by: str
    updated_by: str

    class Config:
        orm_mode = True

class JobExecutionBase(BaseModel):
    """作业执行记录基础模型"""
    job_id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: Optional[str] = None

class JobExecutionCreate(JobExecutionBase):
    """创建作业执行记录模型"""
    pass

class JobExecutionResponse(JobExecutionBase):
    """作业执行记录响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True 