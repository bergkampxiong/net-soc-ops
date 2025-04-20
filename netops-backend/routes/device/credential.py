from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database.session import get_db
from database.category_models import Credential, CredentialType
from auth.authentication import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime
from database.device_connection_models import DeviceConnection

router = APIRouter(
    prefix="/api/device/credential",
    tags=["credential-management"]
)

# 凭证基础模型
class CredentialBase(BaseModel):
    name: str
    description: Optional[str] = None
    credential_type: CredentialType

# SSH密码凭证请求模型
class SSHPasswordCredentialCreate(CredentialBase):
    username: str
    password: str
    enable_password: Optional[str] = None

# API凭证请求模型
class APICredentialCreate(CredentialBase):
    api_key: str
    api_secret: str

# SSH密钥凭证请求模型
class SSHKeyCredentialCreate(CredentialBase):
    username: str
    private_key: str
    passphrase: Optional[str] = None

# 凭证响应模型
class CredentialResponse(CredentialBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: Optional[bool] = True
    username: Optional[str] = None
    api_key: Optional[str] = None
    private_key: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# 凭证更新模型
class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enable_password: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None

# 完整凭证响应模型（包含密码）
class FullCredentialResponse(CredentialResponse):
    password: Optional[str] = None
    enable_password: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# 获取所有凭证
@router.get("/", response_model=List[CredentialResponse])
async def get_credentials(
    skip: int = 0, 
    limit: int = 100, 
    credential_type: Optional[CredentialType] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取凭证列表"""
    query = db.query(Credential)
    
    if credential_type:
        query = query.filter(Credential.credential_type == credential_type)
    
    credentials = query.offset(skip).limit(limit).all()
    return credentials

# 获取单个凭证
@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取单个凭证详情"""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="凭证不存在"
        )
    return credential

# 创建SSH密码凭证
@router.post("/ssh-password", response_model=CredentialResponse)
async def create_ssh_password_credential(
    credential: SSHPasswordCredentialCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建SSH密码凭证"""
    # 检查名称是否已存在
    existing = db.query(Credential).filter(Credential.name == credential.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="凭证名称已存在"
        )
    
    # 创建凭证
    db_credential = Credential(
        name=credential.name,
        description=credential.description,
        credential_type=CredentialType.SSH_PASSWORD,
        username=credential.username,
        password=credential.password,
        enable_password=credential.enable_password
    )
    
    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)
    return db_credential

# 创建API凭证
@router.post("/api-key", response_model=CredentialResponse)
async def create_api_credential(
    credential: APICredentialCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建API凭证"""
    # 检查名称是否已存在
    existing = db.query(Credential).filter(Credential.name == credential.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="凭证名称已存在"
        )
    
    # 创建凭证
    db_credential = Credential(
        name=credential.name,
        description=credential.description,
        credential_type=CredentialType.API_KEY,
        api_key=credential.api_key,
        api_secret=credential.api_secret
    )
    
    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)
    return db_credential

# 创建SSH密钥凭证
@router.post("/ssh-key", response_model=CredentialResponse)
async def create_ssh_key_credential(
    credential: SSHKeyCredentialCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建SSH密钥凭证"""
    # 检查名称是否已存在
    existing = db.query(Credential).filter(Credential.name == credential.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="凭证名称已存在"
        )
    
    # 创建凭证
    db_credential = Credential(
        name=credential.name,
        description=credential.description,
        credential_type=CredentialType.SSH_KEY,
        username=credential.username,
        private_key=credential.private_key,
        passphrase=credential.passphrase
    )
    
    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)
    return db_credential

# 更新凭证
@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: int,
    credential_update: CredentialUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新凭证"""
    # 获取凭证
    db_credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not db_credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="凭证不存在"
        )
    
    # 如果更新名称，检查是否已存在
    if credential_update.name and credential_update.name != db_credential.name:
        existing = db.query(Credential).filter(Credential.name == credential_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="凭证名称已存在"
            )
    
    # 更新字段
    update_data = credential_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_credential, key, value)
    
    db_credential.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_credential)
    return db_credential

# 删除凭证
@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """删除凭证"""
    # 获取凭证
    db_credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not db_credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="凭证不存在"
        )
    
    # 检查是否有设备连接使用此凭证
    device_connections = db.query(DeviceConnection).filter(
        DeviceConnection.credential_id == str(credential_id)
    ).all()
    
    if device_connections:
        # 如果有关联的设备连接，先删除它们
        for connection in device_connections:
            db.delete(connection)
        db.commit()
    
    # 删除凭证
    db.delete(db_credential)
    db.commit()
    return None

# 获取完整凭证信息（包含密码）
@router.get("/{credential_id}/full", response_model=FullCredentialResponse)
async def get_full_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取完整的凭证信息（包含密码）"""
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="凭证不存在"
        )
    return credential 