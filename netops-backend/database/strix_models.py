# Strix 集成：扫描任务与 OpenAPI 配置
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from database.base import Base
from utils.datetime_utils import utc_to_beijing_str


class StrixScanTask(Base):
    """Strix 扫描任务：单次扫描的元数据与状态，供列表/详情/报告使用。"""
    __tablename__ = "strix_scan_tasks"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(64), nullable=True, comment="目标类型: web_url / git_url / local_path / domain_ip")
    target_value = Column(Text, nullable=True, comment="目标值 JSON 或文本，如 URL、路径、多目标")
    instruction = Column(Text, nullable=True, comment="自定义指令 --instruction")
    scan_mode = Column(String(32), nullable=True, default="deep", comment="quick / standard / deep")
    status = Column(String(32), nullable=False, default="pending", index=True,
                    comment="pending / running / success / failed / cancelled")
    run_name = Column(String(128), nullable=True, index=True, comment="Strix run 目录名")
    job_execution_id = Column(Integer, nullable=True, index=True, comment="关联作业执行 ID")
    created_by = Column(String(64), nullable=True, comment="创建人/系统标识")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True, comment="结束时间")
    summary = Column(Text, nullable=True, comment="摘要 JSON: 漏洞数、严重程度等")
    report_path = Column(Text, nullable=True, comment="报告文件路径（相对或绝对）")
    unified_report_path = Column(Text, nullable=True, comment="统一报告文件路径（由 int_all_db ensure 添加）")
    unified_report_generated_at = Column(DateTime(timezone=True), nullable=True, comment="统一报告生成时间（由 int_all_db ensure 添加）")

    def to_dict(self):
        import json
        d = {
            "id": self.id,
            "target_type": self.target_type,
            "target_value": self.target_value,
            "instruction": self.instruction,
            "scan_mode": self.scan_mode,
            "status": self.status,
            "run_name": self.run_name,
            "job_execution_id": self.job_execution_id,
            "created_by": self.created_by,
            "created_at": utc_to_beijing_str(self.created_at),
            "finished_at": utc_to_beijing_str(self.finished_at),
            "report_path": self.report_path,
            "unified_report_path": self.unified_report_path,
            "unified_report_generated_at": utc_to_beijing_str(self.unified_report_generated_at),
        }
        if self.summary:
            try:
                d["summary"] = json.loads(self.summary) if isinstance(self.summary, str) else self.summary
            except Exception:
                d["summary"] = None
        else:
            d["summary"] = None
        return d


class StrixConfig(Base):
    """Strix OpenAPI/LLM 配置：STRIX_LLM、LLM_API_KEY 等，执行时注入环境变量。"""
    __tablename__ = "strix_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(128), unique=True, nullable=False, index=True, comment="配置键")
    config_value = Column(Text, nullable=True, comment="配置值（敏感项存加密或脱敏）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self, mask_sensitive=True):
        val = self.config_value
        if mask_sensitive and self.config_key and "key" in self.config_key.lower() and val:
            val = "********"  # 不暴露任何字符，仅表示已配置
        return {
            "config_key": self.config_key,
            "config_value": val,
            "updated_at": utc_to_beijing_str(self.updated_at),
        }
