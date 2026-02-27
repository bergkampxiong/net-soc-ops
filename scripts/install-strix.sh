#!/usr/bin/env bash
# Strix 安装脚本
# 1. 安装 Docker 并配置桥接子网 192.168.0.0/25 避免 IP 冲突
# 2. 将 strix 工程代码克隆到 netops-backend 下单独目录
# 3. 确保 netops 用户对该路径有完整权限
#
# 用法: sudo bash scripts/install-strix.sh
# 或:   sudo ./scripts/install-strix.sh

set -e

STRIX_REPO="${STRIX_REPO:-https://github.com/usestrix/strix.git}"
STRIX_BRANCH="${STRIX_BRANCH:-main}"
BACKEND_DIR="${BACKEND_DIR:-/app/net-soc-ops/netops-backend}"
STRIX_DIR="${BACKEND_DIR}/strix"
DOCKER_BIP="${DOCKER_BIP:-192.168.0.1/25}"
TARGET_USER="${TARGET_USER:-netops}"
TARGET_GROUP="${TARGET_GROUP:-netops}"

# 需要 root 权限安装 Docker 和写 /app
if [[ $(id -u) -ne 0 ]]; then
  echo "请使用 root 运行此脚本，例如: sudo $0"
  exit 1
fi

echo "========== 1. 安装 Docker =========="
if command -v docker &>/dev/null; then
  echo "Docker 已安装: $(docker --version)"
else
  echo "正在安装 Docker..."
  if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME:-$UBUNTU_CODENAME}") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  elif command -v yum &>/dev/null || command -v dnf &>/dev/null; then
    (command -v dnf &>/dev/null && dnf install -y dnf-plugins-core) || yum install -y yum-utils
    (command -v dnf &>/dev/null && dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo) || yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    (command -v dnf &>/dev/null && dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin) || yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  else
    echo "未检测到 apt-get 或 yum/dnf，请先手动安装 Docker。"
    exit 1
  fi
  systemctl enable docker
  systemctl start docker
  echo "Docker 安装完成."
fi

echo ""
echo "========== 2. 配置 Docker 桥接子网 (${DOCKER_BIP}) =========="
DAEMON_JSON="/etc/docker/daemon.json"
mkdir -p "$(dirname "$DAEMON_JSON")"
if [[ -f "$DAEMON_JSON" ]]; then
  if grep -q '"bip"' "$DAEMON_JSON" 2>/dev/null; then
    echo "daemon.json 中已存在 bip 配置，跳过修改。"
  else
    if command -v jq &>/dev/null; then
      tmp=$(mktemp)
      jq --arg bip "$DOCKER_BIP" '. + {"bip": $bip}' "$DAEMON_JSON" > "$tmp" && mv "$tmp" "$DAEMON_JSON"
    elif command -v python3 &>/dev/null; then
      tmp=$(mktemp)
      python3 -c "
import json, sys
p = '$DAEMON_JSON'
with open(p) as f: d = json.load(f)
d['bip'] = '$DOCKER_BIP'
with open('$tmp', 'w') as f: json.dump(d, f, indent=2)
" && mv "$tmp" "$DAEMON_JSON"
    else
      cp -a "$DAEMON_JSON" "${DAEMON_JSON}.bak"
      echo "{\"bip\": \"${DOCKER_BIP}\"}" > "$DAEMON_JSON"
      echo "已备份原配置到 ${DAEMON_JSON}.bak，并写入新 bip。若需保留其它项请手动合并。"
    fi
  fi
else
  echo "{\"bip\": \"${DOCKER_BIP}\"}" > "$DAEMON_JSON"
fi
echo "当前 $DAEMON_JSON 内容:"
cat "$DAEMON_JSON"
echo ""
systemctl restart docker
echo "Docker 已重启，桥接子网为 ${DOCKER_BIP}。"

echo ""
echo "========== 3. 克隆 Strix 到 ${STRIX_DIR} =========="
mkdir -p "$(dirname "$STRIX_DIR")"
if [[ -d "$STRIX_DIR/.git" ]]; then
  echo "目录已存在，执行 git pull..."
  (cd "$STRIX_DIR" && git fetch origin && git checkout "${STRIX_BRANCH}" && git pull --rebase origin "${STRIX_BRANCH}")
else
  echo "正在克隆 ${STRIX_REPO} ..."
  git clone --branch "${STRIX_BRANCH}" --depth 1 "${STRIX_REPO}" "$STRIX_DIR"
fi

echo ""
echo "========== 4. 设置 netops 对 Strix 目录的权限 =========="
if getent group "$TARGET_GROUP" &>/dev/null; then
  _group="$TARGET_GROUP"
else
  _group=""
fi
if getent passwd "$TARGET_USER" &>/dev/null; then
  chown -R "${TARGET_USER}:${_group:-$TARGET_USER}" "$STRIX_DIR"
  chmod -R u+rwX,go=rX "$STRIX_DIR"
  echo "已将 ${STRIX_DIR} 的所有者设为 ${TARGET_USER}:${_group:-$TARGET_USER}，权限已设置。"
else
  echo "警告: 系统用户 ${TARGET_USER} 不存在，已跳过 chown。请手动执行:"
  echo "  sudo chown -R netops:netops ${STRIX_DIR}"
  echo "  sudo chmod -R u+rwX,go=rX ${STRIX_DIR}"
fi

echo ""
echo "========== 安装完成 =========="
echo "Strix 代码路径: ${STRIX_DIR}"
echo "Docker 桥接子网: ${DOCKER_BIP}"
echo "如需使用 Strix CLI，请参考官方文档配置 LLM 并在此目录或项目中运行。"
echo "  cd ${STRIX_DIR} && cat README.md"
