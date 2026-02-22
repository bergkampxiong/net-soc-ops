# NetOps 安装与部署指南

本文档说明 NetOps 的详细安装与生产部署步骤。若仅需在本地快速运行，请以根目录 [README.md](README.md) 中的「快速开始」为准。

---

## 一、环境要求

### 系统要求
- 操作系统：Linux（推荐 Ubuntu 20.04 LTS 或 CentOS 8）
- CPU：4 核及以上
- 内存：8GB 及以上
- 磁盘：50GB 及以上

### 软件要求（按部署方式）

| 场景         | Python | Node.js | 数据库           | Redis | Nginx | 说明 |
|--------------|--------|---------|------------------|-------|-------|------|
| 本地/开发    | 3.8+   | 16+     | SQLite3（默认）  | 可选  | 可选  | 最小依赖 |
| 生产部署     | 3.9+   | 16+     | PostgreSQL 13+   | 6+    | 1.18+ | 推荐 |

- Docker、LDAP、Celery：可选，按需使用。

---

## 二、本地 / 开发环境（最小化）

适用于本机开发或演示，无需 PostgreSQL/Redis。

### 2.1 后端

```bash
cd <项目根目录>/netops-backend
pip install -r requirements.txt
```

**数据库**：不设置环境变量时，默认使用当前目录下的 SQLite 数据库文件。表结构在**首次执行 `python main.py` 时自动创建**，无需单独执行 `init_db`。

**创建管理员**（首次使用建议执行）：
```bash
python create_admin.py
```
按脚本提示使用默认账号（如 admin / admin123）登录。

**启动**：
```bash
python main.py
```
服务默认 http://localhost:8000。

### 2.2 前端

```bash
cd <项目根目录>/netops-frontend
npm install
npm run start
```
默认 http://localhost:3000。

**对接后端**：前端请求带 `/api` 前缀，需指向后端地址。可任选其一：

- 在 `netops-frontend/package.json` 中配置 `"proxy": "http://localhost:8000"`（Create React App 会将 `/api` 代理到该地址），然后 `npm run start`；或
- 使用项目内代理：先启动后端，再在 frontend 目录执行 `npm run start-all`（会同时起代理与前端，具体以项目脚本为准）。

### 2.3 使用 SQLite 时的备份/恢复（可选）

- 备份：`cd netops-backend && python backup_database.py`，备份文件在 `database_backups/`。
- 恢复：`python restore_database.py database_backups/netops_backup_YYYYMMDD_HHMMSS.sql`（恢复前请先停止后端）。

---

## 三、生产环境部署

### 3.1 系统依赖（以 Ubuntu 为例）

```bash
sudo apt update
sudo apt install -y build-essential python3-dev python3-pip python3-venv \
    postgresql postgresql-contrib redis-server nginx git curl wget
```

### 3.2 PostgreSQL

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -u postgres psql
```

在 psql 中执行：
```sql
CREATE DATABASE netops;
CREATE USER netops WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE netops TO netops;
\q
```

### 3.3 Redis

```bash
sudo systemctl start redis
sudo systemctl enable redis
```
若需密码，在 `/etc/redis/redis.conf` 中设置 `requirepass your_redis_password`。

### 3.4 后端安装与配置

```bash
git clone <仓库地址>
cd <项目根目录>/netops-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**环境变量**：在项目根或后端目录新建 `.env`（若仓库提供 `.env.example` 可复制后修改），配置例如：

```bash
DATABASE_URL=postgresql://netops:your_password@localhost:5432/netops
REDIS_URL=redis://:your_redis_password@localhost:6379/0
SECRET_KEY=<强随机密钥，生产必改>
# LDAP 等按需配置
```

**数据库表**：生产使用 PostgreSQL 时，可执行迁移（若项目使用 Alembic）：
```bash
alembic upgrade head
```
或直接启动后端（若代码在启动时自动建表）：
```bash
python main.py
```
确认表已存在后，创建管理员：
```bash
python create_admin.py
```

**说明**：项目根目录**没有** `run.py`，后端入口为 **`main.py`**。不要执行不存在的 `init_db.py`，表由应用启动或迁移创建。

### 3.5 前端安装与构建

```bash
cd <项目根目录>/netops-frontend
npm install
npm run build
```
构建产物在 `build/`（或项目配置的 output 目录）。

前端环境变量（如需要）：新建 `.env` 或 `.env.production`，例如：
```bash
REACT_APP_API_URL=https://your-domain.com
# 其他 REACT_APP_* 按项目说明
```

### 3.6 Nginx 示例

```bash
sudo nano /etc/nginx/sites-available/netops
```

示例配置（请替换 `your_domain.com`、`/path/to/` 等）：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        root /path/to/netops-frontend/build;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

启用并检查：
```bash
sudo ln -s /etc/nginx/sites-available/netops /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.7 使用 Supervisor 管理后端进程（可选）

```bash
sudo apt install supervisor
sudo nano /etc/supervisor/conf.d/netops.conf
```

示例（请将 `/path/to/`、`netops` 替换为实际路径和用户）：

```ini
[program:netops-backend]
command=/path/to/netops-backend/venv/bin/python main.py
directory=/path/to/netops-backend
user=netops
autostart=true
autorestart=true
stderr_logfile=/var/log/netops/backend.err.log
stdout_logfile=/var/log/netops/backend.out.log
environment=DATABASE_URL="postgresql://..."
```

若使用 uvicorn 多进程，可将 `command` 改为例如：
`/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2`

```bash
sudo mkdir -p /var/log/netops
sudo chown netops:netops /var/log/netops
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start netops-backend
```

**注意**：后端入口为 **`main.py`**，不要写 `run.py`。Celery 若使用，需单独配置 worker 程序段（参考项目 `tasks.py`）。

---

## 四、访问与默认账号

- 前端：http://your_domain.com 或 http://localhost:3000（开发）
- 后端 API 文档：http://your_domain.com/api/docs 或 http://localhost:8000/docs

**默认管理员**（仅在使用 `create_admin.py` 且未改脚本时）：
- 用户名：`admin`
- 密码：`admin123`  

**生产环境务必**在首次登录后修改密码，或修改 `create_admin.py` 后重新创建管理员。

---

## 五、常见问题

### 5.1 数据库连接失败
- 检查 PostgreSQL/Redis 服务是否运行。
- 核对 `.env` 中 `DATABASE_URL`、`REDIS_URL` 的地址、端口、用户名、密码。
- 若使用 SQLite，确认运行用户对当前目录有写权限。

### 5.2 后端启动报错 “no such table”
- 使用 SQLite 时：直接执行一次 `python main.py`，表会自动创建。
- 使用 PostgreSQL 时：执行 `alembic upgrade head` 或确认代码中是否有启动时建表逻辑。

### 5.3 前端访问后端 404 / 跨域
- 开发：确认 `package.json` 的 `proxy` 或代理脚本指向正确后端地址（如 http://localhost:8000）。
- 生产：确认 Nginx 的 `location /api` 代理到后端且后端监听正确端口。

### 5.4 没有 .env.example
- 若仓库未提供 `.env.example`，请根据本文档和代码中的配置项**新建 `.env`**，并填写 `DATABASE_URL`、`SECRET_KEY` 等（生产必须使用强随机 `SECRET_KEY`）。

---

## 六、安全建议

1. 生产环境必须修改默认管理员密码，并使用强随机 `SECRET_KEY`。
2. 使用 HTTPS（配置 SSL 证书）。
3. 限制 Nginx 与系统防火墙，仅开放必要端口。
4. 定期备份数据库（SQLite 用 `backup_database.py`，PostgreSQL 用 pg_dump 等）。
5. 定期更新系统与依赖安全补丁。

---

## 七、维护与更新

- **日常**：查看应用与 Nginx 日志，监控磁盘与数据库大小。
- **更新**：拉取代码后，更新依赖（pip/npm），执行数据库迁移（如有），再重启后端与前端（或 Nginx 重载）。

如有问题，建议在项目仓库提交 Issue 或联系维护人员。
