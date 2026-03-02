# NetOps 安装与启动说明

本文档说明从零安装依赖、数据库、后端服务与前端，以及如何启动服务。更细的配置与部署约定见 [部署与配置排查报告](./部署与配置排查报告.md)。

---

## 一、环境准备与一键安装（可选）

- **Python**：3.10+（后端）
- **Node.js**：16+（前端，建议 LTS）
- **数据库**：PostgreSQL、Redis（可使用项目提供的 Docker 脚本一键安装，见第二节）
- **可选**：Docker（用于脚本安装 PostgreSQL + Redis）

**一键安装脚本**（安装 Python3/npm、交互配置数据库与 Redis 并写入 `.env`、安装前后端依赖、初始化库表）：

```bash
bash scripts/install-netops.sh
```

- 建议将项目放在 `/app/net-soc-ops` 下；也可在任意克隆路径执行，脚本以当前仓库为项目根。
- 执行过程中会提示输入 PostgreSQL（主机/端口/用户/密码/库名）与 Redis（主机/端口/DB），并生成 `netops-backend/.env`。若数据库尚未安装，可先执行 `sudo bash scripts/setup-docker-databases.sh`。

---

## 二、数据库（PostgreSQL + Redis）

**方式 A：一键脚本（推荐）**

- 执行：`sudo bash scripts/setup-docker-databases.sh`
- 脚本会安装 Docker（若未安装）、配置桥接、创建并启动 PostgreSQL 与 Redis 容器，数据持久化到 `/app`，并校验空间（约 150 GiB）。
- 详细约定与手动步骤见 [部署与配置排查报告 - 五、Docker 与数据库安装方案及脚本](./部署与配置排查报告.md#五docker-与数据库安装方案及脚本)。

**方式 B：使用已有数据库**

- 在 `netops-backend/.env` 中配置 `DATABASE_URL`、`CMDB_DATABASE_URL`、`REDIS_URL`（或通过 `database/config.py` 所用环境变量），与现有库连接信息一致即可。

---

## 三、后端服务启动

1. **进入后端目录并创建虚拟环境（建议）**

   ```bash
   cd netops-backend
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   # 或 Windows: venv\Scripts\activate
   ```

2. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**

   - 复制或编辑 `netops-backend/.env`，至少配置：
     - `DATABASE_URL`、`CMDB_DATABASE_URL`（PostgreSQL 连接串）
     - `REDIS_URL`（Redis 连接串）
     - `SECRET_KEY`（JWT 等使用）
   - 若使用 Docker 脚本安装的数据库，连接示例见脚本输出或 [部署与配置排查报告 - 5.5 与项目配置的对应关系](./部署与配置排查报告.md#55-与项目配置的对应关系)。

4. **初始化数据库表（首次部署）**

   ```bash
   python int_all_db.py
   ```

5. **启动后端**

   ```bash
   python main.py
   ```

   - 默认监听 `http://0.0.0.0:8000`（开发模式带 reload）。
   - 生产环境建议使用：`uvicorn main:app --host 0.0.0.0 --port 8000`（可去掉 reload）。

---

## 四、前端

1. **安装依赖**

   ```bash
   cd netops-frontend
   npm install
   ```

2. **开发环境启动**

   ```bash
   npm run start
   ```

   - 默认访问：`http://localhost:8080`，API 通过相对路径 `/api` 请求后端；若需连其他后端，可配置 `proxy` 或使用 `proxy-server.js`（见 [部署与配置排查报告](./部署与配置排查报告.md)）。

3. **生产构建**

   ```bash
   npm run build
   ```

   - 产物在 `netops-frontend/build`，由 Nginx 等静态服务托管，并将 `/api` 反向代理到后端（示例见 `scripts/nginx-https-example.conf`）。

---

## 五、开发环境 HTTPS（可选）

- 设置环境变量并启动：`REACT_APP_DEV_HTTPS=true npm run start`，访问 **https://localhost:8080**。
- **长期有效自签名证书**（避免浏览器频繁提示）：
  1. 生成证书（默认 10 年）：`bash scripts/gen-dev-https-cert.sh`
  2. 证书输出到 `netops-frontend/.cert/`（已加入 .gitignore），devServer 会自动使用。
  3. 自定义有效期（天）：`CERT_DAYS=3650 bash scripts/gen-dev-https-cert.sh`

生产环境 HTTPS 在反向代理层配置，见 [部署与配置排查报告 - 2.5 前端 HTTPS](./部署与配置排查报告.md#25-前端-https开发可选--生产反向代理) 与 `scripts/nginx-https-example.conf`。

---

## 六、启动顺序小结

1. 数据库就绪（Docker 脚本或已有库 + `.env` 配置）
2. 后端：`cd netops-backend && source venv/bin/activate && pip install -r requirements.txt && python main.py`
3. 前端：`cd netops-frontend && npm install && npm run start`（或先 `npm run build` 再用 Nginx 托管）

前端请求 `/api` 会发往后端（开发时通过 proxy 或 start-all；生产时通过 Nginx 反向代理）。
