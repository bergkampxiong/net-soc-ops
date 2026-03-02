# NetOps 网络运维与安全自动化平台

网络与安全运维一体化平台：资产管理（CMDB）、配置管理、设备连接、流程编排与作业调度、监控集成，以及自动化渗透测试与报告等能力。

---

## 功能概览

- **用户与安全**：用户与角色、双因素认证（2FA）、审计日志、LDAP 集成、安全策略（密码复杂度、锁定时长等）
- **CMDB**：资产、设备类型、厂商、位置、部门、网络设备/服务器/虚拟机/K8s 等资源管理
- **配置管理**：配置备份与版本、配置生成、配置合规与 EOS 信息
- **设备连接**：设备连接与连接池管理、SSH 等
- **流程与作业**：可视化流程设计器、流程管理、作业执行与监控
- **自动化 RPA**：原子功能组件（设备连接、配置管理、配置生成、数据采集、**渗透测试**）、流程编排、任务作业与**渗透测试报告**
- **监控集成**：Webhook 接入、告警事件落库
- **系统管理**：全局配置、前端证书配置（开发/生产 HTTPS）

渗透测试相关功能提供自动化渗透测试任务与报告查看，不依赖特定第三方产品名称。

---

## 技术栈

| 端     | 技术 |
|--------|------|
| 后端   | Python 3.10+、FastAPI、PostgreSQL、Redis、SQLAlchemy |
| 前端   | React、TypeScript、Ant Design |
| 数据库 | PostgreSQL（业务 + CMDB）、Redis（会话/缓存/连接池等） |

---

## 项目结构

```
net-soc-ops/
├── netops-backend/     # 后端（FastAPI）
├── netops-frontend/    # 前端（React）
├── docs/               # 安装、部署、配置等文档
└── scripts/            # 安装与运维脚本
    ├── install-netops.sh           # 前后端一键安装（Python3/npm、.env 配置、依赖与库表）
    ├── start-netops.sh             # 启动前后端服务（后端后台 + 前端前台；Ctrl+C 一并退出）
    ├── setup-docker-databases.sh   # 本机 Docker 方式安装 PostgreSQL + Redis（可选）
    ├── gen-dev-https-cert.sh      # 开发环境 HTTPS 自签名证书
    └── nginx-https-example.conf   # 生产 Nginx HTTPS 示例
```

---

## 快速开始

### 环境要求

- **Python** 3.10+（后端）
- **Node.js** 16+（前端）
- **PostgreSQL**、**Redis**（需在其它机器或环境单独安装，本仓库不包含数据库安装）

### 一键安装（推荐）

在项目根目录执行，按提示输入数据库与 Redis 连接参数（主机、端口、用户、密码等），脚本会写入 `netops-backend/.env` 并完成依赖安装与库表初始化：

```bash
bash scripts/install-netops.sh
```

数据库在其它机器安装；仅当需要在本机自建库时，可选用：

```bash
sudo bash scripts/setup-docker-databases.sh
```

**启动服务**（安装完成后）：

```bash
bash scripts/start-netops.sh
```

后端在后台运行（端口 8000），前端占当前终端（开发 HTTPS 已开）；按 Ctrl+C 会同时停止前后端。

### 手动安装与启动

详见 [docs/install.md](docs/install.md)，包含：

- 后端：虚拟环境、`pip install -r requirements.txt`、`.env` 配置、`python3 int_all_db.py`、`python3 main.py`
- 前端：`npm install`、`npm run start` / `npm run build`
- 开发 HTTPS、生产 Nginx 示例

---

## 文档与脚本

| 文档/脚本 | 说明 |
|-----------|------|
| [docs/install.md](docs/install.md) | 安装与启动说明 |
| [docs/部署与配置排查报告.md](docs/部署与配置排查报告.md) | 部署约定、环境变量、HTTPS、数据库/Redis 配置 |
| [docs/docker-数据库安装方案.md](docs/docker-数据库安装方案.md) | Docker 方式安装 PostgreSQL + Redis 的约定与步骤 |
| [netops-backend/README.md](netops-backend/README.md) | 后端结构及历史说明 |

---

## 注意事项

1. 数据库与 Redis 需单独部署。在后端目录 `netops-backend` 下新建或编辑 `.env` 文件，在其中填写 PostgreSQL、Redis 的地址、端口、用户、密码等；运行一键安装脚本时也会提示输入并自动生成该文件。
2. 首次部署需执行 `python3 int_all_db.py` 初始化库表（一键安装脚本会自动执行）。
3. 生产环境建议使用 Nginx 等反向代理提供 HTTPS 与 `/api` 转发，参见 `scripts/nginx-https-example.conf`。
