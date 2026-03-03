#!/usr/bin/env bash
# 兼容旧引用：Strix 现由 install-strix.sh 安装（不保存源码、不使用 .venv）。
# 直接转发到 install-strix.sh。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/install-strix.sh" "$@"
