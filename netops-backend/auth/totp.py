import pyotp
import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import random
import string
from datetime import datetime, timedelta

from database.models import User, UsedTOTP

def generate_totp_secret():
    """生成TOTP密钥"""
    return pyotp.random_base32()

def generate_backup_codes(count=10):
    """生成备用验证码"""
    codes = []
    for _ in range(count):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        codes.append(code)
    return codes

def setup_totp(user: User, db: Session):
    """设置TOTP"""
    # 生成TOTP密钥
    totp_secret = generate_totp_secret()
    user.totp_secret = totp_secret
    
    # 生成备用验证码
    backup_codes = generate_backup_codes()
    user.backup_codes = json.dumps(backup_codes)
    
    # 注意：这里不设置totp_enabled，需要用户验证后才能启用
    # user.totp_enabled = True
    
    # 更新数据库
    db.commit()
    
    # 生成TOTP URI
    totp = pyotp.TOTP(totp_secret)
    uri = totp.provisioning_uri(name=user.username, issuer_name="NetOps Platform")
    
    return {
        "secret": totp_secret,
        "uri": uri,
        "backup_codes": backup_codes
    }

def generate_qr_code(uri: str):
    """生成QR码"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 将图像保存到内存中
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    # 返回流式响应
    return StreamingResponse(img_io, media_type="image/png")

def verify_totp(user: User, totp_code: str, db: Session):
    """验证TOTP"""
    if not user.totp_secret:
        return False
    
    # 检查是否已使用过该TOTP码
    used_totp = db.query(UsedTOTP).filter(
        UsedTOTP.user_id == user.id,
        UsedTOTP.totp_code == totp_code
    ).first()
    
    if used_totp:
        return False
    
    # 验证TOTP码
    totp = pyotp.TOTP(user.totp_secret)
    valid = totp.verify(totp_code, valid_window=1)  # 允许±1分钟的时间偏移
    
    if valid:
        # 记录已使用的TOTP码
        now = datetime.utcnow()
        used_totp = UsedTOTP(
            user_id=user.id,
            totp_code=totp_code,
            used_at=now.isoformat(),
            expires_at=(now + timedelta(days=7)).isoformat()  # 7天后过期
        )
        db.add(used_totp)
        db.commit()
    
    return valid

def verify_backup_code(user: User, backup_code: str, db: Session):
    """验证备用验证码"""
    if not user.backup_codes:
        return False
    
    backup_codes = json.loads(user.backup_codes)
    
    if backup_code in backup_codes:
        # 使用后删除备用验证码
        backup_codes.remove(backup_code)
        user.backup_codes = json.dumps(backup_codes)
        db.commit()
        return True
    
    return False 