from pydantic import BaseModel, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_ldap_user: Optional[bool] = False

class UserCreate(UserBase):
    """用户创建模型"""
    password: Optional[str] = None
    role: Optional[str] = "user"
    department: Optional[str] = None
    has_2fa: Optional[bool] = False

class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: int
    role: str
    hashed_password: Optional[str] = None
    is_2fa_enabled: bool = False
    is_2fa_verified: bool = False

    class Config:
        orm_mode = True

class UserResponse(UserInDB):
    """用户响应模型"""
    pass

class UserOut(UserBase):
    id: int
    is_active: bool
    is_ldap_user: bool
    department: Optional[str]
    role: str
    has_2fa: bool
    last_login: Optional[str]
    
    class Config:
        orm_mode = True 