from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import os
import secrets

# 导入数据库模型和会话
from database.models import User, RefreshToken
from database.session import get_db

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 配置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# 可选认证：无 token 时不报错，用于仅需“有则识别用户”的接口（如设备连接列表）
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """生成密码哈希"""
    return pwd_context.hash(password)

def get_user(db: Session, username: str):
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int):
    """根据用户ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def authenticate_user(db: Session, username: str, password: str):
    """验证用户"""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前用户"""
    print(f"获取当前用户，令牌: {token[:10] if token else 'None'}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            print("令牌中没有 sub")
            raise credentials_exception
        print(f"从令牌中获取 sub: {sub}")
    except JWTError as e:
        print(f"JWT错误: {str(e)}")
        raise credentials_exception

    # sub 可能是 username（登录时）或 user.id（刷新 token 后），需兼容两种格式
    user = None
    if isinstance(sub, str) and sub.isdigit():
        user = get_user_by_id(db, int(sub))
    if user is None:
        user = get_user(db, username=str(sub))
    if user is None:
        print(f"找不到用户: sub={sub}")
        raise credentials_exception
    
    print(f"找到用户: {user.username}, 角色: {user.role}")
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选认证：有有效 token 则返回用户，无 token 或无效则返回 None（不抛 401）"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        user = None
        if isinstance(sub, str) and sub.isdigit():
            user = get_user_by_id(db, int(sub))
        if user is None:
            user = get_user(db, username=str(sub))
        return user
    except JWTError:
        return None


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def create_refresh_token(user_id: int, db: Session):
    """创建刷新令牌"""
    # 生成随机令牌
    token = secrets.token_urlsafe(32)
    
    # 设置过期时间（1天）
    expires_at = (datetime.utcnow() + timedelta(days=1)).isoformat()
    
    # 创建刷新令牌记录
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        is_revoked=False
    )
    
    db.add(refresh_token)
    db.commit()
    
    return token, expires_at

def verify_refresh_token(token: str, db: Session):
    """验证刷新令牌"""
    # 查询刷新令牌
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    
    if not refresh_token:
        return None
    
    # 检查是否已撤销
    if refresh_token.is_revoked:
        return None
    
    # 检查是否过期
    if datetime.fromisoformat(refresh_token.expires_at) < datetime.utcnow():
        return None
    
    # 获取用户
    user = db.query(User).filter(User.id == refresh_token.user_id).first()
    
    return user

def revoke_refresh_token(token: str, db: Session):
    """撤销刷新令牌"""
    # 查询刷新令牌
    refresh_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    
    if refresh_token:
        refresh_token.is_revoked = True
        db.commit()
        return True
    
    return False

def revoke_all_user_refresh_tokens(user_id: int, db: Session):
    """撤销用户的所有刷新令牌"""
    # 查询用户的所有刷新令牌
    refresh_tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).all()
    
    for token in refresh_tokens:
        token.is_revoked = True
    
    db.commit()
    return len(refresh_tokens) 