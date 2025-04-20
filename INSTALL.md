# NetOps 网络自动化平台安装说明

## 环境要求
- Python 3.9+
- Node.js v22.14.0+
- PostgreSQL 13+
- Redis 6+
- LDAP服务器（可选）

## 快速安装步骤

### 1. 后端安装

1. 克隆代码并进入后端目录：
```bash
git clone <repository_url>
cd netops-backend
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置数据库连接：
   - 打开 `database/config.py` 文件
   - 修改数据库和Redis连接信息：
     ```python
     DATABASE_CONFIG = {
         "host": "172.18.40.80",  # 数据库服务器地址
         "port": 5432,            # 数据库端口
         "database": "netops",    # 数据库名称
         "user": "amber",         # 数据库用户名
         "password": "amberman@2025!",  # 数据库密码
     }

     REDIS_CONFIG = {
         "host": "172.18.40.80",  # Redis服务器地址
         "port": 6379,            # Redis端口
         "db": 0,                 # Redis数据库编号
     }
     ```
   - 注意：CMDB数据库使用与netops相同的数据库，无需单独配置

5. 配置LDAP（可选）：
   - 打开 `auth/ldap_config.py` 文件
   - 修改LDAP配置信息：
     ```python
     LDAP_CONFIG = {
         "server_url": "ldap://your-ldap-server",  # LDAP服务器地址
         "bind_dn": "cn=admin,dc=example,dc=com",  # 管理员DN
         "bind_password": "admin_password",        # 管理员密码
         "search_base": "dc=example,dc=com",       # 搜索基础DN
         "use_ssl": False,                         # 是否使用SSL
         "admin_group_dn": "cn=admins,dc=example,dc=com",  # 管理员组DN
         "auditor_group_dn": "cn=auditors,dc=example,dc=com"  # 审计员组DN
     }
     ```

6. 初始化数据库：
```bash
# 运行初始化脚本
python int_all_db.py
```

7. 启动后端服务：
```bash
# 启动API服务
python main.py

# 启动Celery Worker（后台任务）
celery -A tasks worker --loglevel=info

# 启动Celery Beat（定时任务）
celery -A tasks beat --loglevel=info
```

### 2. 前端安装

1. 进入前端目录：
```bash
cd netops-frontend
```

2. 安装依赖：
```bash
npm install
```

3. 配置环境变量：
   - 复制 `.env.example` 为 `.env`
   - 修改API地址和其他配置

4. 启动开发服务器：
```bash
npm start
```

## 访问系统
- 前端界面：http://localhost:3000
- 后端API文档：http://localhost:8000/docs

默认登录信息：
- 用户名：admin
- 密码：admin123

## 用户管理

### LDAP用户
1. 在系统设置中配置LDAP服务器信息
2. 创建LDAP用户时，系统会自动同步用户信息
3. 用户角色和权限可以在系统中单独设置

### 本地用户
1. 使用管理员账号登录系统
2. 进入用户管理页面
3. 点击"创建用户"按钮
4. 填写用户信息并设置角色和权限

## 权限管理
系统支持以下权限级别：
- 超级管理员（superuser）：拥有所有权限
- 管理员（admin）：可以管理用户和系统设置
- 操作员（operator）：可以执行日常运维任务
- 审计员（auditor）：可以查看审计日志

每个角色还可以设置细粒度的权限：
- 设备管理权限
- 配置管理权限
- 凭据管理权限
- 审计日志权限

## 数据库管理

### 数据库初始化
系统使用统一的数据库初始化脚本，该脚本会：
1. 创建所有必要的数据库表
2. 初始化基础数据（设备类型、厂商、位置等）
3. 创建管理员账户
4. 初始化LDAP配置表

如需重新初始化数据库，请运行：
```bash
python int_all_db.py
```

## 常见问题

1. 数据库连接失败
   - 检查数据库服务器是否可访问
   - 验证数据库用户名和密码是否正确
   - 确认数据库名称是否存在

2. LDAP连接失败
   - 检查LDAP服务器地址是否正确
   - 验证管理员DN和密码是否正确
   - 确认搜索基础DN是否正确
   - 检查防火墙是否允许LDAP连接

3. 初始化失败
   - 检查数据库用户是否有创建表的权限
   - 查看错误日志获取详细信息

4. 服务启动失败
   - 检查端口是否被占用
   - 确认所有依赖是否正确安装
   - 查看服务日志获取错误信息

## 技术支持
如有问题，请联系系统管理员或提交Issue。 