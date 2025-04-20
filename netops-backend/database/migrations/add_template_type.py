from sqlalchemy import create_engine, text
from database.session import DATABASE_URL

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        # 添加 template_type 列
        try:
            connection.execute(text("""
                ALTER TABLE config_files
                ADD COLUMN template_type VARCHAR DEFAULT 'jinja2'
            """))
            connection.commit()
            print("Successfully added template_type column")
        except Exception as e:
            print(f"Error adding template_type column: {e}")
            # 如果列已存在，忽略错误
            pass

if __name__ == "__main__":
    migrate() 