import os
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.migrations.add_template_type import migrate as add_template_type

def run_migrations():
    """运行所有迁移脚本"""
    print("Starting database migrations...")
    
    # 按顺序运行迁移
    migrations = [
        ("Add template_type column", add_template_type),
    ]
    
    for name, migration in migrations:
        print(f"\nRunning migration: {name}")
        try:
            migration()
            print(f"Successfully completed migration: {name}")
        except Exception as e:
            print(f"Error in migration {name}: {e}")
            raise

if __name__ == "__main__":
    run_migrations() 