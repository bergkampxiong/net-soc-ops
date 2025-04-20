from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
from typing import Optional

from database.session import get_db
from database.models import User, UsedTOTP, RefreshToken
from schemas.user import Token
from auth.authentication import (
    authenticate_user, create_access_token, get_current_active_user,
    create_refresh_token, verify_refresh_token, revoke_refresh_token, revoke_all_user_refresh_tokens,
    verify_password, ACCESS_TOKEN_EXPIRE_MINUTES
)
from auth.ldap_auth import ldap_authenticate
from auth.totp import setup_totp, generate_qr_code, verify_totp
from auth.audit import log_event
from config import settings

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class LoginForm(OAuth2PasswordRequestForm):
    """扩展的登录表单，支持TOTP验证码"""
    def __init__(
        self,
        username: str = Body(...),
        password: str = Body(...),
        totp_code: Optional[str] = Body(None),
        grant_type: Optional[str] = Body(None),
        scope: str = Body(""),
        client_id: Optional[str] = Body(None),
        client_secret: Optional[str] = Body(None),
    ):
        self.username = username
        self.password = password
        self.totp_code = totp_code
        self.grant_type = grant_type
        self.scope = scope
        self.client_id = client_id
        self.client_secret = client_secret

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    # 获取用户
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # 检查用户是否存在
    if not user:
        # 尝试LDAP认证
        ldap_user, ldap_error = ldap_authenticate(form_data.username, form_data.password, db)
        
        if ldap_user:
            # LDAP认证成功
            user = ldap_user
            
            # 检查是否需要2FA
            if user.has_2fa:
                # 返回需要2FA的标志
                log_event(
                    db=db,
                    event_type="ldap_login_2fa_required",
                    user=user,
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent"),
                    success=True
                )
                return {"access_token": f"2FA_REQUIRED_{user.username}", "token_type": "bearer"}
            
            # 创建访问令牌
            access_token = create_access_token(
                data={"sub": user.username}
            )
            
            # 创建刷新令牌
            refresh_token, expires_at = create_refresh_token(
                user_id=user.id,
                db=db
            )
            
            # 更新最后登录时间
            user.last_login = datetime.utcnow().isoformat()
            db.commit()
            
            # 记录登录成功事件
            log_event(
                db=db,
                event_type="ldap_login_success",
                user=user,
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                success=True
            )
            
            # 返回令牌
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "refresh_token": refresh_token,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        else:
            # LDAP认证失败
            log_event(
                db=db,
                event_type="login_failed",
                username=form_data.username,
                ip_address=client_ip,
                details={"reason": "用户名或密码错误", "ldap_error": ldap_error},
                success=False
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
    
    # 如果是LDAP用户，尝试LDAP认证
    if user.is_ldap_user:
        ldap_user, ldap_error = ldap_authenticate(form_data.username, form_data.password, db)
        
        if not ldap_user:
            # LDAP认证失败
            log_event(
                db=db,
                event_type="ldap_login_failed",
                user=user,
                ip_address=client_ip,
                details={"reason": ldap_error},
                success=False
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LDAP认证失败: " + ldap_error
            )
        
        # 检查是否需要2FA
        if user.has_2fa:
            # 返回需要2FA的标志
            log_event(
                db=db,
                event_type="ldap_login_2fa_required",
                user=user,
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                success=True
            )
            return {"access_token": f"2FA_REQUIRED_{user.username}", "token_type": "bearer"}
        
        # 创建访问令牌
        access_token = create_access_token(
            data={"sub": user.username}
        )
        
        # 创建刷新令牌
        refresh_token, expires_at = create_refresh_token(
            user_id=user.id,
            db=db
        )
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow().isoformat()
        db.commit()
        
        # 记录登录成功事件
        log_event(
            db=db,
            event_type="ldap_login_success",
            user=user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        # 返回令牌
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    # 本地用户认证
    # 检查密码是否正确
    if not verify_password(form_data.password, user.hashed_password):
        # 记录失败的登录尝试
        log_event(
            db=db,
            event_type="login_failed",
            username=form_data.username,
            ip_address=client_ip,
            details={"reason": "密码错误"},
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 检查是否是首次登录
    is_first_login = not user.last_login

    # 如果是首次登录，需要修改密码
    if is_first_login:
        # 创建临时访问令牌
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=15)  # 临时令牌15分钟有效期
        )
        
        # 记录首次登录事件
        log_event(
            db=db,
            event_type="first_login",
            user=user,
            ip_address=client_ip,
            details={"ip": client_ip}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "is_first_login": True
        }

    # 如果启用了2FA但未提供验证码
    if user.has_2fa and not form_data.totp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要2FA验证码"
        )

    # 如果启用了2FA，验证TOTP
    if user.has_2fa:
        if not verify_totp(user.totp_secret, form_data.totp_code):
            log_event(
                db=db,
                event_type="2fa_failed",
                user=user,
                ip_address=client_ip,
                details={"ip": client_ip},
                success=False
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA验证码错误"
            )

    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": user.username}
    )
    
    # 创建刷新令牌
    refresh_token, expires_at = create_refresh_token(
        user_id=user.id,
        db=db
    )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow().isoformat()
    db.commit()
    
    # 记录登录成功事件
    log_event(
        db=db,
        event_type="login_success",
        user=user,
        ip_address=client_ip,
        details={"ip": client_ip}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "is_first_login": False
    }

@router.post("/ldap-login")
async def ldap_login(
    request: Request,
    username: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    """LDAP用户登录"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    user, error = ldap_authenticate(username, password, db)
    
    if not user:
        log_event(
            db=db,
            event_type="ldap_login",
            username=username,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=False,
            details={"reason": error}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查是否需要2FA
    if user.has_2fa:
        # 返回需要2FA的标志
        log_event(
            db=db,
            event_type="ldap_login_2fa_required",
            user=user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        return {"access_token": f"2FA_REQUIRED_{user.username}", "token_type": "bearer"}
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # 创建刷新令牌
    refresh_token, refresh_token_expires = create_refresh_token(user.id, db)
    
    log_event(
        db=db,
        event_type="ldap_login",
        user=user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "expires_in": 1800  # 30分钟，单位秒
    }

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """用户登出"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    # 这里可以实现令牌黑名单等功能
    
    log_event(
        db=db,
        event_type="logout",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True
    )
    
    return {"detail": "Successfully logged out"}

@router.get("/verify")
async def verify_token(current_user: User = Depends(get_current_active_user)):
    """验证令牌"""
    return {"username": current_user.username, "role": current_user.role}

@router.post("/totp-setup")
async def setup_totp_endpoint(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """设置TOTP"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    totp_data = setup_totp(current_user, db)
    
    log_event(
        db=db,
        event_type="totp_setup",
        user=current_user,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True
    )
    
    return totp_data

@router.get("/totp-qrcode")
async def get_totp_qrcode(
    uri: str
):
    """获取TOTP QR码"""
    return generate_qr_code(uri)

@router.post("/totp-verify")
async def verify_totp_endpoint(
    request: Request,
    totp_code: str = Body(...),
    username: str = Body(...),
    db: Session = Depends(get_db)
):
    """验证TOTP"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    try:
        print(f"Verifying TOTP for user: {username}, code: {totp_code}")
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User not found: {username}")
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.totp_secret:
            print(f"User {username} has no TOTP secret")
            raise HTTPException(status_code=400, detail="TOTP not set up for this user")
        
        if not verify_totp(user, totp_code, db):
            print(f"Invalid TOTP code for user: {username}")
            log_event(
                db=db,
                event_type="totp_verify",
                user=user,
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                success=False,
                details={"reason": "Invalid TOTP code"}
            )
            raise HTTPException(status_code=401, detail="Invalid TOTP code")
        
        # 如果用户还没有启用TOTP，则启用它
        if not user.has_2fa:
            print(f"Enabling TOTP for user: {username}")
            user.has_2fa = True
            db.commit()
            
            log_event(
                db=db,
                event_type="totp_enabled",
                user=user,
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                success=True
            )
        
        # 验证成功，创建访问令牌
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        # 创建刷新令牌
        refresh_token, refresh_token_expires = create_refresh_token(user.id, db)
        
        # 更新用户最后登录时间
        user.last_login = datetime.utcnow().isoformat()
        db.commit()
        
        log_event(
            db=db,
            event_type="totp_verify",
            user=user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        print(f"TOTP verification successful for user: {username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "expires_in": 1800  # 30分钟，单位秒
        }
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"Error verifying TOTP for user {username}: {str(e)}")
        # 记录失败事件
        try:
            user = db.query(User).filter(User.username == username).first()
            if user:
                log_event(
                    db=db,
                    event_type="totp_verify",
                    user=user,
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent"),
                    success=False,
                    details={"error": str(e)}
                )
        except Exception as log_error:
            print(f"Error logging event: {str(log_error)}")
        
        # 抛出通用错误
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/token/refresh")
async def refresh_access_token(
    request: Request,
    refresh_token: str = Form(...),
    db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    try:
        # 验证刷新令牌
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )
            
        # 检查令牌是否被撤销
        if await is_token_revoked(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已被撤销"
            )
            
        # 获取用户信息
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
            
        # 生成新的访问令牌
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

@router.post("/token/revoke")
async def revoke_token(
    request: Request,
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    """撤销指定的令牌"""
    try:
        # 验证令牌
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )
            
        # 检查令牌是否已经被撤销
        if await is_token_revoked(token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="令牌已经被撤销"
            )
            
        # 获取用户信息
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
            
        # 撤销令牌
        await revoke_token_internal(token)
        
        return {"message": "令牌已撤销"}
        
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

@router.post("/token/revoke-all")
async def revoke_all_tokens(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """撤销用户的所有令牌"""
    try:
        # 获取用户的所有有效令牌
        tokens = await get_user_tokens(str(current_user.id))
        
        # 撤销所有令牌
        for token in tokens:
            await revoke_token_internal(token)
            
        return {"message": "所有令牌已撤销"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/totp-setup-for-user")
async def setup_totp_for_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """为指定用户设置TOTP"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    try:
        # 打印请求信息
        body = await request.body()
        print(f"Request body: {body}")
        print(f"Request headers: {request.headers}")
        
        # 解析请求体
        form_data = await request.form()
        username = form_data.get('username')
        
        if not username:
            # 尝试从JSON中获取
            try:
                json_data = await request.json()
                username = json_data.get('username')
            except:
                pass
        
        if not username:
            print("Username not provided in request")
            raise HTTPException(status_code=422, detail="Username is required")
        
        print(f"Setting up TOTP for user: {username}, type: {type(username)}")
        
        # 确保username是字符串类型
        if not isinstance(username, str):
            print(f"Username is not a string: {username}, type: {type(username)}")
            username = str(username)
            print(f"Converted username to string: {username}")
        
        # 查找用户
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User not found: {username}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # 检查用户是否已经完全设置了2FA
        if user.has_2fa and user.totp_secret:
            print(f"User {username} already has TOTP fully enabled")
            raise HTTPException(status_code=400, detail="User already has 2FA enabled")
        
        # 设置TOTP
        totp_data = setup_totp(user, db)
        
        log_event(
            db=db,
            event_type="totp_setup",
            user=user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        print(f"TOTP setup successful for user: {username}")
        return totp_data
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"Error setting up TOTP for user {username}: {str(e)}")
        # 记录失败事件
        try:
            user = db.query(User).filter(User.username == username).first()
            if user:
                log_event(
                    db=db,
                    event_type="totp_setup",
                    user=user,
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent"),
                    success=False,
                    details={"error": str(e)}
                )
        except Exception as log_error:
            print(f"Error logging event: {str(log_error)}")
        
        # 抛出通用错误
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/direct-totp-setup")
async def direct_totp_setup(
    request: Request,
    username: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    """直接设置TOTP，不需要用户登录，只需要用户名和密码"""
    # 获取客户端IP
    client_ip = request.state.client_ip if hasattr(request.state, 'client_ip') else request.client.host
    
    try:
        print(f"Direct TOTP setup for user: {username}")
        
        # 验证用户身份
        user = authenticate_user(db, username, password)
        if not user:
            print(f"Authentication failed for user: {username}")
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        # 检查用户是否已经设置了TOTP
        if user.has_2fa:
            print(f"User {username} already has TOTP enabled")
            raise HTTPException(status_code=400, detail="TOTP already enabled for this user")
        
        # 设置TOTP
        totp_data = setup_totp(user, db)
        
        log_event(
            db=db,
            event_type="totp_setup",
            user=user,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        print(f"Direct TOTP setup successful for user: {username}")
        return totp_data
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"Error in direct TOTP setup for user {username}: {str(e)}")
        # 记录失败事件
        try:
            user = db.query(User).filter(User.username == username).first()
            if user:
                log_event(
                    db=db,
                    event_type="totp_setup",
                    user=user,
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent"),
                    success=False,
                    details={"error": str(e)}
                )
        except Exception as log_error:
            print(f"Error logging event: {str(log_error)}")
        
        # 抛出通用错误
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "department": current_user.department,
        "is_active": current_user.is_active,
        "is_ldap_user": current_user.is_ldap_user,
        "has_2fa": current_user.has_2fa,
        "last_login": current_user.last_login
    } 