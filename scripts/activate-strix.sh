#!/usr/bin/env bash
# Strix 激活脚本：在 netops-backend/strix 目录执行 poetry install，
# 使 netops 任务执行与报告读取/统一报告功能可用（无需配置 STRIX_CLI_PATH）。
# 使用：bash scripts/activate-strix.sh  或从项目根目录执行
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STRIX_DIR="$PROJECT_ROOT/netops-backend/strix"

echo "Strix 激活脚本（netops 渗透测试与报告功能）"
echo "=============================================="

if [[ ! -d "$STRIX_DIR" ]]; then
  echo "错误: 未找到 Strix 目录 $STRIX_DIR"
  exit 1
fi

if [[ ! -f "$STRIX_DIR/pyproject.toml" ]]; then
  echo "错误: 未找到 $STRIX_DIR/pyproject.toml，请确认 Strix 源码已存在"
  exit 1
fi

echo "Strix 目录: $STRIX_DIR"
echo ""

POETRY_CMD=""
if command -v poetry &>/dev/null; then
  POETRY_CMD="poetry"
fi
if [[ -z "$POETRY_CMD" ]]; then
  echo "未检测到 poetry，尝试安装..."
  export PATH="${HOME}/.local/bin:${PATH}"
  # 优先使用 pipx（适合 externally-managed 系统 Python，如 Debian/Ubuntu）
  if ! command -v pipx &>/dev/null && command -v apt-get &>/dev/null && [[ $(id -u) -eq 0 ]]; then
    echo "检测到 root 与 apt，尝试安装 pipx..."
    apt-get update -qq && apt-get install -y pipx 2>/dev/null || true
    pipx ensurepath 2>/dev/null || true
    export PATH="${HOME}/.local/bin:/root/.local/bin:${PATH}"
  fi
  if command -v pipx &>/dev/null; then
    echo "使用 pipx 安装 poetry..."
    pipx install poetry
    pipx ensurepath 2>/dev/null || true
    export PATH="${HOME}/.local/bin:${PATH}"
    hash -r 2>/dev/null || true
    if command -v poetry &>/dev/null; then
      POETRY_CMD="poetry"
      echo "已安装 poetry，继续执行。"
    fi
  fi
  # 若无 pipx，尝试 pip（可能在某些环境下被禁止）
  if [[ -z "$POETRY_CMD" ]] && command -v python3 &>/dev/null; then
    if python3 -m pip install --user poetry 2>/dev/null; then
      hash -r 2>/dev/null || true
      export PATH="${HOME}/.local/bin:${PATH}"
      [[ -n $(command -v poetry 2>/dev/null) ]] && POETRY_CMD="poetry" && echo "已安装 poetry，继续执行。"
    fi
  fi
  # 若仍无 poetry 命令，尝试以模块方式运行（需已通过 pipx 等安装）
  if [[ -z "$POETRY_CMD" ]] && python3 -m poetry --version &>/dev/null; then
    POETRY_CMD="python3 -m poetry"
    echo "使用 python3 -m poetry 继续执行。"
  fi
fi
if [[ -z "$POETRY_CMD" ]]; then
  echo "错误: 无法使用 poetry。当前系统为「externally-managed」Python，建议用 pipx 安装："
  echo "  apt update && apt install -y pipx && pipx ensurepath"
  echo "  然后重新打开终端或执行: export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo "  再运行: pipx install poetry"
  echo "  最后重新执行本脚本: bash scripts/activate-strix.sh"
  echo "或参考: https://python-poetry.org/docs/#installation"
  exit 1
fi

echo "配置 Poetry 在项目内创建虚拟环境（便于 netops / Docker 识别）..."
(cd "$STRIX_DIR" && $POETRY_CMD config virtualenvs.in-project true --local 2>/dev/null || true)
# 移除已有 venv（含缓存中的），并删除项目内残留 .venv，以便在项目内新建
(cd "$STRIX_DIR" && $POETRY_CMD env remove --all 2>/dev/null || true)
rm -rf "$STRIX_DIR/.venv"
# 若 poetry 仍使用缓存 venv，删除该项目的缓存目录以强制在 netops-backend/strix 下创建 .venv
if [[ -d "$HOME/.cache/pypoetry/virtualenvs" ]]; then
  for v in "$HOME/.cache/pypoetry/virtualenvs"/strix-agent-*; do
    [[ -d "$v" ]] || continue
    rm -rf "$v" && echo "已删除缓存 venv: $v" && break
  done
fi

echo "正在执行 poetry install ..."
(cd "$STRIX_DIR" && $POETRY_CMD install)

STRIX_BIN="$STRIX_DIR/.venv/bin/strix"
if [[ ! -f "$STRIX_BIN" ]]; then
  # 若 poetry 将 venv 建在别处，通过 poetry env info -p 获取路径
  VENV_PATH=$(cd "$STRIX_DIR" && $POETRY_CMD env info -p 2>/dev/null) || true
  if [[ -n "$VENV_PATH" && -f "$VENV_PATH/bin/strix" ]]; then
    echo "Poetry 将虚拟环境建在: $VENV_PATH"
    echo "在项目内创建 .venv/bin 并链接 strix，便于 netops 自动识别..."
    mkdir -p "$STRIX_DIR/.venv/bin"
    ln -sf "$VENV_PATH/bin/strix" "$STRIX_DIR/.venv/bin/strix"
    STRIX_BIN="$STRIX_DIR/.venv/bin/strix"
    echo "已链接: $STRIX_BIN -> $VENV_PATH/bin/strix"
  else
    echo "错误: 未找到 strix 可执行文件。"
    echo "  - 若存在虚拟环境，请检查: cd $STRIX_DIR && $POETRY_CMD env info -p"
    echo "  - 并设置环境变量后启动 netops: export STRIX_CLI_PATH=<上述路径>/bin/strix"
    exit 1
  fi
fi

echo ""
echo "验证 CLI 可执行..."
if "$STRIX_BIN" --help &>/dev/null; then
  echo "已激活: $STRIX_BIN 可正常调用"
else
  echo "警告: $STRIX_BIN 存在但执行 --help 失败，请检查依赖"
fi

echo ""
echo "=============================================="
echo "Strix 已就绪。netops 会自动使用上述 .venv/bin/strix，"
echo "无需设置 STRIX_CLI_PATH。可调用 GET /api/config-module/strix/status 做自检。"
echo "=============================================="
