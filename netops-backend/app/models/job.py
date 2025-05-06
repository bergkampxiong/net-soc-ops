from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.base import Base
import datetime

class Job(Base):
    """作业模型"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="作业名称")
    description = Column(Text, nullable=True, comment="作业描述")
    job_type = Column(String(50), nullable=False, comment="作业类型")
    status = Column(String(20), nullable=False, default="created", comment="作业状态")
    parameters = Column(JSON, nullable=True, comment="执行参数")
    schedule_config = Column(JSON, nullable=True, comment="调度配置")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="更新时间")
    last_run_at = Column(DateTime, nullable=True, comment="最后执行时间")
    next_run_at = Column(DateTime, nullable=True, comment="下次执行时间")
    created_by = Column(String(50), nullable=False, comment="创建人")
    updated_by = Column(String(50), nullable=False, comment="更新人")

    # 关联关系
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")

class JobExecution(Base):
    """作业执行记录模型"""
    __tablename__ = "job_executions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    status = Column(String(20), nullable=False, comment="执行状态")
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    result = Column(JSON, nullable=True, comment="执行结果")
    error_message = Column(Text, nullable=True, comment="错误信息")
    logs = Column(Text, nullable=True, comment="执行日志")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="更新时间")

    # 关联关系
    job = relationship("Job", back_populates="executions") 