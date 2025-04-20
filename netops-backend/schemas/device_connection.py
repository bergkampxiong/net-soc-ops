from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SSHConnectionBase(BaseModel):
    """SSH连接基础模型"""
    name: str = Field(..., description="连接配置名称")
    device_type: str = Field(..., description="设备类型")
    credential_id: int = Field(..., description="凭证ID")
    port: int = Field(default=22, description="SSH端口")
    enable_secret: Optional[str] = Field(None, description="Enable密码")
    global_delay_factor: int = Field(default=1, description="全局延迟因子")
    auth_timeout: int = Field(default=60, description="认证超时时间(秒)")
    banner_timeout: int = Field(default=20, description="Banner超时时间(秒)")
    fast_cli: bool = Field(default=False, description="是否启用快速CLI模式")
    session_timeout: int = Field(default=60, description="会话超时时间(秒)")
    conn_timeout: int = Field(default=20, description="连接超时时间(秒)")
    keepalive: int = Field(default=60, description="保活间隔(秒)")
    verbose: bool = Field(default=False, description="是否启用详细日志")
    description: Optional[str] = Field(None, description="描述")

class SSHConnectionCreate(SSHConnectionBase):
    """创建SSH连接请求模型"""
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")

class SSHConnectionUpdate(BaseModel):
    """更新SSH连接请求模型"""
    name: Optional[str] = Field(None, description="连接配置名称")
    device_type: Optional[str] = Field(None, description="设备类型")
    credential_id: Optional[int] = Field(None, description="凭证ID")
    port: Optional[int] = Field(None, description="SSH端口")
    enable_secret: Optional[str] = Field(None, description="Enable密码")
    global_delay_factor: Optional[int] = Field(None, description="全局延迟因子")
    auth_timeout: Optional[int] = Field(None, description="认证超时时间(秒)")
    banner_timeout: Optional[int] = Field(None, description="Banner超时时间(秒)")
    fast_cli: Optional[bool] = Field(None, description="是否启用快速CLI模式")
    session_timeout: Optional[int] = Field(None, description="会话超时时间(秒)")
    conn_timeout: Optional[int] = Field(None, description="连接超时时间(秒)")
    keepalive: Optional[int] = Field(None, description="保活间隔(秒)")
    verbose: Optional[bool] = Field(None, description="是否启用详细日志")
    description: Optional[str] = Field(None, description="描述")

class SSHConnectionResponse(BaseModel):
    """SSH连接响应模型"""
    id: int
    name: str
    device_type: str
    credential_id: str
    port: int
    enable_secret: Optional[str] = None
    global_delay_factor: int
    auth_timeout: int
    banner_timeout: int
    fast_cli: bool
    session_timeout: int
    conn_timeout: int
    keepalive: int
    verbose: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    username: Optional[str] = None
    password: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConnectionPoolBase(BaseModel):
    """连接池基础模型"""
    ssh_config_id: int = Field(..., description="SSH配置ID")
    max_connections: int = Field(default=5, description="最大连接数")
    min_connections: int = Field(default=1, description="最小连接数")
    idle_timeout: int = Field(default=300, description="空闲超时时间(秒)")
    connection_timeout: int = Field(default=30, description="连接超时时间(秒)")
    is_active: bool = Field(default=True, description="是否启用")

class ConnectionPoolCreate(ConnectionPoolBase):
    """创建连接池请求模型"""
    pass

class ConnectionPoolUpdate(BaseModel):
    """更新连接池请求模型"""
    max_connections: Optional[int] = Field(None, description="最大连接数")
    min_connections: Optional[int] = Field(None, description="最小连接数")
    idle_timeout: Optional[int] = Field(None, description="空闲超时时间(秒)")
    connection_timeout: Optional[int] = Field(None, description="连接超时时间(秒)")
    is_active: Optional[bool] = Field(None, description="是否启用")

class ConnectionPoolResponse(ConnectionPoolBase):
    """连接池响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConnectionStatsResponse(BaseModel):
    """连接池统计信息响应模型"""
    id: int
    pool_id: int
    current_connections: int = Field(default=0, description="当前连接数")
    total_connections: int = Field(default=0, description="总连接数")
    failed_connections: int = Field(default=0, description="失败连接数")
    last_used: Optional[datetime] = Field(None, description="最后使用时间")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 