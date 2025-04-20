from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import ldap
from database.session import get_db
from database.models import LDAPConfig as LDAPConfigModel
from routes.auth import get_current_active_user, User
import logging
import pytz
from datetime import datetime
from database.ldap_models import LDAPTemplate
from schemas.ldap import (
    LDAPTemplateCreate,
    LDAPTemplateUpdate,
    LDAPTemplateResponse,
    LDAPTestRequest,
    LDAPTestResponse,
    LDAPConfigCreate,
    LDAPConfigUpdate,
    LDAPConfigResponse
)
from auth.audit import log_event
from utils.ldap_utils import parse_ldap_url

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ldap",
    tags=["ldap"],
    responses={404: {"description": "Not found"}},
)

# 用于测试连接的简单模型
class LDAPTestConfig(BaseModel):
    server_url: str
    bind_dn: str
    bind_password: str
    search_base: str
    use_ssl: bool = False

class LDAPTestResponse(BaseModel):
    success: bool
    message: str
    server_info: Optional[dict] = None

class LDAPConfigBase(BaseModel):
    server_url: str
    bind_dn: str
    bind_password: str
    search_base: str
    use_ssl: bool = False

class LDAPConfigCreate(LDAPConfigBase):
    pass

class LDAPConfigUpdate(LDAPConfigBase):
    pass

class LDAPConfigResponse(LDAPConfigBase):
    id: int

    class Config:
        from_attributes = True

class LDAPSyncStatus(BaseModel):
    """LDAP同步状态响应模型"""
    last_sync_time: Optional[str] = None
    sync_status: str = "未同步"
    total_users: int = 0
    synced_users: int = 0
    error_message: Optional[str] = None

class LDAPUserInfo(BaseModel):
    """LDAP用户信息响应模型"""
    username: str
    email: Optional[str] = None
    department: Optional[str] = None
    displayName: Optional[str] = None

@router.get("/config", response_model=LDAPConfigResponse)
async def get_ldap_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取LDAP配置"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以查看LDAP配置"
        )
    
    config = db.query(LDAPConfigModel).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP配置"
        )
    
    return config

@router.post("/config", response_model=LDAPConfigResponse)
async def create_ldap_config(
    config: LDAPConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建LDAP配置"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以创建LDAP配置"
        )
    
    # 检查是否已存在配置
    existing_config = db.query(LDAPConfigModel).first()
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LDAP配置已存在，请使用PUT方法更新"
        )
    
    # 创建新配置
    new_config = LDAPConfigModel(**config.dict())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    # 记录审计日志
    log_event(
        db=db,
        event_type="create_ldap_config",
        user=current_user,
        details=f"创建LDAP配置: {config.server_url}"
    )
    
    return new_config

@router.put("/config/{config_id}", response_model=LDAPConfigResponse)
async def update_ldap_config(
    config_id: int,
    config: LDAPConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新LDAP配置"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以更新LDAP配置"
        )
    
    # 查找现有配置
    existing_config = db.query(LDAPConfigModel).filter(LDAPConfigModel.id == config_id).first()
    if not existing_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP配置"
        )
    
    # 更新配置
    for key, value in config.dict().items():
        setattr(existing_config, key, value)
    
    db.commit()
    db.refresh(existing_config)
    
    # 记录审计日志
    log_event(
        db=db,
        event_type="update_ldap_config",
        user=current_user,
        details=f"更新LDAP配置: {config.server_url}"
    )
    
    return existing_config

@router.delete("/config/{config_id}")
async def delete_ldap_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除LDAP配置"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除LDAP配置"
        )
    
    # 查找现有配置
    existing_config = db.query(LDAPConfigModel).filter(LDAPConfigModel.id == config_id).first()
    if not existing_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP配置"
        )
    
    # 删除配置
    db.delete(existing_config)
    db.commit()
    
    # 记录审计日志
    log_event(
        db=db,
        event_type="delete_ldap_config",
        user=current_user,
        details=f"删除LDAP配置: {existing_config.server_url}"
    )
    
    return {"message": "LDAP配置已删除"}

@router.post("/test-connection", response_model=LDAPTestResponse)
async def test_ldap_connection(config: LDAPTestConfig):
    """测试LDAP连接"""
    try:
        # 调用ldap_utils中的测试函数
        from utils.ldap_utils import test_ldap_connection as test_ldap
        
        result = test_ldap(
            server_url=config.server_url,
            bind_dn=config.bind_dn,
            bind_password=config.bind_password,
            search_base=config.search_base,
            use_ssl=config.use_ssl
        )
        
        return LDAPTestResponse(
            success=result["success"],
            message=result["message"],
            server_info=result.get("server_info")
        )
        
    except Exception as e:
        return LDAPTestResponse(
            success=False,
            message=f"LDAP连接测试失败: {str(e)}"
        )

@router.get("/sync-status", response_model=LDAPSyncStatus)
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取LDAP同步状态"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以查看LDAP同步状态"
        )
    
    # 从数据库获取同步状态
    sync_status = db.query(LDAPSyncStatus).first()
    if not sync_status:
        return LDAPSyncStatus()
    
    return sync_status

@router.post("/sync")
async def sync_ldap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """同步LDAP用户"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以同步LDAP用户"
        )
    
    # 获取LDAP配置
    config = db.query(LDAPConfigModel).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP配置"
        )
    
    # 执行LDAP同步
    # TODO: 实现LDAP同步逻辑
    
    return {"message": "LDAP同步已启动"}

@router.get("/templates", response_model=List[LDAPTemplateResponse])
async def list_ldap_templates(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """获取LDAP模板列表"""
    templates = db.query(LDAPTemplate).all()
    return templates

@router.post("/templates", response_model=LDAPTemplateResponse)
async def create_ldap_template(
    template: LDAPTemplateCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """创建LDAP模板"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以创建LDAP模板"
        )
    
    # 检查是否已存在同名模板
    existing_template = db.query(LDAPTemplate).filter(LDAPTemplate.name == template.name).first()
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已存在同名LDAP模板"
        )
    
    # 创建新模板
    new_template = LDAPTemplate(**template.dict())
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    # 记录审计日志
    log_event(
        db=db,
        event_type="create_ldap_template",
        user=current_user,
        details=f"创建LDAP模板: {template.name}"
    )
    
    return new_template

@router.get("/templates/{template_id}", response_model=LDAPTemplateResponse)
async def get_ldap_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """获取LDAP模板详情"""
    template = db.query(LDAPTemplate).filter(LDAPTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP模板"
        )
    
    return template

@router.put("/templates/{template_id}", response_model=LDAPTemplateResponse)
async def update_ldap_template(
    template_id: int,
    template_update: LDAPTemplateUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """更新LDAP模板"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以更新LDAP模板"
        )
    
    # 查找现有模板
    existing_template = db.query(LDAPTemplate).filter(LDAPTemplate.id == template_id).first()
    if not existing_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP模板"
        )
    
    # 检查是否与其他模板重名
    if template_update.name and template_update.name != existing_template.name:
        name_exists = db.query(LDAPTemplate).filter(
            LDAPTemplate.name == template_update.name,
            LDAPTemplate.id != template_id
        ).first()
        if name_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已存在同名LDAP模板"
            )
    
    # 更新模板
    for key, value in template_update.dict(exclude_unset=True).items():
        setattr(existing_template, key, value)
    
    db.commit()
    db.refresh(existing_template)
    
    # 记录审计日志
    log_event(
        db=db,
        event_type="update_ldap_template",
        user=current_user,
        details=f"更新LDAP模板: {existing_template.name}"
    )
    
    return existing_template

@router.delete("/templates/{template_id}")
async def delete_ldap_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """删除LDAP模板"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除LDAP模板"
        )
    
    # 查找现有模板
    existing_template = db.query(LDAPTemplate).filter(LDAPTemplate.id == template_id).first()
    if not existing_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP模板"
        )
    
    # 删除模板
    db.delete(existing_template)
    db.commit()
    
    # 记录审计日志
    log_event(
        db=db,
        event_type="delete_ldap_template",
        user=current_user,
        details=f"删除LDAP模板: {existing_template.name}"
    )
    
    return {"message": "LDAP模板已删除"}

@router.post("/test", response_model=LDAPTestResponse)
async def test_ldap_connection(
    test_request: LDAPTestRequest,
    current_user = Depends(get_current_active_user)
):
    """测试LDAP连接"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以测试LDAP连接"
        )
    
    try:
        # 调用ldap_utils中的测试函数
        from utils.ldap_utils import test_ldap_connection as test_ldap
        
        result = test_ldap(
            server_url=test_request.server_url,
            bind_dn=test_request.bind_dn,
            bind_password=test_request.bind_password,
            search_base=test_request.search_base,
            use_ssl=test_request.use_ssl
        )
        
        return LDAPTestResponse(
            success=result["success"],
            message=result["message"],
            server_info=result.get("server_info")
        )
        
    except Exception as e:
        return LDAPTestResponse(
            success=False,
            message=f"LDAP连接测试失败: {str(e)}"
        )

@router.get("/search", response_model=LDAPUserInfo)
async def search_ldap_user(
    username: str = Query(..., description="要搜索的用户名"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """搜索LDAP用户"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以搜索LDAP用户"
        )
    
    # 获取LDAP配置
    config = db.query(LDAPConfigModel).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到LDAP配置"
        )
    
    try:
        # 解析服务器地址
        server_info = parse_ldap_url(config.server_url)
        
        # 创建LDAP连接
        if config.use_ssl:
            conn = ldap.initialize(f"ldaps://{server_info['host']}:{server_info['port']}")
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        else:
            conn = ldap.initialize(f"ldap://{server_info['host']}:{server_info['port']}")
        
        # 设置连接选项
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        
        # 绑定到LDAP服务器
        conn.simple_bind_s(config.bind_dn, config.bind_password)
        
        # 构建搜索过滤器
        search_filter = f"(sAMAccountName={username})"
        
        # 搜索用户
        result = conn.search_s(
            config.search_base,
            ldap.SCOPE_SUBTREE,
            search_filter,
            ['mail', 'department', 'displayName']
        )
        
        # 关闭连接
        conn.unbind_s()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到LDAP用户"
            )
        
        # 提取用户信息
        user_info = result[0][1]  # 获取第一个结果的属性
        
        # 安全地获取属性值
        def get_attr_value(attr_name):
            if attr_name in user_info:
                values = user_info[attr_name]
                if values and len(values) > 0:
                    return values[0].decode('utf-8')
            return None
        
        return LDAPUserInfo(
            username=username,
            email=get_attr_value('mail'),
            department=get_attr_value('department'),
            displayName=get_attr_value('displayName')
        )
        
    except ldap.INVALID_CREDENTIALS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LDAP认证失败"
        )
    except ldap.SERVER_DOWN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP服务器连接失败"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索LDAP用户失败: {str(e)}"
        ) 