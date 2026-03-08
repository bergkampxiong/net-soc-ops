# IP 管理模块 — Aggregates、Prefixes、DHCP 服务器/作用域/租约（PRD-IP管理功能）
# 与 config_module_models 共用 database.base.Base，表通过 int_all_db.py 初始化
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.sql import func
from database.base import Base
from utils.datetime_utils import utc_to_beijing_str


class IpamAggregate(Base):
    """IPAM 聚合：顶层 IP 地址块（如 10.0.0.0/8），彼此不能重叠。"""
    __tablename__ = "ipam_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    prefix = Column(String(64), nullable=False, unique=True, index=True, comment="CIDR，如 10.0.0.0/8")
    rir = Column(String(128), nullable=True, index=True, comment="分配机构，如 RFC 1918、APNIC")
    date_added = Column(Date, nullable=True, comment="分配/部署日期")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "prefix": self.prefix,
            "rir": self.rir,
            "date_added": self.date_added.isoformat() if self.date_added else None,
            "description": self.description,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class IpamPrefix(Base):
    """IPAM 网段：CIDR 网段，可归属某 Aggregate，可与 DHCP Scope 关联。"""
    __tablename__ = "ipam_prefixes"

    id = Column(Integer, primary_key=True, index=True)
    prefix = Column(String(64), nullable=False, index=True, comment="CIDR")
    status = Column(String(32), nullable=False, index=True, comment="active / reserved / deprecated / container")
    description = Column(Text, nullable=True)
    is_pool = Column(Boolean, nullable=True, default=False, server_default="0")
    mark_utilized = Column(Boolean, nullable=True, default=False, server_default="0")
    vlan_id = Column(Integer, nullable=True, index=True)
    location = Column(String(256), nullable=True, index=True)
    aggregate_id = Column(Integer, ForeignKey("ipam_aggregates.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "prefix": self.prefix,
            "status": self.status,
            "description": self.description,
            "is_pool": self.is_pool,
            "mark_utilized": self.mark_utilized,
            "vlan_id": self.vlan_id,
            "location": self.location,
            "aggregate_id": self.aggregate_id,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class DhcpServer(Base):
    """DHCP 服务器：由 WMI 或 Agent 同步到本地。"""
    __tablename__ = "dhcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=True, index=True, comment="DHCP 服务器名称/FQDN")
    type = Column(String(64), nullable=True, index=True, comment="如 Windows")
    ip_address = Column(String(64), nullable=True, index=True)
    failover_status = Column(String(64), nullable=True, comment="如 Enabled、Load Balance")
    location = Column(String(256), nullable=True, index=True)
    vlan_id = Column(Integer, nullable=True, index=True)
    num_scopes = Column(Integer, nullable=True, default=0, server_default="0")
    total_ips = Column(Integer, nullable=True, default=0, server_default="0")
    used_ips = Column(Integer, nullable=True, default=0, server_default="0")
    available_ips = Column(Integer, nullable=True, default=0, server_default="0")
    status = Column(String(32), nullable=True, index=True, comment="如 Up")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        total = self.total_ips or 0
        used = self.used_ips or 0
        pct = (used / total * 100) if total else 0
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "ip_address": self.ip_address,
            "failover_status": self.failover_status,
            "location": self.location,
            "vlan_id": self.vlan_id,
            "num_scopes": self.num_scopes,
            "total_ips": total,
            "used_ips": used,
            "available_ips": self.available_ips or 0,
            "percent_used": round(pct, 2),
            "status": self.status,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class DhcpScope(Base):
    """DHCP 作用域：属于某 DHCP 服务器，可关联 ipam_prefixes。"""
    __tablename__ = "dhcp_scopes"

    id = Column(Integer, primary_key=True, index=True)
    dhcp_server_id = Column(Integer, ForeignKey("dhcp_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(256), nullable=True, index=True)
    network_address = Column(String(64), nullable=True, index=True)
    mask_cidr = Column(String(64), nullable=True)
    failover_mode = Column(String(64), nullable=True)
    enabled = Column(Boolean, nullable=True, default=True, server_default="1")
    location = Column(String(256), nullable=True, index=True)
    vlan_id = Column(Integer, nullable=True, index=True)
    prefix_id = Column(Integer, ForeignKey("ipam_prefixes.id", ondelete="SET NULL"), nullable=True, index=True)
    total_ips = Column(Integer, nullable=True, default=0, server_default="0")
    used_ips = Column(Integer, nullable=True, default=0, server_default="0")
    available_ips = Column(Integer, nullable=True, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        total = self.total_ips or 0
        used = self.used_ips or 0
        pct = (used / total * 100) if total else 0
        return {
            "id": self.id,
            "dhcp_server_id": self.dhcp_server_id,
            "name": self.name,
            "network_address": self.network_address,
            "mask_cidr": self.mask_cidr,
            "failover_mode": self.failover_mode,
            "enabled": self.enabled,
            "location": self.location,
            "vlan_id": self.vlan_id,
            "prefix_id": self.prefix_id,
            "total_ips": total,
            "used_ips": used,
            "available_ips": self.available_ips or 0,
            "percent_used": round(pct, 2),
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class DhcpLease(Base):
    """DHCP 租约/保留：合并表，is_reservation 区分。"""
    __tablename__ = "dhcp_leases"

    id = Column(Integer, primary_key=True, index=True)
    scope_id = Column(Integer, ForeignKey("dhcp_scopes.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = Column(String(64), nullable=True, index=True)
    mac = Column(String(64), nullable=True, index=True)
    client_name = Column(String(256), nullable=True)
    is_reservation = Column(Boolean, nullable=False, default=False, server_default="0")
    last_response = Column(DateTime(timezone=True), nullable=True)
    response_time = Column(Integer, nullable=True, comment="响应时间（秒或毫秒）")
    status = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "scope_id": self.scope_id,
            "ip_address": self.ip_address,
            "mac": self.mac,
            "client_name": self.client_name,
            "is_reservation": self.is_reservation,
            "last_response": utc_to_beijing_str(self.last_response) if self.last_response else None,
            "response_time": self.response_time,
            "status": self.status,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class NetboxImportConfig(Base):
    """NetBox 导入配置：URL 与 Token 存后端。"""
    __tablename__ = "netbox_import_config"

    id = Column(Integer, primary_key=True, index=True)
    base_url = Column(String(512), nullable=False, comment="NetBox 基础 URL")
    api_token = Column(String(256), nullable=True, comment="API Token")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "base_url": self.base_url,
            "api_token": "***" if self.api_token else None,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }


class DhcpWmiTarget(Base):
    """DHCP WMI 采集目标：Windows 主机 + WinRM 凭证，用于通过 WinRM 执行 PowerShell 读取 DHCP。"""
    __tablename__ = "dhcp_wmi_targets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=True, comment="目标名称")
    host = Column(String(256), nullable=False, index=True, comment="Windows 主机 IP 或主机名")
    port = Column(Integer, nullable=True, default=5985, server_default="5985", comment="WinRM 端口，5985/5986")
    username = Column(String(256), nullable=True, comment="WinRM 用户名")
    password = Column(String(512), nullable=True, comment="WinRM 密码")
    use_ssl = Column(Boolean, nullable=True, default=False, server_default="0", comment="是否 HTTPS WinRM")
    enabled = Column(Boolean, nullable=True, default=True, server_default="1", comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self, mask_password=True):
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": "***" if (mask_password and self.password) else self.password,
            "use_ssl": self.use_ssl,
            "enabled": self.enabled,
            "created_at": utc_to_beijing_str(self.created_at),
            "updated_at": utc_to_beijing_str(self.updated_at),
        }
