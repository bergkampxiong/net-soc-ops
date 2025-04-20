from sqlalchemy import create_engine, text
from database.session import DATABASE_URL

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        try:
            # 重命名列
            connection.execute(text("""
                ALTER TABLE rpa_config_files
                RENAME COLUMN type TO template_type
            """))
            connection.commit()
            print("Successfully renamed type column to template_type")
        except Exception as e:
            print(f"Error renaming column: {e}")
            # 如果列不存在，忽略错误
            pass 