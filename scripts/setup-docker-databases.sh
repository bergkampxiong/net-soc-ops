#!/usr/bin/env bash
# 用途：安装 Docker（如未安装）、配置桥接网段，并启动 PostgreSQL + Redis，持久化到 /app
# 使用：bash scripts/setup-docker-databases.sh [--run-user=netops]  或  RUN_AS_USER=netops bash ...
#       指定运行用户后将将其加入 docker 组，与 install-netops.sh / install-strix.sh 一致
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 运行用户：环境变量 RUN_AS_USER > 命令行 --run-user= > 项目 .run-user > 默认
RUN_AS_USER="${RUN_AS_USER:-}"
for arg in "$@"; do
  case "$arg" in
    --run-user=*) RUN_AS_USER="${arg#*=}" ; break ;;
  esac
done
[[ -z "$RUN_AS_USER" ]] && [[ -f "$PROJECT_ROOT/.run-user" ]] && RUN_AS_USER=$(cat "$PROJECT_ROOT/.run-user" | head -1)
[[ -z "$RUN_AS_USER" ]] && RUN_AS_USER=$([[ "$(id -u 2>/dev/null)" -eq 0 ]] && echo "netops" || echo "$USER")

# 持久化根目录与所需空间（GiB）：PostgreSQL 约 100G + Redis 约 50G
DATA_ROOT=/app
REQUIRED_GIB=150
# Docker 桥接：192.168.0.0/16，默认桥与自定义网络使用 /25 子网
DOCKER_BRIDGE_BIP=192.168.0.1/25
DOCKER_DEFAULT_POOL_BASE=192.168.0.0/16
DOCKER_DEFAULT_POOL_SIZE=25
PG_USER=amber
PG_PASSWORD='amberman@2025!'
PG_DB=netops
PG_PORT=5432
REDIS_PORT=6379
PG_DATA_DIR=${DATA_ROOT}/netops-postgres-data
REDIS_DATA_DIR=${DATA_ROOT}/netops-redis-data
PG_CONTAINER=netops-postgres
REDIS_CONTAINER=netops-redis
# 若脚本内安装了 Docker，后续命令用 sudo docker（因当前 shell 尚未加入 docker 组）
DOCKER_CMD=docker

echo "========== 0. 检查持久化目录与空间 =========="
if [[ ! -d "$DATA_ROOT" ]]; then
  echo "目录 $DATA_ROOT 不存在，尝试创建（可能需要 sudo）"
  if ! mkdir -p "$DATA_ROOT" 2>/dev/null; then
    echo "请使用 sudo 创建目录: sudo mkdir -p $DATA_ROOT && sudo chown \$(whoami) $DATA_ROOT"
    exit 1
  fi
fi
# 校验挂载点可用空间（取 $DATA_ROOT 所在文件系统）
AVAIL_BYTES=$(df -P -B1 "$DATA_ROOT" 2>/dev/null | awk 'NR==2 {print $4}')
REQUIRED_BYTES=$((REQUIRED_GIB * 1024 * 1024 * 1024))
if [[ -z "$AVAIL_BYTES" || "$AVAIL_BYTES" -lt "$REQUIRED_BYTES" ]]; then
  AVAIL_GIB=$((AVAIL_BYTES / 1024 / 1024 / 1024))
  echo "错误: $DATA_ROOT 所在分区可用空间不足。需要至少 ${REQUIRED_GIB} GiB，当前约 ${AVAIL_GIB:-0} GiB。"
  echo "请扩容或修改 DATA_ROOT / REQUIRED_GIB 后重试。"
  exit 1
fi
echo "目录 $DATA_ROOT 存在，可用空间充足（需 ${REQUIRED_GIB} GiB，当前约 $((AVAIL_BYTES / 1024 / 1024 / 1024)) GiB）"
mkdir -p "$PG_DATA_DIR" "$REDIS_DATA_DIR"
echo "持久化路径: PostgreSQL -> $PG_DATA_DIR, Redis -> $REDIS_DATA_DIR"

echo ""
echo "========== 1. Docker 安装与桥接配置 =========="
INSTALLED_DOCKER=
if ! command -v docker &>/dev/null; then
  echo "未检测到 Docker，开始安装（需要 sudo）..."
  if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    source /etc/os-release
    if [[ "$ID" =~ ^(debian|ubuntu)$ ]]; then
      curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
      sudo sh /tmp/get-docker.sh
      for u in "$USER" "$RUN_AS_USER"; do [[ -n "$u" ]] && sudo usermod -aG docker "$u" 2>/dev/null || true; done
      INSTALLED_DOCKER=1
    elif [[ "$ID" =~ ^(rhel|centos|fedora|rocky|almalinux)$ ]]; then
      sudo yum install -y yum-utils
      sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      sudo yum install -y docker-ce docker-ce-cli containerd.io
      sudo systemctl enable --now docker
      for u in "$USER" "$RUN_AS_USER"; do [[ -n "$u" ]] && sudo usermod -aG docker "$u" 2>/dev/null || true; done
      INSTALLED_DOCKER=1
    else
      echo "未识别的发行版 ($ID)，请手动安装 Docker 后重试。"
      exit 1
    fi
  else
    echo "无法检测系统类型，请手动安装 Docker 后重试。"
    exit 1
  fi
  # 刚安装后当前 shell 尚未加入 docker 组，后续用 sudo docker
  DOCKER_CMD="sudo docker"
  echo "Docker 安装完成。"
else
  DOCKER_CMD=docker
fi

# 配置 Docker 桥接：192.168.0.0/16，/25 子网（需 root）
DAEMON_JSON=/etc/docker/daemon.json
if sudo test -w /etc/docker 2>/dev/null; then
  if sudo test -f "$DAEMON_JSON" 2>/dev/null; then
    sudo cp "$DAEMON_JSON" "${DAEMON_JSON}.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  fi
  DAEMON_CONTENT="{\"bip\": \"$DOCKER_BRIDGE_BIP\", \"default-address-pools\": [{\"base\": \"$DOCKER_DEFAULT_POOL_BASE\", \"size\": $DOCKER_DEFAULT_POOL_SIZE}]}"
  echo "$DAEMON_CONTENT" | sudo tee "$DAEMON_JSON" >/dev/null
  echo "已写入 $DAEMON_JSON（bip=$DOCKER_BRIDGE_BIP，default-address-pools: $DOCKER_DEFAULT_POOL_BASE /$DOCKER_DEFAULT_POOL_SIZE），重启 Docker..."
  sudo systemctl restart docker 2>/dev/null || sudo service docker restart 2>/dev/null || true
  sleep 2
else
  echo "无法写入 $DAEMON_JSON（需要 root），跳过桥接配置；Docker 使用默认网段。"
fi

$DOCKER_CMD --version

echo ""
echo "========== 2. PostgreSQL =========="
if $DOCKER_CMD ps -a --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
  echo "容器 ${PG_CONTAINER} 已存在，跳过创建。若需重建请先: $DOCKER_CMD rm -f ${PG_CONTAINER}"
  $DOCKER_CMD start ${PG_CONTAINER} 2>/dev/null || true
else
  $DOCKER_CMD run -d \
    --name "$PG_CONTAINER" \
    --restart unless-stopped \
    -e POSTGRES_USER="$PG_USER" \
    -e POSTGRES_PASSWORD="$PG_PASSWORD" \
    -e POSTGRES_DB="$PG_DB" \
    -p "$PG_PORT:5432" \
    -v "$PG_DATA_DIR:/var/lib/postgresql/data" \
    postgres:16
  echo "PostgreSQL 已启动，端口 $PG_PORT，用户 $PG_USER，数据库 $PG_DB，数据目录 $PG_DATA_DIR"
fi

echo ""
echo "========== 3. Redis =========="
if $DOCKER_CMD ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
  echo "容器 ${REDIS_CONTAINER} 已存在，跳过创建。若需重建请先: $DOCKER_CMD rm -f ${REDIS_CONTAINER}"
  $DOCKER_CMD start ${REDIS_CONTAINER} 2>/dev/null || true
else
  $DOCKER_CMD run -d \
    --name "$REDIS_CONTAINER" \
    --restart unless-stopped \
    -p "$REDIS_PORT:6379" \
    -v "$REDIS_DATA_DIR:/data" \
    redis:7 redis-server --appendonly yes
  echo "Redis 已启动，端口 $REDIS_PORT，数据目录 $REDIS_DATA_DIR"
fi

echo ""
echo "========== 4. 验证 =========="
sleep 3
if $DOCKER_CMD exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c 'SELECT 1;' &>/dev/null; then
  echo "PostgreSQL 连接正常"
else
  echo "PostgreSQL 验证失败，请检查容器日志: $DOCKER_CMD logs $PG_CONTAINER"
  exit 1
fi
if $DOCKER_CMD exec "$REDIS_CONTAINER" redis-cli PING 2>/dev/null | grep -q PONG; then
  echo "Redis 连接正常"
else
  echo "Redis 验证失败，请检查容器日志: $DOCKER_CMD logs $REDIS_CONTAINER"
  exit 1
fi

echo ""
echo "完成。运行用户: $RUN_AS_USER（已加入 docker 组，与 install-netops/install-strix 一致）。"
echo "后端可配置 DATABASE_URL 与 REDIS_URL 指向本机 $PG_PORT / $REDIS_PORT。"
echo "示例: DATABASE_URL=postgresql://${PG_USER}:amberman%402025!@127.0.0.1:${PG_PORT}/${PG_DB}"
echo "      REDIS_URL=redis://127.0.0.1:${REDIS_PORT}/0"
