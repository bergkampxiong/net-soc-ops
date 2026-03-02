  # Docker 与数据库（PostgreSQL + Redis）安装方案

本文档供确认后使用，确认无误再与 `install.md` 合并。  
数据库账号密码与项目文档（如 `database/config.py` / 部署与配置排查报告）一致，便于本机或单机部署后直接对接后端。

---

## 一、约定与前提

| 项目 | 说明 |
|------|------|
| 操作系统 | 以 Linux（Debian/Ubuntu 或 CentOS/RHEL）为例 |
| 磁盘 | PostgreSQL 约 **100G**、Redis 约 **50G**，**合计约 150G**；脚本会校验 **/app 所在分区**可用空间 |
| 持久化目录 | **/app**：PostgreSQL → `/app/netops-postgres-data`，Redis → `/app/netops-redis-data`（绑定挂载） |
| Docker 桥接 | 脚本会配置 **192.168.0.0/16**，默认桥 bip **192.168.0.1/25**，自定义网络使用 **/25** 子网（需 root 写 `/etc/docker/daemon.json`） |
| PostgreSQL | 用户 `amber`，密码 `amberman@2025!`，数据库 `netops`，端口 `5432` |
| Redis | 端口 `6379`，DB 0，当前项目配置无密码（可选后续加 requirepass） |

---

## 二、Docker 安装与桥接（脚本可自动完成）

**一键脚本会**：若未检测到 Docker，则按系统类型自动安装（Debian/Ubuntu 使用 get.docker.com，CentOS/RHEL 使用 yum）；并写入 `/etc/docker/daemon.json`，配置桥接网段 **192.168.0.0/16**、默认桥 **192.168.0.1/25**、自定义网络 **/25** 子网，然后重启 Docker。**建议使用 `sudo bash scripts/setup-docker-databases.sh` 以完成安装与配置。**

以下为手动安装时参考（与脚本逻辑一致）。

### 2.1 Debian / Ubuntu

```bash
# 使用官方 convenience script（需 root）
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker "$USER"
# 重新登录或执行 newgrp docker 后生效
```

### 2.2 CentOS / RHEL / Fedora

```bash
# 安装 yum 系
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
# 重新登录或 newgrp docker 后生效
```

安装后验证：

```bash
docker --version
docker run --rm hello-world
```

---

## 三、PostgreSQL 安装与持久化（约 100G）

- 镜像：官方 `postgres:16`（可改为 15/14）
- 端口：`5432`
- 数据目录：**/app/netops-postgres-data**（绑定挂载；需确保 /app 所在分区有足够空间，见脚本第 0 步）
- 账号：与项目一致，便于后端直接使用

```bash
# 确保 /app 存在且空间充足（≥150G 用于 PG+Redis），脚本会自动校验
mkdir -p /app/netops-postgres-data

# 启动 PostgreSQL
docker run -d \
  --name netops-postgres \
  --restart unless-stopped \
  -e POSTGRES_USER=amber \
  -e POSTGRES_PASSWORD='amberman@2025!' \
  -e POSTGRES_DB=netops \
  -p 5432:5432 \
  -v /app/netops-postgres-data:/var/lib/postgresql/data \
  postgres:16

# 验证
docker exec netops-postgres psql -U amber -d netops -c 'SELECT 1;'
```

连接串（供后端或 .env 使用）：

- `postgresql://amber:amberman@2025!@<本机IP或localhost>:5432/netops`  
- 密码中含 `@`，在 URL 中需做 URL 编码（或使用环境变量 / 配置文件）。

---

## 四、Redis 安装与持久化（约 50G）

- 镜像：官方 `redis:7`
- 端口：`6379`
- 数据目录：**/app/netops-redis-data**（绑定挂载）
- 当前项目未配置 Redis 密码，以下先不启用 requirepass；若需密码，可加 `-e REDIS_PASSWORD=xxx` 并配合镜像文档启用

```bash
# 确保 /app 存在且空间充足
mkdir -p /app/netops-redis-data

# 启动 Redis（开启 AOF 持久化，更安全）
docker run -d \
  --name netops-redis \
  --restart unless-stopped \
  -p 6379:6379 \
  -v /app/netops-redis-data:/data \
  redis:7 redis-server --appendonly yes

# 验证
docker exec netops-redis redis-cli PING
# 应返回 PONG
```

连接串（供后端或 .env 使用）：

- `redis://<本机IP或localhost>:6379/0`

---

## 五、一键脚本（可选）

脚本路径：`scripts/setup-docker-databases.sh`。执行前请确认：

1. **建议使用 `sudo bash scripts/setup-docker-databases.sh`**：脚本会自动安装 Docker（若未安装）、配置桥接 192.168.0.0/16（/25）、启动数据库容器。
2. **/app 目录存在**，且 **/app 所在分区可用空间 ≥ 150 GiB**（脚本会自动校验，不足则退出）。
3. 端口 5432、6379 未被占用。

脚本会：先校验 /app 与空间 → 创建 `/app/netops-postgres-data`、`/app/netops-redis-data` → 启动容器并绑定挂载上述目录。

脚本步骤摘要（以仓库内 `scripts/setup-docker-databases.sh` 为准）：

- **0** 检查 `/app` 存在；若不存在则尝试创建；校验 `/app` 所在分区可用空间 ≥ 150 GiB（PG 100G + Redis 50G），不足则退出。
- **1** 检查 Docker 已安装。
- **2** 创建 `netops-postgres` 容器，数据绑定挂载到 `/app/netops-postgres-data`。
- **3** 创建 `netops-redis` 容器，数据绑定挂载到 `/app/netops-redis-data`。
- **4** 执行 PostgreSQL 与 Redis 连接验证并输出示例连接串。

---

## 六、与项目配置的对应关系

| 项目配置 | 本方案 |
|----------|--------|
| `database/config.py` 中 PostgreSQL | host 改为本机 IP 或 `127.0.0.1`，port 5432，user=amber，password=amberman@2025!，database=netops |
| `database/config.py` 中 Redis | host 改为本机 IP 或 `127.0.0.1`，port 6379，db 0 |
| `.env` 的 `DATABASE_URL` / `CMDB_DATABASE_URL` | `postgresql://amber:<URL编码密码>@<host>:5432/netops` |
| `.env` 的 `REDIS_URL` | `redis://<host>:6379/0` |

密码中的 `@` 在 URL 中应编码为 `%40`，例如：

- `postgresql://amber:amberman%402025!@127.0.0.1:5432/netops`

---

## 七、确认清单（请确认后再合并到 install.md）

- [ ] Docker 安装段落与目标系统（Debian/Ubuntu 或 CentOS/RHEL）一致，是否需要补充其他发行版？
- [ ] PostgreSQL/Redis 端口 5432、6379 是否与现网无冲突？
- [ ] 账号密码（amber / amberman@2025!）是否确认用于此环境？
- [ ] 持久化目录 `/app` 及 150 GiB 空间要求（PG 100G + Redis 50G）是否满足（脚本会校验 /app 所在分区）？
- [ ] 一键脚本路径 `scripts/setup-docker-databases.sh` 是否合适？

确认无误后，可将本方案合并进 `install.md`（或项目既有安装文档），并视需要补充：依赖安装、后端 .env 示例、首次初始化数据库表等步骤。
