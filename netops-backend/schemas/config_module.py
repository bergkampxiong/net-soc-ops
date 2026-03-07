# 配置管理模块 API 请求/响应模型
from pydantic import BaseModel
from typing import Optional


class BackupCreate(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    device_host: Optional[str] = None
    job_execution_id: Optional[str] = None  # 作业执行 ID
    content: str
    source: Optional[str] = None  # workflow / manual / api
    remark: Optional[str] = None


class BackupResponse(BaseModel):
    id: int
    device_id: str
    device_name: Optional[str] = None
    device_host: Optional[str] = None
    job_execution_id: Optional[str] = None
    source: Optional[str] = None
    remark: Optional[str] = None
    version_no: Optional[int] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    content: Optional[str] = None  # 仅详情接口返回

    class Config:
        from_attributes = True


class BackupListResponse(BaseModel):
    items: list
    total: int


class DiffResponse(BaseModel):
    diff_text: str
    id_a: int
    id_b: int


class SummaryStatsResponse(BaseModel):
    device_count: int
    backup_24h_success: int
    backup_24h_fail: int
    backup_7d_success: int
    backup_7d_fail: int
    change_count_7d: int
    compliance_pass_rate: Optional[float] = None


# ---------- 合规 ----------
class CompliancePolicyCreate(BaseModel):
    name: str
    rule_type: str  # must_contain / must_not_contain / regex
    rule_content: str
    device_type: Optional[str] = None
    description: Optional[str] = None


class CompliancePolicyUpdate(BaseModel):
    name: Optional[str] = None
    rule_type: Optional[str] = None
    rule_content: Optional[str] = None
    device_type: Optional[str] = None
    description: Optional[str] = None


class ComplianceRunRequest(BaseModel):
    backup_id: Optional[int] = None  # 指定备份
    device_id: Optional[str] = None   # 或按设备取最新备份
    policy_ids: Optional[list] = None  # 指定策略 id 列表，空则全部


# ---------- 服务终止 ----------
class EosInfoCreate(BaseModel):
    device_or_model: str
    eos_date: Optional[str] = None  # YYYY-MM-DD
    description: Optional[str] = None


class EosInfoUpdate(BaseModel):
    device_or_model: Optional[str] = None
    eos_date: Optional[str] = None
    description: Optional[str] = None
