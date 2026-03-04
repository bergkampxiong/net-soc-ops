#!/usr/bin/env bash
# Strix 安装脚本（NetOps 渗透测试）：不在 git 中保存 Strix 源码，安装时从 usestrix/strix 拉取并安装。
# 1. Strix 安装在 /app/net-soc-ops/netops-backend/strix 目录下（二进制在 bin/，不使用 .venv）
# 2. Docker 镜像拉取后落在 Docker 数据目录；若已执行 install-netops.sh 则数据目录为 /app/docker
# 3. 执行任务时使用安装的二进制，不运行 .venv 环境
# 使用：bash scripts/install-strix.sh [--run-user=netops]  或  RUN_AS_USER=netops bash scripts/install-strix.sh
#       运行用户将获得 Strix 与 netops-backend/data 目录权限并被加入 docker 组（与 install-netops.sh 一致）
set -euo pipefail

REPO="usestrix/strix"
STRIX_IMAGE="ghcr.io/usestrix/strix-sandbox:0.1.12"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# 安装目录：与集成说明一致，优先 /app/net-soc-ops/netops-backend/strix，否则项目内 netops-backend/strix
if [[ -d "/app/net-soc-ops" ]]; then
  STRIX_BASE="/app/net-soc-ops/netops-backend/strix"
else
  STRIX_BASE="$PROJECT_ROOT/netops-backend/strix"
fi
BACKEND_DATA="$PROJECT_ROOT/netops-backend/data"
INSTALL_BIN_DIR="$STRIX_BASE/bin"
mkdir -p "$INSTALL_BIN_DIR"

# 运行用户：与 install-netops.sh 一致；环境变量 RUN_AS_USER > 命令行 --run-user= > 项目根 .run-user 文件 > 默认
STRIX_RUN_USER="${RUN_AS_USER:-}"
for arg in "$@"; do
  case "$arg" in
    --run-user=*) STRIX_RUN_USER="${arg#*=}" ; break ;;
  esac
done
[[ -z "$STRIX_RUN_USER" ]] && [[ -f "$PROJECT_ROOT/.run-user" ]] && STRIX_RUN_USER=$(cat "$PROJECT_ROOT/.run-user" | head -1)
[[ -z "$STRIX_RUN_USER" ]] && STRIX_RUN_USER=$([[ "$(id -u 2>/dev/null)" -eq 0 ]] && echo "netops" || echo "$USER")

MUTED='\033[0;2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

raw_os=$(uname -s)
os=$(echo "$raw_os" | tr '[:upper:]' '[:lower:]')
case "$raw_os" in
  Darwin*) os="macos" ;;
  Linux*)  os="linux" ;;
  MINGW*|MSYS*|CYGWIN*) os="windows" ;;
  *) echo -e "${RED}Unsupported OS: $raw_os${NC}"; exit 1 ;;
esac

arch=$(uname -m)
[[ "$arch" == "aarch64" ]] && arch="arm64"
[[ "$arch" == "x86_64" ]] && arch="x86_64"
if [[ "$os" == "macos" && "$arch" == "x86_64" ]]; then
  rosetta=$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)
  [[ "$rosetta" == "1" ]] && arch="arm64"
fi

combo="$os-$arch"
case "$combo" in
  linux-x86_64|macos-x86_64|macos-arm64|windows-x86_64) ;;
  *) echo -e "${RED}Unsupported arch: $combo（官方仅提供 linux-x86_64 / macos / windows-x86_64）${NC}"; exit 1 ;;
esac

requested_version="${VERSION:-}"
if [[ -z "$requested_version" ]]; then
  api_json=$(curl -sSf "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null) || true
  if command -v jq &>/dev/null && [[ -n "$api_json" ]]; then
    specific_version=$(echo "$api_json" | jq -r '.tag_name // empty' | sed 's/^v//')
  fi
  [[ -z "$specific_version" ]] && specific_version=$(echo "$api_json" | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p' 2>/dev/null)
  [[ -z "$specific_version" ]] && specific_version="0.8.2"
else
  specific_version="$requested_version"
fi

archive_ext=".tar.gz"
[[ "$os" == "windows" ]] && archive_ext=".zip"
filename="strix-${specific_version}-${combo}${archive_ext}"
url="https://github.com/$REPO/releases/download/v${specific_version}/$filename"

echo -e "${CYAN}Strix 安装（NetOps 渗透测试）${NC}"
echo "安装目录: $STRIX_BASE"
echo "二进制目录: $INSTALL_BIN_DIR"
echo ""

# 若已安装同版本则跳过下载
if [[ -x "$INSTALL_BIN_DIR/strix" ]]; then
  installed_ver=$("$INSTALL_BIN_DIR/strix" --version 2>/dev/null | awk '{print $2}' || echo "")
  if [[ "$installed_ver" == "$specific_version" ]]; then
    echo -e "${GREEN}已安装 Strix $specific_version，跳过下载。${NC}"
  else
    echo -e "${MUTED}已存在 $installed_ver，将覆盖为 $specific_version${NC}"
  fi
fi

if [[ ! -x "$INSTALL_BIN_DIR/strix" ]] || [[ "$("$INSTALL_BIN_DIR/strix" --version 2>/dev/null | awk '{print $2}')" != "$specific_version" ]]; then
  echo -e "${MUTED}下载 $url ...${NC}"
  tmp_dir=$(mktemp -d)
  if ! curl -sSfL -o "$tmp_dir/$filename" "$url"; then
    echo -e "${RED}下载失败，请检查网络或版本 v$specific_version 是否存在。${NC}"
    rm -rf "$tmp_dir"
    exit 1
  fi
  if [[ "$os" == "windows" ]]; then
    unzip -q -o "$tmp_dir/$filename" -d "$tmp_dir"
    mv -f "$tmp_dir/strix-${specific_version}-${combo}.exe" "$INSTALL_BIN_DIR/strix.exe" 2>/dev/null || true
  else
    tar -xzf "$tmp_dir/$filename" -C "$tmp_dir"
    mv -f "$tmp_dir/strix-${specific_version}-${combo}" "$INSTALL_BIN_DIR/strix"
    chmod 755 "$INSTALL_BIN_DIR/strix"
  fi
  rm -rf "$tmp_dir"
  echo -e "${GREEN}Strix $specific_version 已安装到 $INSTALL_BIN_DIR${NC}"
fi

# Docker：检查并拉取沙箱镜像（镜像存储位置由 Docker daemon 配置决定，若已执行 install-netops 则在 /app/docker）
echo ""
if ! command -v docker &>/dev/null; then
  echo -e "${YELLOW}未检测到 docker，请先安装并启动 Docker。Strix 沙箱需要 Docker。${NC}"
else
  if ! docker info &>/dev/null; then
    echo -e "${YELLOW}Docker 未运行，请启动后执行: docker pull $STRIX_IMAGE${NC}"
  else
    if docker image inspect "$STRIX_IMAGE" &>/dev/null; then
      echo -e "${GREEN}沙箱镜像已存在: $STRIX_IMAGE${NC}"
    else
      echo -e "${MUTED}拉取沙箱镜像（可能较久）...${NC}"
      if docker pull "$STRIX_IMAGE"; then
        echo -e "${GREEN}沙箱镜像拉取成功${NC}"
      else
        echo -e "${YELLOW}拉取失败，可稍后手动: docker pull $STRIX_IMAGE${NC}"
      fi
    fi
    # 若 Docker 配置了 data-root 在 /app 下则提示
    data_root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)
    if [[ -n "$data_root" && "$data_root" == /app* ]]; then
      echo -e "${MUTED}Docker 数据目录: $data_root（已在 /app 下）${NC}"
    else
      echo -e "${MUTED}若需将 Docker 镜像与数据放在 /app 下，请先执行 scripts/install-netops.sh 配置 Docker。${NC}"
    fi
    # 将运行用户加入 docker 组，与 install-netops.sh 一致
    if id "$STRIX_RUN_USER" &>/dev/null; then
      sudo usermod -aG docker "$STRIX_RUN_USER" 2>/dev/null && echo -e "${GREEN}已将用户 $STRIX_RUN_USER 加入 docker 组${NC}" || true
    fi
  fi
fi

# 将 Strix 与后端 data 目录属主设为运行用户（需 root）
if [[ "$(id -u 2>/dev/null)" -eq 0 ]] && id "$STRIX_RUN_USER" &>/dev/null; then
  echo -e "${MUTED}将 Strix 与数据目录属主设为 $STRIX_RUN_USER ...${NC}"
  chown -R "$STRIX_RUN_USER:$STRIX_RUN_USER" "$STRIX_BASE" 2>/dev/null || true
  mkdir -p "$BACKEND_DATA"
  chown -R "$STRIX_RUN_USER:$STRIX_RUN_USER" "$BACKEND_DATA" 2>/dev/null || true
fi

STRIX_CMD="$INSTALL_BIN_DIR/strix"
[[ "$os" == "windows" ]] && STRIX_CMD="$INSTALL_BIN_DIR/strix.exe"
echo ""
if [[ -x "$STRIX_CMD" ]]; then
  echo -e "${GREEN}Strix 已就绪（不使用 .venv）: $STRIX_CMD${NC}"
  echo "NetOps 将优先使用该路径；也可设置环境变量: export STRIX_CLI_PATH=$STRIX_CMD"
  echo "自检接口: GET /api/config-module/strix/status"
  echo ""
  echo -e "${CYAN}【运行用户】${NC} 当前指定: $STRIX_RUN_USER（Strix 与 data 目录已赋予该用户；已加入 docker 组。请以此用户启动后端以减少权限问题。）"
  echo "  • 数据目录: $BACKEND_DATA（Strix 工作目录在其下 strix_workspace/）"
else
  echo -e "${RED}未找到可执行文件 $STRIX_CMD${NC}"
  exit 1
fi
echo ""
