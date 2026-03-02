#!/usr/bin/env bash
# NetOps 前后端安装脚本：安装 Python3、Node/npm（若缺失），由用户输入数据库/Redis 连接参数并写入 .env，安装依赖并初始化库表。
# 不安装数据库：PostgreSQL/Redis 需在其它机器或环境单独安装，本脚本仅配置连接参数。
# 安装目录约定：项目建议放在 /app/net-soc-ops 下；也可在任意路径执行，脚本以当前仓库为项目根。
# 使用：bash scripts/install-netops.sh  或  sudo bash scripts/install-netops.sh（安装系统包时可能需要 sudo）
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/netops-backend"
FRONTEND_DIR="$PROJECT_ROOT/netops-frontend"
ENV_FILE="$BACKEND_DIR/.env"

# 默认数据库/Redis 参数（仅用于交互时的默认提示，实际以用户输入或现有 .env 为准）
DEFAULT_DB_HOST="${DB_HOST:-127.0.0.1}"
DEFAULT_DB_PORT="${DB_PORT:-5432}"
DEFAULT_DB_USER="${DB_USER:-amber}"
DEFAULT_DB_NAME="${DB_NAME:-netops}"
DEFAULT_REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
DEFAULT_REDIS_PORT="${REDIS_PORT:-6379}"
DEFAULT_REDIS_DB="${REDIS_DB:-0}"

echo "========== NetOps 安装脚本 =========="
echo "项目根目录: $PROJECT_ROOT"
echo ""

# ---------- 1. 检测并安装 Python3 ----------
install_python3() {
  if command -v python3 &>/dev/null; then
    echo "[Python3] 已安装: $(python3 --version)"
    return
  fi
  echo "[Python3] 未检测到，正在安装..."
  if [[ -f /etc/debian_version ]]; then
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-venv python3-pip
  elif [[ -f /etc/redhat-release ]]; then
    sudo yum install -y python3 python3-pip
  else
    echo "请手动安装 Python 3.10+ 后重试。"
    exit 1
  fi
  echo "[Python3] 安装完成: $(python3 --version)"
}

# ---------- 2. 检测并安装 Node.js / npm ----------
install_node_npm() {
  if command -v node &>/dev/null && command -v npm &>/dev/null; then
    echo "[Node/npm] 已安装: node $(node -v), npm $(npm -v)"
    return
  fi
  echo "[Node/npm] 未检测到或不全，正在安装..."
  if [[ -f /etc/debian_version ]]; then
    sudo apt-get update -qq
    sudo apt-get install -y nodejs npm || true
    if ! command -v node &>/dev/null; then
      echo "Debian/Ubuntu 请安装 Node.js 16+（如: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs）"
      exit 1
    fi
  elif [[ -f /etc/redhat-release ]]; then
    sudo yum install -y nodejs npm 2>/dev/null || true
    if ! command -v node &>/dev/null; then
      echo "CentOS/RHEL 请安装 Node.js 16+（如: 使用 NodeSource 或 dnf install nodejs）"
      exit 1
    fi
  else
    echo "请手动安装 Node.js 16+ 与 npm 后重试。"
    exit 1
  fi
  echo "[Node/npm] 安装完成: node $(node -v), npm $(npm -v)"
}

# ---------- 3. 收集数据库与 Redis 环境变量 ----------
write_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    echo ""
    read -p "已存在 $ENV_FILE，是否覆盖？(y/N): " overwrite
    if [[ "${overwrite,,}" != "y" && "${overwrite,,}" != "yes" ]]; then
      echo "保留现有 .env，跳过写入。"
      return
    fi
  fi

  echo ""
  echo "请输入数据库与 Redis 配置（直接回车使用默认值）。"
  read -p "PostgreSQL 主机 [${DEFAULT_DB_HOST}]: " DB_HOST_IN
  read -p "PostgreSQL 端口 [${DEFAULT_DB_PORT}]: " DB_PORT_IN
  read -p "PostgreSQL 用户 [${DEFAULT_DB_USER}]: " DB_USER_IN
  read -sp "PostgreSQL 密码: " DB_PASSWORD_IN
  echo ""
  read -p "PostgreSQL 数据库名 [${DEFAULT_DB_NAME}]: " DB_NAME_IN
  read -p "Redis 主机 [${DEFAULT_REDIS_HOST}]: " REDIS_HOST_IN
  read -p "Redis 端口 [${DEFAULT_REDIS_PORT}]: " REDIS_PORT_IN
  read -p "Redis DB 编号 [${DEFAULT_REDIS_DB}]: " REDIS_DB_IN
  read -p "SECRET_KEY（JWT 等，留空将自动生成）: " SECRET_KEY_IN

  DB_HOST="${DB_HOST_IN:-$DEFAULT_DB_HOST}"
  DB_PORT="${DB_PORT_IN:-$DEFAULT_DB_PORT}"
  DB_USER="${DB_USER_IN:-$DEFAULT_DB_USER}"
  DB_PASSWORD="${DB_PASSWORD_IN}"
  DB_NAME="${DB_NAME_IN:-$DEFAULT_DB_NAME}"
  REDIS_HOST="${REDIS_HOST_IN:-$DEFAULT_REDIS_HOST}"
  REDIS_PORT="${REDIS_PORT_IN:-$DEFAULT_REDIS_PORT}"
  REDIS_DB="${REDIS_DB_IN:-$DEFAULT_REDIS_DB}"

  # 密码中的 @ 等需 URL 编码（如 @ -> %40），通过环境变量传入避免特殊字符问题
  export _DB_PASS="$DB_PASSWORD"
  DB_PASSWORD_ENC=$(python3 -c "import urllib.parse, os; print(urllib.parse.quote(os.environ.get('_DB_PASS', ''), safe=''))")
  unset _DB_PASS

  DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD_ENC}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
  CMDB_DATABASE_URL="$DATABASE_URL"
  REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}"

  if [[ -z "$SECRET_KEY_IN" ]]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  else
    SECRET_KEY="$SECRET_KEY_IN"
  fi

  mkdir -p "$BACKEND_DIR"
  cat > "$ENV_FILE" << EOF
# NetOps 后端环境变量（由 scripts/install-netops.sh 生成/更新）
DATABASE_URL=$DATABASE_URL
CMDB_DATABASE_URL=$CMDB_DATABASE_URL
REDIS_URL=$REDIS_URL
SECRET_KEY=$SECRET_KEY
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_USER=$DB_USER
DB_NAME=$DB_NAME
REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT
REDIS_DB=$REDIS_DB
EOF
  echo ""
  echo "已写入 $ENV_FILE"
}

# ---------- 4. 后端：venv + pip + 数据库初始化 ----------
install_backend() {
  if [[ ! -d "$BACKEND_DIR" ]]; then
    echo "错误: 未找到后端目录 $BACKEND_DIR"
    exit 1
  fi
  cd "$BACKEND_DIR"
  if [[ ! -f requirements.txt ]]; then
    echo "错误: 未找到 requirements.txt"
    exit 1
  fi
  echo ""
  echo "========== 后端依赖与数据库初始化 =========="
  if [[ ! -d venv ]]; then
    python3 -m venv venv
    echo "已创建虚拟环境 venv"
  fi
  source venv/bin/activate
  pip install -q -r requirements.txt
  echo "已安装 Python 依赖"
  if [[ -f int_all_db.py ]]; then
    python3 int_all_db.py
  else
    echo "未找到 int_all_db.py，请手动执行数据库初始化。"
  fi
  deactivate
  echo "后端安装完成。"
}

# ---------- 5. 前端：npm install ----------
install_frontend() {
  if [[ ! -d "$FRONTEND_DIR" ]]; then
    echo "未找到前端目录 $FRONTEND_DIR，跳过前端依赖安装。"
    return
  fi
  if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
    echo "未找到 package.json，跳过前端。"
    return
  fi
  echo ""
  echo "========== 前端依赖 =========="
  cd "$FRONTEND_DIR"
  npm install
  echo "前端依赖安装完成。"
}

# ---------- 主流程 ----------
install_python3
install_node_npm
write_env_file
install_backend
install_frontend

echo ""
echo "========== 安装完成 =========="
echo "项目路径: $PROJECT_ROOT"
echo "后端 .env: $ENV_FILE"
echo "启动后端: cd $BACKEND_DIR && source venv/bin/activate && python3 main.py"
echo "启动前端: cd $FRONTEND_DIR && npm run start"
echo "生产构建: cd $FRONTEND_DIR && npm run build"
echo "数据库在其它机器安装；本机需自建时可选: sudo bash $SCRIPT_DIR/setup-docker-databases.sh"
