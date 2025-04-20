import sqlite3
import os
from datetime import datetime

def backup_database():
    """备份数据库到SQL文件"""
    # 创建备份目录
    backup_dir = "database_backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 生成备份文件名（包含时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"netops_backup_{timestamp}.sql")
    
    # 连接到数据库
    conn = sqlite3.connect('netops.db')
    
    # 打开备份文件
    with open(backup_file, 'w', encoding='utf-8') as f:
        # 遍历所有表
        for table in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            table_name = table[0]
            
            # 获取表结构
            f.write(f"\n-- 表结构: {table_name}\n")
            create_table_sql = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'").fetchone()[0]
            f.write(f"{create_table_sql};\n\n")
            
            # 获取表数据
            f.write(f"-- 表数据: {table_name}\n")
            rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
            for row in rows:
                # 处理每个字段的值
                values = []
                for value in row:
                    if value is None:
                        values.append('NULL')
                    elif isinstance(value, str):
                        # 转义单引号
                        value = value.replace("'", "''")
                        values.append(f"'{value}'")
                    else:
                        values.append(str(value))
                
                # 写入INSERT语句
                f.write(f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n")
            f.write("\n")
    
    # 关闭连接
    conn.close()
    
    print(f"数据库已备份到: {backup_file}")

if __name__ == "__main__":
    backup_database() 