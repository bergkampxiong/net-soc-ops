#!/usr/bin/env bash
# 统一启动前后端开发环境（与当前实际启动方式一致）
# 后端：netops-backend + venv + python3 main.py
# 前端：netops-frontend + npm run start-all（代理 + 前端）
# 用法：在项目根目录执行 ./scripts/start-dev.sh

set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_DIR="$ROOT_DIR/netops-backend"
FRONTEND_DIR="$ROOT_DIR/netops-frontend"

BACKEND_PID=""
cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "正在停止后端 (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

[[ -d "$BACKEND_DIR" ]] || { echo "错误: 未找到 $BACKEND_DIR"; exit 1; }
[[ -d "$FRONTEND_DIR" ]] || { echo "错误: 未找到 $FRONTEND_DIR"; exit 1; }

# 后端：使用 venv，python3 main.py
if [[ ! -d "$BACKEND_DIR/venv" ]]; then
  echo "未检测到 venv，正在创建..."
  (cd "$BACKEND_DIR" && python3 -m venv venv)
fi
echo "启动后端 (venv + python3 main.py)..."
(cd "$BACKEND_DIR" && source venv/bin/activate && python3 main.py) &
BACKEND_PID=$!
echo "后端已启动 (PID $BACKEND_PID)，默认端口 8000"

sleep 2

# 前端：npm run start-all（代理 + 前端）
echo "启动前端 (npm run start-all)..."
cd "$FRONTEND_DIR"
npm run start-all
