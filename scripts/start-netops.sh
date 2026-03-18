#!/usr/bin/env bash
# NetOps 前后端服务启动脚本：先启动后端（后台），再启动前端（前台）；Ctrl+C 退出时会一并停止后端。
# 首次使用请先执行：bash scripts/install-netops.sh（安装 Python/Node 依赖并初始化数据库）
# 使用：bash scripts/start-netops.sh  或从项目根目录执行
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/netops-backend"
FRONTEND_DIR="$PROJECT_ROOT/netops-frontend"
VENV_ACTIVATE="$BACKEND_DIR/venv/bin/activate"
BACKEND_PID=""
DAEMON_MODE=0
BACKEND_PORT=8000
FRONTEND_PORT=8080

for arg in "$@"; do
  case "$arg" in
    --daemon)
      DAEMON_MODE=1
      ;;
  esac
done
if [[ "${NETOPS_DAEMON:-0}" == "1" ]]; then
  DAEMON_MODE=1
fi

is_port_listening() {
  local port="$1"
  ss -ltn "sport = :$port" 2>/dev/null | awk 'NR>1 {found=1} END {exit found ? 0 : 1}'
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "正在停止后端 (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup SIGINT SIGTERM

# 启动后端
if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "错误: 未找到后端目录 $BACKEND_DIR"
  exit 1
fi
if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "错误: 未检测到虚拟环境（缺少 $VENV_ACTIVATE）"
  echo "首次启动请先执行安装脚本（会安装 Python 依赖并初始化数据库）："
  echo "  bash $SCRIPT_DIR/install-netops.sh"
  exit 1
fi
cd "$BACKEND_DIR"
source "$VENV_ACTIVATE"
# 统一使用北京时区，避免重启后系统默认 UTC 导致时间显示偏差
export TZ=Asia/Shanghai
echo "启动后端: $BACKEND_DIR (端口 8000, TZ=$TZ)"
if is_port_listening "$BACKEND_PORT"; then
  :
else
if [[ "$DAEMON_MODE" -eq 1 ]]; then
  mkdir -p "$PROJECT_ROOT/.cursor"
  # 后台长期运行：单进程、不 reload，减少端口占用与启动竞态
  setsid nohup env NETOPS_UVICORN_RELOAD=0 python3 main.py >> "$PROJECT_ROOT/.cursor/netops-backend.log" 2>&1 &
else
  python3 main.py &
fi
BACKEND_PID=$!
fi
deactivate
cd "$PROJECT_ROOT"

# 等待后端就绪（reload/库表初始化可能超过 2 秒）
BACKEND_WAIT_SEC=60
for _ in $(seq 1 "$BACKEND_WAIT_SEC"); do
  if is_port_listening "$BACKEND_PORT"; then
    break
  fi
  sleep 1
done
if ! is_port_listening "$BACKEND_PORT"; then
  echo "后端启动失败（${BACKEND_WAIT_SEC}s 内端口 ${BACKEND_PORT} 未监听）。"
  echo "若日志中有 Address already in use，请先结束占用 8000 的进程后再启动。"
  if [[ -f "$PROJECT_ROOT/.cursor/netops-backend.log" ]]; then
    echo "--- 最近日志 ---"
    tail -n 30 "$PROJECT_ROOT/.cursor/netops-backend.log"
  fi
  exit 1
fi

# 启动前端（前台，占用当前终端）
if [[ ! -d "$FRONTEND_DIR" ]] || [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  echo "错误: 未找到前端目录或 package.json"
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 1
fi
echo "启动前端: $FRONTEND_DIR (开发 HTTPS 已启用)"
cd "$FRONTEND_DIR"
export HOST=0.0.0.0
if is_port_listening "$FRONTEND_PORT"; then
  if [[ "$DAEMON_MODE" -eq 1 ]]; then
    echo "守护模式启动完成，前端已在监听端口 $FRONTEND_PORT。"
    exit 0
  fi
fi
if [[ "$DAEMON_MODE" -eq 1 ]]; then
  mkdir -p "$PROJECT_ROOT/.cursor"
  setsid nohup env REACT_APP_DEV_HTTPS=true npm run start >> "$PROJECT_ROOT/.cursor/netops-frontend.log" 2>&1 &
  FRONTEND_PID=$!
  # 前端 dev 编译较慢，最多等 120 秒再判断 8080 是否监听
  FRONTEND_WAIT_SEC=120
  for _ in $(seq 1 "$FRONTEND_WAIT_SEC"); do
    if is_port_listening "$FRONTEND_PORT"; then
      break
    fi
    sleep 1
  done
  if ! is_port_listening "$FRONTEND_PORT"; then
    echo "前端启动失败（${FRONTEND_WAIT_SEC}s 内端口 ${FRONTEND_PORT} 未监听）。"
    if [[ -f "$PROJECT_ROOT/.cursor/netops-frontend.log" ]]; then
      echo "--- 前端最近日志 ---"
      tail -n 40 "$PROJECT_ROOT/.cursor/netops-frontend.log"
    fi
    kill "$BACKEND_PID" 2>/dev/null || true
    exit 1
  fi
  echo "守护模式启动完成，后端 PID: $BACKEND_PID，前端 PID: $FRONTEND_PID"
  exit 0
fi
REACT_APP_DEV_HTTPS=true npm run start
