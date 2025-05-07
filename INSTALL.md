# NetOps安装指南

本文档提供了NetOps网络自动化平台的详细安装和配置说明。

## 环境要求

### 系统要求
- 操作系统：Linux (推荐 Ubuntu 20.04 LTS 或 CentOS 8)
- CPU：4核或以上
- 内存：8GB或以上
- 磁盘空间：50GB或以上

### 软件要求
- Python 3.9+
- Node.js v22.14.0+
- PostgreSQL 13+
- Redis 6+
- Nginx 1.18+
- Docker 20.10+ (可选)
- LDAP服务器 (可选)

## 安装步骤

### 1. 系统准备

#### 1.1 安装系统依赖
```bash
# Ubuntu
sudo apt update
sudo apt install -y build-essential python3-dev python3-pip python3-venv \
    postgresql postgresql-contrib redis-server nginx \
    git curl wget

# CentOS
sudo yum update
sudo yum install -y gcc python3-devel python3-pip python3-virtualenv \
    postgresql-server postgresql-contrib redis nginx \
    git curl wget
```

#### 1.2 配置Python环境
```bash
# 创建Python虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip
```

### 2. 数据库配置

#### 2.1 PostgreSQL配置
```bash
# 启动PostgreSQL服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql
postgres=# CREATE DATABASE netops;
postgres=# CREATE USER netops WITH PASSWORD 'your_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE netops TO netops;
postgres=# \q
```

#### 2.2 Redis配置
```bash
# 启动Redis服务
sudo systemctl start redis
sudo systemctl enable redis

# 配置Redis密码
sudo nano /etc/redis/redis.conf
# 添加或修改以下行：
# requirepass your_redis_password
```

### 3. 后端安装

#### 3.1 克隆代码
```bash
git clone https://github.com/your-username/netops.git
cd netops/netops-backend
```

#### 3.2 安装依赖
```bash
# 激活虚拟环境
source ../venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 3.3 配置环境变量
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
nano .env

# 主要配置项：
DATABASE_URL=postgresql://netops:your_password@localhost:5432/netops
REDIS_URL=redis://:your_redis_password@localhost:6379/0
SECRET_KEY=your_secret_key
LDAP_SERVER=ldap://your_ldap_server
LDAP_BASE_DN=dc=example,dc=com
```

#### 3.4 初始化数据库
```bash
# 创建数据库表
python init_db.py

# 创建初始管理员用户
python create_admin.py
```

### 4. 前端安装

#### 4.1 安装Node.js
```bash
# 使用nvm安装Node.js
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 22.14.0
nvm use 22.14.0
```

#### 4.2 安装前端依赖
```bash
cd ../netops-frontend
npm install
```

#### 4.3 配置环境变量
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
nano .env

# 主要配置项：
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

### 5. Nginx配置

#### 5.1 配置Nginx
```bash
sudo nano /etc/nginx/sites-available/netops

# 添加以下配置
server {
    listen 80;
    server_name your_domain.com;

    # 前端静态文件
    location / {
        root /path/to/netops-frontend/build;
        try_files $uri $uri/ /index.html;
    }

    # 后端API代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket代理
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

#### 5.2 启用配置
```bash
sudo ln -s /etc/nginx/sites-available/netops /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. 启动服务

#### 6.1 使用Supervisor管理进程
```bash
# 安装Supervisor
sudo apt install supervisor

# 配置Supervisor
sudo nano /etc/supervisor/conf.d/netops.conf

# 添加以下配置
[program:netops-backend]
command=/path/to/venv/bin/python run.py
directory=/path/to/netops-backend
user=netops
autostart=true
autorestart=true
stderr_logfile=/var/log/netops/backend.err.log
stdout_logfile=/var/log/netops/backend.out.log

[program:netops-celery]
command=/path/to/venv/bin/celery -A tasks worker --loglevel=info
directory=/path/to/netops-backend
user=netops
autostart=true
autorestart=true
stderr_logfile=/var/log/netops/celery.err.log
stdout_logfile=/var/log/netops/celery.out.log
```

#### 6.2 启动服务
```bash
# 创建日志目录
sudo mkdir -p /var/log/netops
sudo chown -R netops:netops /var/log/netops

# 重新加载Supervisor配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动服务
sudo supervisorctl start netops-backend
sudo supervisorctl start netops-celery
```

### 7. 构建前端
```bash
cd ../netops-frontend
npm run build
```

## 访问系统

- 前端界面：http://your_domain.com
- 后端API文档：http://your_domain.com/api/docs
- 默认管理员账号：
- 用户名：admin
- 密码：admin123

## 常见问题

### 1. 数据库连接问题
- 检查PostgreSQL服务是否运行
- 验证数据库连接信息是否正确
- 确认数据库用户权限

### 2. Redis连接问题
- 检查Redis服务是否运行
- 验证Redis密码是否正确
- 确认Redis端口是否开放

### 3. 前端构建问题
- 清除node_modules并重新安装
- 检查Node.js版本是否兼容
- 查看构建日志获取详细错误信息

### 4. 后端服务问题
- 检查日志文件
- 验证环境变量配置
- 确认依赖包版本兼容性

## 安全建议

1. 修改默认密码
2. 配置SSL证书
3. 启用防火墙
4. 定期备份数据
5. 更新安全补丁

## 维护指南

### 日常维护
1. 检查日志文件
2. 监控系统资源
3. 备份数据库
4. 清理临时文件

### 更新部署
1. 备份当前版本
2. 拉取最新代码
3. 更新依赖包
4. 执行数据库迁移
5. 重启服务

## 联系支持

如有问题，请通过以下方式获取支持：
- 提交Issue：https://github.com/your-username/netops/issues
- 邮件支持：support@example.com
- 文档中心：https://docs.example.com 