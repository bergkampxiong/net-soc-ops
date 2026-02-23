from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os
import sys
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy.inspection import inspect

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 导入数据库配置和模型
from database.config import get_database_url
from database.base import Base
from database.cmdb_models import (
    CMDBBase, DeviceType, Vendor, Location, Department, 
    AssetStatus, Asset, NetworkDevice, Server, VirtualMachine, K8sCluster,
    SystemType
)
from database.models import User, UsedTOTP, RefreshToken
from database.category_models import Base as CategoryBase, Credential, CredentialType
from database.config_management_models import Base as ConfigBase
from database.device_connection_models import DeviceConnection
from app.models.job import Job, JobExecution

# 创建密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    """生成密码哈希"""
    return pwd_context.hash(password)

def init_system_data(db):
    """初始化系统数据"""
    try:
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
                is_superuser=True,
                role="admin"
            )
            db.add(admin)
            db.commit()
            print("系统管理员用户创建成功")
            
        # 初始化系统类型
        init_system_types(db)
            
    except Exception as e:
        print(f"系统数据初始化失败: {str(e)}")
        db.rollback()
        raise

def init_system_types(db):
    """初始化系统类型数据"""
    try:
        # 默认系统类型列表
        default_system_types = [
            "ruijie_os",
            "hp_comware",
            "huawei_vrpv8",
            "linux",
            "cisco_ios",
            "cisco_nxos",
            "cisco_xe",
            "cisco_xr",
            "paloalto_panos",
            "fortinet"
        ]
        
        # 检查并添加默认系统类型
        for system_type_name in default_system_types:
            existing_type = db.query(SystemType).filter(SystemType.name == system_type_name).first()
            if not existing_type:
                new_system_type = SystemType(
                    name=system_type_name,
                    description=f"默认系统类型: {system_type_name}",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                db.add(new_system_type)
        
        db.commit()
        print("系统类型初始化成功")
    except Exception as e:
        print(f"系统类型初始化失败: {str(e)}")
        db.rollback()
        raise

def init_cmdb_data(db):
    """初始化CMDB数据"""
    try:
        # 检查并添加version字段
        inspector = inspect(db.get_bind())
        if 'cmdb_assets' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('cmdb_assets')]
            if 'version' not in columns:
                with db.get_bind().connect() as conn:
                    conn.execute(text("ALTER TABLE cmdb_assets ADD COLUMN version VARCHAR(50)"))
                    conn.commit()
                print("已添加version列到cmdb_assets表")
            else:
                print("cmdb_assets表已存在且包含version列")
            
            # 检查并添加cpu_count、memory_capacity和storage_capacity字段
            if 'cpu_count' not in columns:
                with db.get_bind().connect() as conn:
                    conn.execute(text("ALTER TABLE cmdb_assets ADD COLUMN cpu_count INTEGER"))
                    conn.commit()
                print("已添加cpu_count列到cmdb_assets表")
            if 'memory_capacity' not in columns:
                with db.get_bind().connect() as conn:
                    conn.execute(text("ALTER TABLE cmdb_assets ADD COLUMN memory_capacity FLOAT"))
                    conn.commit()
                print("已添加memory_capacity列到cmdb_assets表")
            if 'storage_capacity' not in columns:
                with db.get_bind().connect() as conn:
                    conn.execute(text("ALTER TABLE cmdb_assets ADD COLUMN storage_capacity FLOAT"))
                    conn.commit()
                print("已添加storage_capacity列到cmdb_assets表")
        
        # 检查是否已有数据
        if db.query(DeviceType).count() == 0:
            # 添加设备类型
            device_types = [
                {"name": "Router", "description": "网络路由器设备"},
                {"name": "Switch", "description": "网络交换机设备"},
                {"name": "Firewall", "description": "网络安全设备"},
                {"name": "Server", "description": "物理服务器"},
                {"name": "Virtual Machine", "description": "虚拟服务器"},
                {"name": "K8s Cluster", "description": "Kubernetes集群"}
            ]
            for dt in device_types:
                now = datetime.utcnow().isoformat()
                db.add(DeviceType(
                    name=dt["name"],
                    description=dt["description"],
                    created_at=now,
                    updated_at=now
                ))
            
            # 添加厂商
            vendors = [
                {"name": "Cisco", "description": "Cisco Systems"},
                {"name": "Huawei", "description": "Huawei Technologies"},
                {"name": "H3C", "description": "H3C Technologies"},
                {"name": "Ruijie", "description": "Ruijie Networks"},
                {"name": "Palo Alto", "description": "Palo Alto Networks"},
                {"name": "Fortinet", "description": "Fortinet Inc."},
                {"name": "Dell", "description": "Dell Technologies"},
                {"name": "HP", "description": "Hewlett Packard"}
            ]
            for vendor in vendors:
                now = datetime.utcnow().isoformat()
                db.add(Vendor(
                    name=vendor["name"],
                    description=vendor["description"],
                    created_at=now,
                    updated_at=now
                ))
            
            # 添加位置
            locations = [
                {"name": "总部", "description": "公司总部"},
                {"name": "数据中心1", "description": "主数据中心"},
                {"name": "数据中心2", "description": "备用数据中心"},
                {"name": "分支机构1", "description": "主要分支机构"},
                {"name": "分支机构2", "description": "次要分支机构"}
            ]
            for loc in locations:
                now = datetime.utcnow().isoformat()
                db.add(Location(
                    name=loc["name"],
                    description=loc["description"],
                    created_at=now,
                    updated_at=now
                ))
            
            # 添加部门
            departments = [
                {"name": "IT", "description": "信息技术部"},
                {"name": "网络", "description": "网络运维部"},
                {"name": "安全", "description": "安全运维部"},
                {"name": "开发", "description": "软件开发部"},
                {"name": "运维", "description": "系统运维部"}
            ]
            for dept in departments:
                now = datetime.utcnow().isoformat()
                db.add(Department(
                    name=dept["name"],
                    description=dept["description"],
                    created_at=now,
                    updated_at=now
                ))
            
            # 添加资产状态
            statuses = [
                {"name": "使用中", "description": "资产正在使用中"},
                {"name": "库存中", "description": "资产在库存中"},
                {"name": "维护中", "description": "资产正在维护中"},
                {"name": "已退役", "description": "资产已退役"}
            ]
            for status in statuses:
                now = datetime.utcnow().isoformat()
                db.add(AssetStatus(
                    name=status["name"],
                    description=status["description"],
                    created_at=now,
                    updated_at=now
                ))
            
            # 添加示例资产
            example_asset = Asset(
                name="示例设备",
                asset_tag="ASSET-001",
                ip_address="192.168.1.1",
                serial_number="SN123456",
                device_type_id=1,
                vendor_id=1,
                department_id=1,
                location_id=1,
                status_id=1,
                owner="admin",
                version="1.0.0",
                cpu_count=4,
                memory_capacity=16.0,
                storage_capacity=500.0,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            db.add(example_asset)
            
            db.commit()
            print("CMDB基础数据初始化成功")
    except Exception as e:
        print(f"CMDB数据初始化失败: {str(e)}")
        db.rollback()
        raise

def init_device_connection_tables(engine):
    """初始化设备连接管理模块的表"""
    try:
        print("正在创建设备连接管理模块的表...")
        
        # 创建设备连接管理模块的表
        DeviceConnection.__table__.create(engine, checkfirst=True)
        
        # 检查device_connections表是否存在description和is_active列
        inspector = inspect(engine)
        if 'device_connections' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('device_connections')]
            if 'description' not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE device_connections ADD COLUMN description TEXT"))
                    conn.commit()
                print("已添加description列到device_connections表")
            else:
                print("device_connections表已存在且包含description列")
                
            if 'is_active' not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE device_connections ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                    conn.commit()
                print("已添加is_active列到device_connections表")
            else:
                print("device_connections表已存在且包含is_active列")
        
        print("设备连接管理模块的表创建完成")
            
    except Exception as e:
        print(f"设备连接管理模块的表初始化失败: {str(e)}")
        raise

def init_credential_tables(engine):
    """初始化凭证相关的表"""
    try:
        print("正在初始化凭证相关的表...")
        
        # 创建凭证表
        Credential.__table__.create(engine, checkfirst=True)
        
        # 创建默认凭证
        db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        try:
            # 检查是否已存在默认凭证
            default_credential = db.query(Credential).first()
            if not default_credential:
                # 创建默认凭证
                default_credential = Credential(
                    name="默认凭证",
                    description="默认设备凭证",
                    credential_type="ssh_password",
                    username="admin",
                    password="admin",
                    is_active=True
                )
                db.add(default_credential)
                db.commit()
                print("默认凭证创建成功")
            else:
                print("默认凭证已存在")
        except Exception as e:
            print(f"创建默认凭证失败: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        print(f"凭证表初始化失败: {str(e)}")
        raise

def init_ldap_templates(engine):
    """初始化LDAP模板表"""
    try:
        # 创建LDAP模板表
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ldap_templates (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    server_url VARCHAR(255) NOT NULL,
                    port INTEGER DEFAULT 389,
                    bind_dn VARCHAR(255) NOT NULL,
                    bind_password VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # 添加用户表的LDAP模板关联
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS ldap_template_id INTEGER 
                REFERENCES ldap_templates(id);
            """))
            
            conn.commit()
        
        print("LDAP模板表初始化成功")
    except Exception as e:
        print(f"LDAP模板表初始化失败: {str(e)}")
        raise

def init_ldap_config(engine):
    """初始化LDAP配置表"""
    try:
        print("开始初始化LDAP配置表...")
        # 创建LDAP配置表
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ldap_config (
                    id SERIAL PRIMARY KEY,
                    server_url VARCHAR(255) NOT NULL,
                    bind_dn VARCHAR(255) NOT NULL,
                    bind_password VARCHAR(255) NOT NULL,
                    search_base VARCHAR(255) NOT NULL,
                    use_ssl BOOLEAN DEFAULT false
                );
            """))
            
            # 检查use_ssl列是否存在，如果不存在则添加
            inspector = inspect(engine)
            if 'ldap_config' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('ldap_config')]
                if 'use_ssl' not in columns:
                    conn.execute(text("ALTER TABLE ldap_config ADD COLUMN use_ssl BOOLEAN DEFAULT false"))
                    conn.commit()
                    print("已添加use_ssl列到ldap_config表")
                else:
                    print("ldap_config表已存在且包含use_ssl列")
            
            conn.commit()
        
        print("LDAP配置表初始化成功")
    except Exception as e:
        print(f"LDAP配置表初始化失败: {str(e)}")
        raise

def init_process_management_tables(engine):
    """初始化流程管理模块的表"""
    try:
        print("正在创建流程管理模块的表...")
        
        # 创建流程定义表
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS process_definitions (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    version INTEGER NOT NULL DEFAULT 1,
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
                    nodes JSONB NOT NULL DEFAULT '[]',
                    edges JSONB NOT NULL DEFAULT '[]',
                    variables JSONB NOT NULL DEFAULT '{}',
                    created_by VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_by VARCHAR(255) NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP
                );
            """))
            
            # 创建流程版本表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS process_definition_versions (
                    id VARCHAR(36) PRIMARY KEY,
                    process_id VARCHAR(36) NOT NULL REFERENCES process_definitions(id),
                    version INTEGER NOT NULL,
                    nodes JSONB NOT NULL DEFAULT '[]',
                    edges JSONB NOT NULL DEFAULT '[]',
                    variables JSONB NOT NULL DEFAULT '{}',
                    created_by VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            conn.commit()
        
        print("流程管理模块的表创建完成")
    except Exception as e:
        print(f"流程管理模块的表初始化失败: {str(e)}")
        raise

def init_process_management_data(db):
    """初始化流程管理数据"""
    try:
        # 检查是否已有数据
        if db.execute(text("SELECT COUNT(*) FROM process_definitions")).scalar() == 0:
            # 添加示例流程
            now = datetime.utcnow().isoformat()
            db.execute(text("""
                INSERT INTO process_definitions (
                    id, name, description, version, status, nodes, edges, variables,
                    created_by, created_at, updated_by, updated_at
                ) VALUES (
                    :id, :name, :description, :version, :status, :nodes, :edges, :variables,
                    :created_by, :created_at, :updated_by, :updated_at
                )
            """), {
                'id': '00000000-0000-0000-0000-000000000001',
                'name': '示例流程',
                'description': '这是一个示例流程',
                'version': 1,
                'status': 'draft',
                'nodes': '[]',
                'edges': '[]',
                'variables': '{}',
                'created_by': 'admin',
                'created_at': now,
                'updated_by': 'admin',
                'updated_at': now
            })
            
            db.commit()
            print("流程管理数据初始化成功")
    except Exception as e:
        print(f"流程管理数据初始化失败: {str(e)}")
        db.rollback()
        raise

def init_job_tables(engine):
    """初始化作业执行控制相关表"""
    try:
        # 创建作业相关表
        Base.metadata.create_all(bind=engine, tables=[Job.__table__, JobExecution.__table__])
        print("作业执行控制相关表创建成功")
    except Exception as e:
        print(f"作业执行控制相关表创建失败: {str(e)}")
        raise

def init_databases():
    """初始化所有数据库"""
    try:
        # 获取数据库URL
        database_url = get_database_url()
        
        # 创建数据库引擎
        engine = create_engine(database_url)
        
        # 创建会话工厂
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 创建数据库会话
        db = SessionLocal()
        
        try:
            # 初始化系统数据
            init_system_data(db)
            
            # 初始化CMDB数据
            init_cmdb_data(db)
            
            # 初始化设备连接表
            init_device_connection_tables(engine)
            
            # 初始化凭证表
            init_credential_tables(engine)
            
            # 初始化LDAP模板
            init_ldap_templates(engine)
            
            # 初始化LDAP配置
            init_ldap_config(engine)
            
            # 初始化流程管理表
            init_process_management_tables(engine)
            
            # 初始化流程管理数据
            init_process_management_data(db)
            
            # 初始化作业执行控制表
            init_job_tables(engine)
            
            print("所有数据库初始化完成")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        raise

if __name__ == "__main__":
    init_databases() 