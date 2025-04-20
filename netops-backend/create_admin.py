from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from datetime import datetime

# 导入数据库模型
from database.models import Base, User

# 创建数据库连接
DATABASE_URL = "sqlite:///./netops.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    """生成密码哈希"""
    return pwd_context.hash(password)

def create_admin_user():
    """创建管理员用户"""
    db = SessionLocal()
    try:
        # 检查admin用户是否已存在
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if admin_user:
            print("管理员用户已存在，正在更新密码...")
            admin_user.hashed_password = get_password_hash("admin123")
            admin_user.is_active = True
            admin_user.role = "Admin"
        else:
            print("创建新的管理员用户...")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                role="Admin",
                password_changed_at=datetime.utcnow().isoformat()
            )
            db.add(admin_user)
        
        db.commit()
        print("管理员用户创建/更新成功！")
        print(f"用户名: admin")
        print(f"密码: admin123")
        print(f"角色: {admin_user.role}")
        
    except Exception as e:
        db.rollback()
        print(f"创建管理员用户时出错: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user() 