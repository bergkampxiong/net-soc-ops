import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database.session import SessionLocal
from database.models import User
from auth.authentication import get_password_hash
from datetime import datetime

def create_admin_user():
    db = SessionLocal()
    try:
        # 检查是否已存在管理员用户
        admin = db.query(User).filter(User.username == "admin").first()
        if admin:
            print("Admin user already exists")
            return

        # 创建新的管理员用户
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),  # 默认密码
            is_active=True,
            is_ldap_user=False,
            role="Admin",
            department="IT",
            totp_enabled=False,
            password_changed_at=datetime.utcnow().isoformat()
        )
        
        db.add(admin_user)
        db.commit()
        print("Admin user created successfully")
        print("Username: admin")
        print("Password: admin123")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user() 