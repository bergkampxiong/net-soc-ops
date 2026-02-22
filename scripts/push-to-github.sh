#!/bin/bash
# 在本机终端执行此脚本，将当前分支和 v1.8 标签推送到 GitHub
# 使用前请确保本机已配置 GitHub 认证（如 gh auth login 或 git 凭证）

set -e
cd "$(dirname "$0")/.."
echo "正在推送到 origin (master + v1.8)..."
git push origin master
git push origin v1.8
echo "推送完成。"
