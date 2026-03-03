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
    """合规策略：规则类型与内容。"""
    __tablename__ = "config_compliance_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="策略名称")
    rule_type = Column(String(32), nullable=False, comment="must_contain / must_not_contain / regex")
    rule_content = Column(Text, nullable=False, comment="规则内容")
    device_type = Column(String(64), nullable=True, index=True, comment="适用设备类型")
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "rule_content": self.rule_content,
            "device_type": self.device_type,
            "description": self.description,
            "created_at": utc_to_beijing_str(self.created_at),
        }


class ConfigComplianceResult(Base):
    """合规执行结果：某次对某备份执行某策略的结果。"""
    __tablename__ = "config_compliance_results"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("config_compliance_policies.id"), nullable=False, index=True)
    backup_id = Column(Integer, ForeignKey("config_module_backups.id"), nullable=True, index=True)
    device_id = Column(String(64), nullable=True, index=True)
    passed = Column(Boolean, nullable=False)
    detail = Column(Text, nullable=True, comment="说明或匹配片段")
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "backup_id": self.backup_id,
            "device_id": self.device_id,
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
