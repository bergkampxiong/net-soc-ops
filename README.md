# NetOps 网络自动化平台

## 项目简介

NetOps 是一个现代化的网络自动化平台，提供网络设备管理、配置管理、自动化运维等功能，支持 LDAP 认证和细粒度权限管理。

## 功能特点

### 1. CMDB 资产管理
- 数据查询：灵活的资产查询和过滤
- ADS 自动发现：自动发现和更新网络设备
- 资产盘点：定期盘点和差异分析
- 模型管理：自定义资产模型和属性

### 2. 设备管理
- 设备分类：多维度设备分组管理
- 凭证管理：设备访问凭证管理

### 3. 自动化 RPA
- **原子组件**：设备连接、配置备份/恢复、配置生成、数据采集、安全审计、告警与报告
- **流程编排**：可视化流程设计器、流程版本与发布管理
- **任务作业**：作业执行与调度、任务队列、监控与报告
- **系统集成**：监控系统、工单系统对接

### 4. AIOPS 智能运维
- 智能告警、根因分析、预测性维护

## 技术架构

| 层级 | 技术 |
|------|------|
| 前端 | React 18、TypeScript、Ant Design 5.x、React Router 6、Axios、ECharts |
| 后端 | Python 3.9+、FastAPI、SQLAlchemy、PostgreSQL / SQLite、Redis（可选）、APScheduler |
| 部署 | Docker、Nginx 反向代理、Gunicorn、Supervisor（可选） |

## 项目结构

```
<项目根目录>/
├── netops-backend/    # 后端服务（入口：main.py）
└── netops-frontend/   # 前端应用
```

克隆后若仓库目录名为 `net-soc-ops`，则上述「项目根目录」即 `net-soc-ops`。

## 快速开始

### 方式一：本地 / 开发（最小依赖，推荐先跑通）

**环境**：Python 3.8+、Node.js 16+，无需 PostgreSQL/Redis。

1. **克隆并安装依赖**
   ```bash
   git clone <仓库地址>
   cd <项目根目录>/netops-backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # 首次可创建管理员
   python3 create_admin.py
   ```
   然后**另开终端**安装前端依赖：
   ```bash
   cd <项目根目录>/netops-frontend
   npm install
   ```

2. **启动服务（两种方式任选）**

   **方式 A：分两个终端**
   - 终端一（后端）：
     ```bash
     cd <项目根目录>/netops-backend
     source venv/bin/activate
     python3 main.py
     ```
   - 终端二（前端）：
     ```bash
     cd <项目根目录>/netops-frontend
     npm run start-all
     ```

   **方式 B：一条命令（推荐）**
   ```bash
   cd <项目根目录>
   ./scripts/start-dev.sh
   ```
   会先起后端，再起前端（`start-all` = 代理 + 前端）。按 Ctrl+C 会同时停止两者。

3. **访问**  
   浏览器打开前端地址（默认如 http://localhost:3000 或代理端口），使用 `create_admin.py` 创建的管理员账号登录（默认如 admin / admin123）。

### 方式二：生产部署（PostgreSQL + Redis + Nginx）

需安装 PostgreSQL、Redis、Nginx 等，完整步骤见 **[INSTALL.md](INSTALL.md)**。

## 详细安装与部署

- **完整安装、环境变量、Nginx、Supervisor、常见问题**：请参考 [INSTALL.md](INSTALL.md)。

## 开发指南

### 代码规范
- 前端：遵循项目 ESLint 配置
- 后端：遵循 PEP 8
- 注释使用中文，变量命名使用英文驼峰

### 提交规范
- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档
- `style:` 格式
- `refactor:` 重构
- `test:` 测试
- `chore:` 构建/工具

### 分支
- `master`：稳定
- `develop`：开发
- `feature/*`：功能
- `hotfix/*`：紧急修复

## 许可证

MIT，详见 [LICENSE](LICENSE) 文件。
