from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class LDAPTemplateBase(BaseModel):
    """LDAP模板基础模型"""
    name: str = Field(..., description="模板名称")
    server_url: str = Field(..., description="LDAP服务器地址")
    port: int = Field(default=389, description="LDAP服务器端口")
    bind_dn: str = Field(..., description="绑定DN")
    bind_password: str = Field(..., description="绑定密码")
    is_active: bool = Field(default=True, description="是否启用")

class LDAPTemplateCreate(LDAPTemplateBase):
    """创建LDAP模板请求模型"""
    pass

class LDAPTemplateUpdate(BaseModel):
    """更新LDAP模板请求模型"""
    name: Optional[str] = Field(None, description="模板名称")
    server_url: Optional[str] = Field(None, description="LDAP服务器地址")
    port: Optional[int] = Field(None, description="LDAP服务器端口")
    bind_dn: Optional[str] = Field(None, description="绑定DN")
    bind_password: Optional[str] = Field(None, description="绑定密码")
    is_active: Optional[bool] = Field(None, description="是否启用")

class LDAPTemplateInDB(LDAPTemplateBase):
    """数据库中的LDAP模板模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LDAPTemplateResponse(LDAPTemplateInDB):
    """LDAP模板响应模型"""
    pass

class LDAPTestRequest(BaseModel):
    """LDAP连接测试请求模型"""
    server_url: str = Field(..., description="LDAP服务器地址")
    port: int = Field(default=389, description="LDAP服务器端口")
    bind_dn: str = Field(..., description="绑定DN")
    bind_password: str = Field(..., description="绑定密码")
    use_ssl: bool = Field(default=False, description="是否使用SSL")

class LDAPTestResponse(BaseModel):
    """LDAP连接测试响应模型"""
    success: bool = Field(..., description="测试是否成功")
    message: str = Field(..., description="测试结果消息")

class LDAPConfigBase(BaseModel):
    """LDAP配置基础模型"""
    server_url: str = Field(..., description="LDAP服务器地址")
    bind_dn: str = Field(..., description="绑定DN")
    bind_password: str = Field(..., description="绑定密码")
    search_base: str = Field(..., description="搜索基础")
    use_ssl: bool = Field(default=False, description="是否使用SSL")

class LDAPConfigCreate(LDAPConfigBase):
    """LDAP配置创建模型"""
    pass

class LDAPConfigUpdate(LDAPConfigBase):
    """LDAP配置更新模型"""
    pass

class LDAPConfigResponse(LDAPConfigBase):
    """LDAP配置响应模型"""
    id: int = Field(..., description="配置ID")

    class Config:
        from_attributes = True 