from database.models import User
from sqlalchemy.orm import Session
from database.session import get_db

def main():
    db = next(get_db())
    print('Fixing users with inconsistent 2FA state...')
    
    # 查找所有totp_enabled为True但totp_secret为None的用户
    users = db.query(User).filter(User.totp_enabled == True, User.totp_secret == None).all()
    
    for user in users:
        print(f'Fixing user {user.username}...')
        # 将totp_enabled设置为False
        user.totp_enabled = False
        db.commit()
        print(f'User {user.username} fixed.')
    
    print('Done.')
    
    # 显示所有用户的状态
    print('\nUsers in database:')
    for user in db.query(User).all():
        print(f'- {user.username} (role: {user.role}, totp_enabled: {user.totp_enabled}, totp_secret: {user.totp_secret is not None})')

if __name__ == "__main__":
    main() 