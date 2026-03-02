#!/usr/bin/env bash
# NetOps 前后端服务启动脚本：先启动后端（后台），再启动前端（前台）；Ctrl+C 退出时会一并停止后端。
# 使用：bash scripts/start-netops.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/netops-backend"
FRONTEND_DIR="$PROJECT_ROOT/netops-frontend"
BACKEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "正在停止后端 (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 启动后端
if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "错误: 未找到后端目录 $BACKEND_DIR"
  exit 1
fi
cd "$BACKEND_DIR"
if [[ ! -d venv ]]; then
  echo "未检测到虚拟环境，正在创建 venv..."
  python3 -m venv venv
fi
source venv/bin/activate
echo "启动后端: $BACKEND_DIR (端口 8000)"
python3 main.py &
BACKEND_PID=$!
deactivate
cd "$PROJECT_ROOT"

# 等待后端就绪
sleep 2
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "后端启动失败。"
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
REACT_APP_DEV_HTTPS=true npm run start
