from sqlalchemy.orm import Session
from app.models.user import User
from app.services.auth_service import get_password_hash

def init_db(db: Session) -> None:
    # 检查是否已存在管理员用户
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        # 创建默认管理员用户
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Administrator",
            is_active=True,
            is_superuser=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin) 