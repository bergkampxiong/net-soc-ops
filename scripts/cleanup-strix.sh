#!/usr/bin/env bash
# 清理当前环境中的 Strix：工程目录、虚拟环境、Docker 沙箱；并提示环境变量。
# 使用：bash scripts/cleanup-strix.sh  或  sudo bash scripts/cleanup-strix.sh（推荐，以删除 root 属主文件）
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STRIX_DIR="$PROJECT_ROOT/netops-backend/strix"
DATA_STRIX="$PROJECT_ROOT/netops-backend/data/strix_workspace"
STRIX_IMAGE="${STRIX_IMAGE:-ghcr.io/usestrix/strix-sandbox:0.1.12}"

echo "========== 清理 Strix 环境 =========="

# 1. 删除 Strix 工程目录（含 .venv、源码、strix_runs）
if [[ -d "$STRIX_DIR" ]]; then
  if [[ $EUID -eq 0 ]]; then
    rm -rf "$STRIX_DIR"
    echo "已删除: $STRIX_DIR"
  else
    rm -rf "$STRIX_DIR" 2>/dev/null || true
    if [[ -d "$STRIX_DIR" ]]; then
      echo "部分文件为 root 属主，删除失败。请使用 sudo 执行以完整清理: sudo bash scripts/cleanup-strix.sh"
    else
      echo "已删除: $STRIX_DIR"
    fi
  fi
else
  echo "不存在: $STRIX_DIR，跳过"
fi

# 2. 可选：删除 Strix 工作目录（任务产生的报告与运行目录）。带 -d 或 --data 参数时执行
if [[ -d "$DATA_STRIX" ]]; then
  if [[ "$1" == "-d" || "$1" == "--data" ]]; then
    rm -rf "$DATA_STRIX"
    echo "已删除: $DATA_STRIX"
  else
    echo "保留: $DATA_STRIX（若需删除请加参数: bash scripts/cleanup-strix.sh -d）"
  fi
fi

# 3. Docker：停止并删除 Strix 沙箱容器与镜像
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  containers=$(docker ps -aq --filter "name=strix-scan" 2>/dev/null || true)
  if [[ -n "$containers" ]]; then
    docker rm -f $containers 2>/dev/null || true
    echo "已删除 Strix 沙箱容器"
  fi
  if docker image inspect "$STRIX_IMAGE" &>/dev/null 2>&1; then
    docker rmi "$STRIX_IMAGE" 2>/dev/null && echo "已删除镜像: $STRIX_IMAGE" || echo "删除镜像需先停止依赖容器"
  fi
else
  echo "Docker 未运行或未安装，跳过容器/镜像清理"
fi

# 4. 环境变量提示
echo ""
echo "========== 环境变量 =========="
echo "若曾在 shell 或 .env 中设置过 Strix，请手动移除或 unset："
echo "  unset STRIX_CLI_PATH"
echo "  # 若在 netops-backend/.env 中有 STRIX_*、LLM_API_KEY 等 Strix 相关项，可编辑删除（配置也存于 DB strix_config 表）。"
echo ""
echo "清理完成。重新安装请执行: bash scripts/install-strix.sh"
echo "=========================================="
