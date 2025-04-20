from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.user import User, RefreshToken
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(db: Session, user_id: int) -> str:
    token = jwt.encode(
        {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(days=30)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    db_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return token

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def verify_refresh_token(db: Session, token: str) -> Optional[User]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not refresh_token:
        return None
        
    return get_user_by_id(db, int(user_id)) 