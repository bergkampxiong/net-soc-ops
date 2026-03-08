# IP 管理模块 API 请求/响应模型（PRD-IP管理功能）
from pydantic import BaseModel
from typing import Optional, List


# ---------- Aggregates ----------
class AggregateCreate(BaseModel):
    prefix: str
    rir: Optional[str] = None
    date_added: Optional[str] = None  # YYYY-MM-DD
    description: Optional[str] = None


class AggregateUpdate(BaseModel):
    prefix: Optional[str] = None
    rir: Optional[str] = None
    date_added: Optional[str] = None
    description: Optional[str] = None


class AggregateListResponse(BaseModel):
    items: list
    total: int


class AvailableRangesResponse(BaseModel):
    items: List[str]  # CIDR 字符串列表


# ---------- Prefixes ----------
class PrefixCreate(BaseModel):
    prefix: str
    status: str  # active / reserved / deprecated / container
    description: Optional[str] = None
    is_pool: Optional[bool] = False
    mark_utilized: Optional[bool] = False
    vlan_id: Optional[int] = None
    location: Optional[str] = None
    aggregate_id: Optional[int] = None


class PrefixUpdate(BaseModel):
    prefix: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    is_pool: Optional[bool] = None
    mark_utilized: Optional[bool] = None
    vlan_id: Optional[int] = None
    location: Optional[str] = None
    aggregate_id: Optional[int] = None


class PrefixListResponse(BaseModel):
    items: list
    total: int


# ---------- NetBox 导入配置 ----------
class NetboxConfigBody(BaseModel):
    base_url: str
    api_token: Optional[str] = None
    api_credential_id: Optional[int] = None  # 引用凭证表 API 凭证，优先于 api_token


class NetboxImportBody(BaseModel):
    strategy: Optional[str] = "merge"  # merge | replace


class NetboxImportResult(BaseModel):
    aggregates_created: int = 0
    aggregates_updated: int = 0
    prefixes_created: int = 0
    prefixes_updated: int = 0
    message: str = ""


# ---------- DHCP Sync（Agent 或手动上报） ----------
class DhcpServerSyncItem(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    ip_address: Optional[str] = None
    failover_status: Optional[str] = None
    location: Optional[str] = None
    vlan_id: Optional[int] = None
    num_scopes: Optional[int] = None
    total_ips: Optional[int] = None
    used_ips: Optional[int] = None
    available_ips: Optional[int] = None
    status: Optional[str] = None


class DhcpScopeSyncItem(BaseModel):
    dhcp_server_id: Optional[int] = None
    server_name: Optional[str] = None  # 若按 name 匹配服务器时可填
    name: Optional[str] = None
    network_address: Optional[str] = None
    mask_cidr: Optional[str] = None
    failover_mode: Optional[str] = None
    enabled: Optional[bool] = True
    location: Optional[str] = None
    vlan_id: Optional[int] = None
    total_ips: Optional[int] = None
    used_ips: Optional[int] = None
    available_ips: Optional[int] = None


class DhcpLeaseSyncItem(BaseModel):
    scope_id: Optional[int] = None
    ip_address: Optional[str] = None
    mac: Optional[str] = None
    client_name: Optional[str] = None
    is_reservation: Optional[bool] = False
    last_response: Optional[str] = None
    response_time: Optional[int] = None
    status: Optional[str] = None


class DhcpSyncBody(BaseModel):
    servers: Optional[List[DhcpServerSyncItem]] = None
    scopes: Optional[List[DhcpScopeSyncItem]] = None
    leases: Optional[List[DhcpLeaseSyncItem]] = None


# ---------- DHCP WMI 采集目标 ----------
class DhcpWmiTargetCreate(BaseModel):
    name: Optional[str] = None
    host: str
    port: Optional[int] = 5985
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: Optional[bool] = False
    enabled: Optional[bool] = True
    windows_credential_id: Optional[int] = None  # 引用凭证表 Windows/域控凭证


class DhcpWmiTargetUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: Optional[bool] = None
    enabled: Optional[bool] = None
    windows_credential_id: Optional[int] = None


# ---------- Scope 关联 Prefix ----------
class ScopeLinkPrefixBody(BaseModel):
    prefix_id: Optional[int] = None  # 置空可解除关联


class DhcpScopesListResponse(BaseModel):
    items: list
    total: int


class DhcpLeasesListResponse(BaseModel):
    items: list
    total: int
