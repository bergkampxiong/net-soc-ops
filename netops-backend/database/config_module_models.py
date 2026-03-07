# 配置管理模块 — 设备配置备份、变更模板、合规、服务终止（与 rpa_config_files 等现有表独立）
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from database.base import Base
from utils.datetime_utils import utc_to_beijing_str


class ConfigModuleBackup(Base):
    """设备配置备份：存储从设备拉取的配置全文及元数据，供版本历史、对比、检索使用。"""
    __tablename__ = "config_module_backups"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), nullable=False, index=True, comment="设备标识")
    device_name = Column(String(128), nullable=True, comment="设备显示名")
    device_host = Column(String(128), nullable=True, index=True, comment="设备 IP/主机名")
    job_execution_id = Column(String(64), nullable=True, index=True, comment="作业执行 ID，与作业/流程关联")
    content = Column(Text, nullable=False, comment="配置全文")
    source = Column(String(32), nullable=True, comment="来源: workflow / manual / api")
    remark = Column(String(500), nullable=True, comment="备注")
    version_no = Column(Integer, nullable=True, comment="同设备下版本号")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(64), nullable=True, comment="创建人/系统标识")

    def to_dict(self, include_content=False):
        d = {
            "id": self.id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_host": self.device_host,
            "job_execution_id": self.job_execution_id,
            "source": self.source,
            "remark": self.remark,
            "version_no": self.version_no,
            "created_at": utc_to_beijing_str(self.created_at),
            "created_by": self.created_by,
        }
        if include_content:
            d["content"] = self.content
        return d


class ConfigChangeTemplate(Base):
    """配置变更模板：可复用变更片段，绑定设备类型与用途标签。独立于 rpa_config_files。"""
    __tablename__ = "config_module_change_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="模板名称")
    device_type = Column(String(64), nullable=True, index=True, comment="适用设备类型")
    content = Column(Text, nullable=False, comment="模板内容")
    tags = Column(String(256), nullable=True, comment="用途标签，逗号分隔")
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self, include_content=True):
        d = {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "tags": self.tags,
            "description": self.description,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }
        if include_content:
            d["content"] = self.content
        return d


class ConfigCompliancePolicy(Base):
    """合规策略：规则类型与内容；支持分组与启用状态。"""
    __tablename__ = "config_compliance_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="策略名称")
    rule_type = Column(String(32), nullable=False, comment="must_contain / must_not_contain / regex")
    rule_content = Column(Text, nullable=False, comment="规则内容")
    device_type = Column(String(64), nullable=True, index=True, comment="适用设备类型")
    description = Column(String(500), nullable=True)
    group = Column(String(128), nullable=True, index=True, comment="分组/文件夹")
    enabled = Column(Boolean, nullable=False, default=True, server_default="1", comment="启用状态")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "rule_content": self.rule_content,
            "device_type": self.device_type,
            "description": self.description,
            "group": self.group,
            "enabled": self.enabled,
            "created_at": utc_to_beijing_str(self.created_at),
        }


class ConfigComplianceSchedule(Base):
    """合规执行计划：关联报告，按 cron 或间隔自动执行。"""
    __tablename__ = "config_compliance_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="计划名称")
    report_id = Column(Integer, ForeignKey("config_compliance_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(32), nullable=False, comment="by_device_type / device_ids")
    target_device_ids = Column(Text, nullable=True, comment="JSON 数组，target_type=device_ids 时使用")
    cron_expr = Column(String(64), nullable=True, comment="Cron 表达式，与 interval_seconds 二选一")
    interval_seconds = Column(Integer, nullable=True, comment="执行间隔秒数，与 cron_expr 二选一")
    enabled = Column(Boolean, nullable=False, default=True, server_default="1", comment="是否启用")
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="上次执行时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "report_id": self.report_id,
            "target_type": self.target_type,
            "target_device_ids": self.target_device_ids,
            "cron_expr": self.cron_expr,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "last_run_at": utc_to_beijing_str(self.last_run_at) if self.last_run_at else None,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class ConfigComplianceReport(Base):
    """合规策略报告：名称、分组、适用设备类型、启用状态；不绑定设备，执行时指定目标。"""
    __tablename__ = "config_compliance_reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="报告名称")
    group = Column(String(128), nullable=True, index=True, comment="分组/文件夹")
    comments = Column(String(500), nullable=True, comment="说明")
    device_type = Column(String(64), nullable=True, index=True, comment="适用设备类型")
    enabled = Column(Boolean, nullable=False, default=True, server_default="1", comment="启用状态")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "group": self.group,
            "comments": self.comments,
            "device_type": self.device_type,
            "enabled": self.enabled,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class ConfigComplianceReportPolicy(Base):
    """报告与策略多对多关联。"""
    __tablename__ = "config_compliance_report_policies"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("config_compliance_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey("config_compliance_policies.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0", comment="排序")

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "policy_id": self.policy_id,
            "sort_order": self.sort_order,
        }


class ConfigComplianceResult(Base):
    """合规执行结果：某次对某备份执行某策略的结果。"""
    __tablename__ = "config_compliance_results"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("config_compliance_policies.id"), nullable=False, index=True)
    backup_id = Column(Integer, ForeignKey("config_module_backups.id"), nullable=True, index=True)
    device_id = Column(String(64), nullable=True, index=True)
    report_id = Column(Integer, ForeignKey("config_compliance_reports.id", ondelete="SET NULL"), nullable=True, index=True, comment="按报告执行时写入")
    passed = Column(Boolean, nullable=False)
    detail = Column(Text, nullable=True, comment="说明或匹配片段")
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "backup_id": self.backup_id,
            "device_id": self.device_id,
            "report_id": self.report_id,
            "passed": self.passed,
            "detail": self.detail,
            "executed_at": utc_to_beijing_str(self.executed_at),
        }


class ConfigEosInfo(Base):
    """服务终止：设备或型号的 EOS/EOL 信息。"""
    __tablename__ = "config_eos_info"

    id = Column(Integer, primary_key=True, index=True)
    device_or_model = Column(String(128), nullable=False, index=True, comment="设备标识或型号")
    eos_date = Column(String(32), nullable=True, comment="EOS 日期 YYYY-MM-DD")
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "device_or_model": self.device_or_model,
            "eos_date": self.eos_date,
            "description": self.description,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }
