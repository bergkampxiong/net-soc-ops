# NetOps 网络自动化平台

## 项目结构
```
netops/
├── netops-backend/    # 后端服务
└── netops-frontend/   # 前端应用
```

## 后端服务安装说明

### 1. 环境要求
- Python 3.8+
- SQLite3
- pip

### 2. 安装步骤

1. 克隆代码库：
```bash
git clone <repository_url>
cd netops-backend
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 数据库初始化（两种方式）：

#### 方式一：使用数据库备份（推荐）
1. 将 `database_backups` 目录下的最新备份文件复制到服务器
2. 执行恢复脚本：
```bash
python restore_database.py database_backups/netops_backup_*.sql
```

#### 方式二：使用 Alembic 迁移
1. 执行数据库迁移：
```bash
alembic upgrade head
```

### 3. 启动服务
```bash
python main.py
```

## 前端应用安装说明

### 1. 环境要求
- Node.js 16+
- npm 8+ 或 yarn 1.22+

### 2. 安装步骤

1. 进入前端目录：
```bash
cd netops-frontend
```

2. 安装依赖：
```bash
# 使用 npm
npm install

# 或使用 yarn
yarn install
```

3. 开发环境运行：
```bash
# 使用 npm
npm run dev

# 或使用 yarn
yarn dev
```

4. 生产环境构建：
```bash
# 使用 npm
npm run build

# 或使用 yarn
yarn build
```

5. 生产环境预览：
```bash
# 使用 npm
npm run preview

# 或使用 yarn
yarn preview
```

### 3. 部署说明
1. 执行构建命令生成 dist 目录
2. 将 dist 目录下的文件部署到 Web 服务器（如 Nginx）
3. 配置 Web 服务器反向代理到后端服务

## 数据库管理

### 备份数据库
```bash
python backup_database.py
```
备份文件将保存在 `database_backups` 目录下，文件名格式为 `netops_backup_YYYYMMDD_HHMMSS.sql`

### 恢复数据库
```bash
python restore_database.py <备份文件路径>
```

## 注意事项
1. 首次安装建议使用数据库备份方式，可以快速完成部署
2. 定期执行数据库备份，以防数据丢失
3. 恢复数据库前请确保已停止服务
4. 建议在恢复数据库前先备份现有数据
5. 前端开发时注意配置正确的后端服务地址
6. 生产环境部署时注意配置正确的环境变量

## 常见问题
1. 如果遇到数据库权限问题，请确保当前用户对数据库目录有写入权限
2. 如果恢复失败，请检查备份文件是否完整
3. 如果遇到编码问题，请确保系统支持 UTF-8 编码
4. 如果前端构建失败，请检查 Node.js 版本是否符合要求
5. 如果前端访问后端 API 失败，请检查跨域配置是否正确

## 技术支持
如有问题，请联系系统管理员或提交 Issue。 