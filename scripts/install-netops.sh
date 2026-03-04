#!/usr/bin/env bash
# NetOps 前后端安装脚本：安装 Docker（含桥接与数据目录）、Python3、Node/npm（若缺失），由用户输入数据库/Redis 连接参数并写入 .env，安装依赖并初始化库表。
# 不安装数据库：PostgreSQL/Redis 需在其它机器或环境单独安装，本脚本仅配置连接参数。
# Docker：若未安装则安装；桥接 192.168.0.0/16、子网 /25；镜像与数据目录置于 /app 下。
# 安装目录约定：项目建议放在 /app/net-soc-ops 下；也可在任意路径执行，脚本以当前仓库为项目根。
# 使用：bash scripts/install-netops.sh [选项]
#       选项示例：--db-host=172.19.128.242 --db-port=5432 --db-user=amber --db-name=netops
#       --run-user=netops  指定运行前后端的用户（将拥有工程目录权限并加入 docker 组，减少运行时权限问题）
#       也可在下方「脚本内默认配置」中直接修改默认值。
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/netops-backend"
FRONTEND_DIR="$PROJECT_ROOT/netops-frontend"
ENV_FILE="$BACKEND_DIR/.env"
VENV_ACTIVATE="$BACKEND_DIR/venv/bin/activate"

# ---------- 脚本内默认配置：其他用户在新环境安装时直接回车即用此处参数写入 .env 与 database/config.py ----------
# 交付给客户前可在此修改为对方环境的数据库/Redis 地址，安装时客户只需输入密码即可。
SCRIPT_DEFAULT_DB_HOST="127.0.0.1"
SCRIPT_DEFAULT_DB_PORT="5432"
SCRIPT_DEFAULT_DB_USER="amber"
SCRIPT_DEFAULT_DB_NAME="netops"
SCRIPT_DEFAULT_REDIS_HOST="127.0.0.1"
SCRIPT_DEFAULT_REDIS_PORT="6379"
SCRIPT_DEFAULT_REDIS_DB="0"
SCRIPT_DEFAULT_RUN_USER="netops"

# 解析命令行参数（--db-host=IP、--run-user= 等），覆盖下面的默认值
parse_install_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --db-host=*)   DEFAULT_DB_HOST="${1#*=}" ;;
      --db-port=*)   DEFAULT_DB_PORT="${1#*=}" ;;
      --db-user=*)   DEFAULT_DB_USER="${1#*=}" ;;
      --db-name=*)   DEFAULT_DB_NAME="${1#*=}" ;;
      --redis-host=*) DEFAULT_REDIS_HOST="${1#*=}" ;;
      --redis-port=*) DEFAULT_REDIS_PORT="${1#*=}" ;;
      --redis-db=*)  DEFAULT_REDIS_DB="${1#*=}" ;;
      --run-user=*) DEFAULT_RUN_USER="${1#*=}" ;;
    esac
    shift
  done
}
parse_install_args "$@"

# 默认数据库/Redis 参数：命令行 > 环境变量 > 脚本内默认（交互时直接回车即用此默认）
DEFAULT_DB_HOST="${DEFAULT_DB_HOST:-${DB_HOST:-$SCRIPT_DEFAULT_DB_HOST}}"
DEFAULT_DB_PORT="${DEFAULT_DB_PORT:-${DB_PORT:-$SCRIPT_DEFAULT_DB_PORT}}"
DEFAULT_DB_USER="${DEFAULT_DB_USER:-${DB_USER:-$SCRIPT_DEFAULT_DB_USER}}"
DEFAULT_DB_NAME="${DEFAULT_DB_NAME:-${DB_NAME:-$SCRIPT_DEFAULT_DB_NAME}}"
DEFAULT_REDIS_HOST="${DEFAULT_REDIS_HOST:-${REDIS_HOST:-$SCRIPT_DEFAULT_REDIS_HOST}}"
DEFAULT_REDIS_PORT="${DEFAULT_REDIS_PORT:-${REDIS_PORT:-$SCRIPT_DEFAULT_REDIS_PORT}}"
DEFAULT_REDIS_DB="${DEFAULT_REDIS_DB:-${REDIS_DB:-$SCRIPT_DEFAULT_REDIS_DB}}"

# 运行用户：拥有工程目录权限并加入 docker 组；环境变量 RUN_AS_USER > 命令行 --run-user= > 默认（root 时为 netops，否则为当前用户）
if [[ -n "${RUN_AS_USER:-}" ]]; then
  : # 已由环境变量指定
elif [[ -n "${DEFAULT_RUN_USER:-}" ]]; then
  RUN_AS_USER="$DEFAULT_RUN_USER"
elif [[ "$(id -u 2>/dev/null)" -eq 0 ]]; then
  RUN_AS_USER="${SCRIPT_DEFAULT_RUN_USER}"
else
  RUN_AS_USER="$USER"
fi
[[ -z "$RUN_AS_USER" ]] && RUN_AS_USER="netops"

echo "========== NetOps 安装脚本 =========="
echo "项目根目录: $PROJECT_ROOT"
echo "运行用户: $RUN_AS_USER（将赋予工程所有权与 docker 组）"
echo ""

# ---------- 0. Docker 安装与配置（桥接 192.168.0.0/16、/25，镜像与数据放到 /app 下）----------
DOCKER_APP_ROOT="/app"
DOCKER_DATA_ROOT="${DOCKER_APP_ROOT}/docker"
DOCKER_BRIDGE_BIP="192.168.0.1/25"
DOCKER_DEFAULT_POOL_BASE="192.168.0.0/16"
DOCKER_DEFAULT_POOL_SIZE=25

install_docker_and_configure() {
  if [[ ! -d "$DOCKER_APP_ROOT" ]]; then
    echo "[Docker] 创建目录 $DOCKER_APP_ROOT（需 sudo）..."
    sudo mkdir -p "$DOCKER_APP_ROOT" 2>/dev/null || true
    if [[ ! -d "$DOCKER_APP_ROOT" ]]; then
      echo "请使用 sudo 创建目录: sudo mkdir -p $DOCKER_APP_ROOT && sudo chown \$(whoami) $DOCKER_APP_ROOT"
      exit 1
    fi
  fi
  sudo mkdir -p "$DOCKER_DATA_ROOT" 2>/dev/null || true

  if ! command -v docker &>/dev/null; then
    echo "[Docker] 未检测到 Docker，开始安装（需要 sudo）..."
    if [[ -f /etc/os-release ]]; then
      # shellcheck source=/dev/null
      source /etc/os-release
      if [[ "$ID" =~ ^(debian|ubuntu)$ ]]; then
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo sh /tmp/get-docker.sh
        for u in "$USER" "$RUN_AS_USER"; do [[ -n "$u" ]] && sudo usermod -aG docker "$u" 2>/dev/null || true; done
      elif [[ "$ID" =~ ^(rhel|centos|fedora|rocky|almalinux)$ ]]; then
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io
        sudo systemctl enable --now docker
        for u in "$USER" "$RUN_AS_USER"; do [[ -n "$u" ]] && sudo usermod -aG docker "$u" 2>/dev/null || true; done
      else
        echo "未识别的发行版 ($ID)，请手动安装 Docker 后重试。"
        exit 1
      fi
    else
      echo "无法检测系统类型，请手动安装 Docker 后重试。"
      exit 1
    fi
    echo "[Docker] 安装完成。"
  else
    echo "[Docker] 已安装: $(docker --version 2>/dev/null || true)"
  fi

  DAEMON_JSON=/etc/docker/daemon.json
  if sudo test -w /etc/docker 2>/dev/null; then
    if sudo test -f "$DAEMON_JSON" 2>/dev/null; then
      sudo cp "$DAEMON_JSON" "${DAEMON_JSON}.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
    fi
    # data-root：镜像与容器数据存于 /app 下；桥接 192.168.0.0/16，子网 /25
    DAEMON_CONTENT="{\"data-root\": \"$DOCKER_DATA_ROOT\", \"bip\": \"$DOCKER_BRIDGE_BIP\", \"default-address-pools\": [{\"base\": \"$DOCKER_DEFAULT_POOL_BASE\", \"size\": $DOCKER_DEFAULT_POOL_SIZE}]}"
    echo "$DAEMON_CONTENT" | sudo tee "$DAEMON_JSON" >/dev/null
    echo "[Docker] 已配置: 数据目录=$DOCKER_DATA_ROOT, 桥接=$DOCKER_BRIDGE_BIP, 地址池=$DOCKER_DEFAULT_POOL_BASE/$DOCKER_DEFAULT_POOL_SIZE"
    sudo systemctl restart docker 2>/dev/null || sudo service docker restart 2>/dev/null || true
    sleep 2
  else
    echo "[Docker] 无法写入 $DAEMON_JSON（需要 root），跳过桥接与数据目录配置。"
  fi
}

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

# ---------- 2.5 确保 python3-venv 可用（Debian/Ubuntu 创建 venv 需此包）----------
ensure_python3_venv() {
  if python3 -c "import ensurepip" 2>/dev/null; then
    return
  fi
  echo "[python3-venv] 当前 Python 无法创建 venv（缺少 ensurepip），尝试安装 python3-venv..."
  if [[ -f /etc/debian_version ]]; then
    PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || true
    if [[ -n "$PYVER" ]]; then
      sudo apt-get update -qq
      sudo apt-get install -y "python${PYVER}-venv" 2>/dev/null || sudo apt-get install -y python3-venv
    else
      sudo apt-get update -qq
      sudo apt-get install -y python3-venv
    fi
    echo "[python3-venv] 安装完成"
  else
    echo "错误: 当前系统无法创建 Python 虚拟环境，请手动安装 python3-venv 或等价包后重试。"
    exit 1
  fi
}

# ---------- 2.6 确保 pip 编译依赖（python-ldap 等需 Python 头文件与 OpenLDAP 开发库）----------
ensure_pip_build_deps() {
  if [[ ! -f /etc/debian_version ]]; then
    return
  fi
  echo "[构建依赖] 安装 python3-dev、libldap2-dev、libsasl2-dev（供 python-ldap 编译）..."
  sudo apt-get update -qq
  sudo apt-get install -y python3-dev libldap2-dev libsasl2-dev 2>/dev/null || {
    PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || true
    if [[ -n "$PYVER" ]]; then
      sudo apt-get install -y "python${PYVER}-dev" libldap2-dev libsasl2-dev
    else
      sudo apt-get install -y python3-dev libldap2-dev libsasl2-dev
    fi
  }
  echo "[构建依赖] 完成"
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
  echo "已写入 $ENV_FILE"

  # 同步写入 database/config.py，便于其他模块与 int_all_db 直接读同一套配置
  export BACKEND_DIR
  export _CFG_DB_HOST="$DB_HOST"
  export _CFG_DB_PORT="$DB_PORT"
  export _CFG_DB_USER="$DB_USER"
  export _CFG_DB_NAME="$DB_NAME"
  export _CFG_DB_PASS="$DB_PASSWORD"
  export _CFG_REDIS_HOST="$REDIS_HOST"
  export _CFG_REDIS_PORT="$REDIS_PORT"
  export _CFG_REDIS_DB="$REDIS_DB"
  python3 << 'PYCONFIG'
import os
h = os.environ.get("_CFG_DB_HOST", "127.0.0.1")
p = int(os.environ.get("_CFG_DB_PORT", "5432"))
u = os.environ.get("_CFG_DB_USER", "netops")
db = os.environ.get("_CFG_DB_NAME", "netops")
pw = os.environ.get("_CFG_DB_PASS", "")
rh = os.environ.get("_CFG_REDIS_HOST", "127.0.0.1")
rp = int(os.environ.get("_CFG_REDIS_PORT", "6379"))
rd = int(os.environ.get("_CFG_REDIS_DB", "0"))
content = '''import os
from typing import Dict
from urllib.parse import quote_plus

# 数据库配置
DATABASE_CONFIG = {
    "host": ''' + repr(h) + ''',
    "port": ''' + str(p) + ''',
    "database": ''' + repr(db) + ''',
    "user": ''' + repr(u) + ''',
    "password": ''' + repr(pw) + ''',
}

# Redis配置
REDIS_CONFIG = {
    "host": ''' + repr(rh) + ''',
    "port": ''' + str(rp) + ''',
    "db": ''' + str(rd) + ''',
}

# 构建数据库URL
def get_database_url(db_name: str = "netops") -> str:
    """构建数据库连接URL"""
    config = DATABASE_CONFIG.copy()
    config["database"] = db_name
    password = quote_plus(config['password'])
    return f"postgresql://{config['user']}:{password}@{config['host']}:{config['port']}/{config['database']}"

# 构建Redis URL
def get_redis_url(db: int = 0) -> str:
    """构建Redis连接URL"""
    config = REDIS_CONFIG.copy()
    config["db"] = db
    return f"redis://{config['host']}:{config['port']}/{config['db']}"

# 导出环境变量
os.environ["DATABASE_URL"] = get_database_url()
os.environ["CMDB_DATABASE_URL"] = get_database_url()  # 使用同一个数据库
os.environ["REDIS_URL"] = get_redis_url()
'''
out_path = os.path.join(os.environ.get("BACKEND_DIR", ""), "database", "config.py")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(content)
PYCONFIG
  unset _CFG_DB_HOST _CFG_DB_PORT _CFG_DB_USER _CFG_DB_NAME _CFG_DB_PASS _CFG_REDIS_HOST _CFG_REDIS_PORT _CFG_REDIS_DB
  echo "已写入 $BACKEND_DIR/database/config.py"
  echo ""
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
  if [[ ! -f "$VENV_ACTIVATE" ]]; then
    python3 -m venv "$BACKEND_DIR/venv"
    echo "已创建虚拟环境 $BACKEND_DIR/venv"
  fi
  source "$VENV_ACTIVATE"
  pip install -q -r requirements.txt
  echo "已安装 Python 依赖"
  if [[ -f int_all_db.py ]]; then
    if ! python3 int_all_db.py; then
      echo ""
      echo "数据库初始化失败: 无法连接 PostgreSQL（请检查 .env 中 DB_HOST/端口及数据库是否已启动、网络是否可达）。"
      echo "修复连接后请手动执行: cd $BACKEND_DIR && source venv/bin/activate && python3 int_all_db.py"
      echo ""
    fi
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

# ---------- 运行用户权限：将工程目录及后端 data 属主设为 RUN_AS_USER，并写入 .run-user 供 install-strix 等读取 ----------
apply_run_user_permissions() {
  if ! id "$RUN_AS_USER" &>/dev/null; then
    echo "[运行用户] 用户 $RUN_AS_USER 不存在，跳过 chown；请先创建用户或使用 --run-user= 指定已存在用户。"
    return 0
  fi
  echo "$RUN_AS_USER" > "$PROJECT_ROOT/.run-user"
  if [[ "$(id -u 2>/dev/null)" -eq 0 ]]; then
    echo "[运行用户] 将工程目录及数据目录属主设为 $RUN_AS_USER ..."
    chown -R "$RUN_AS_USER:$RUN_AS_USER" "$PROJECT_ROOT" 2>/dev/null || true
    mkdir -p "$BACKEND_DIR/data"
    chown -R "$RUN_AS_USER:$RUN_AS_USER" "$BACKEND_DIR/data" 2>/dev/null || true
    chown "$RUN_AS_USER" "$PROJECT_ROOT/.run-user" 2>/dev/null || true
    echo "[运行用户] 已赋予 $RUN_AS_USER 对 $PROJECT_ROOT 及 $BACKEND_DIR/data 的所有权；该用户已加入 docker 组（需重新登录或重启服务后生效）。"
  else
    echo "[运行用户] 当前非 root，未执行 chown；若需将属主改为 $RUN_AS_USER，请使用 sudo 重新运行本脚本或手动: sudo chown -R $RUN_AS_USER:$RUN_AS_USER $PROJECT_ROOT"
  fi
}

# ---------- 主流程 ----------
install_docker_and_configure
install_python3
ensure_python3_venv
ensure_pip_build_deps
install_node_npm
write_env_file
install_backend
install_frontend
apply_run_user_permissions

echo ""
echo "========== 安装完成 =========="
echo "项目路径: $PROJECT_ROOT"
echo "运行用户: $RUN_AS_USER（工程目录属主，已加入 docker 组；请以此用户启动前后端以减少权限问题）"
echo "后端 .env: $ENV_FILE"
echo "启动后端: cd $BACKEND_DIR && source venv/bin/activate && python3 main.py"
echo "启动前端: cd $FRONTEND_DIR && npm run start"
echo "生产构建: cd $FRONTEND_DIR && npm run build"
echo "数据库在其它机器安装；本机需自建时可选: sudo bash $SCRIPT_DIR/setup-docker-databases.sh --run-user=$RUN_AS_USER"
