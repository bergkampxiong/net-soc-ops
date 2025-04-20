from database.models import User
from sqlalchemy.orm import Session
from database.session import get_db

def main():
    db = next(get_db())
    print('Users in database:')
    for user in db.query(User).all():
        print(f'- {user.username} (role: {user.role}, totp_enabled: {user.totp_enabled}, totp_secret: {user.totp_secret is not None})')

if __name__ == "__main__":
    main() 