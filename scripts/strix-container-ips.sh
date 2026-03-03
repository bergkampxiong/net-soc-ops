#!/usr/bin/env bash
# 列出当前运行的 Strix 沙箱容器名称与 IP，便于在目标机或本机按源 IP 抓包。
# 使用：bash scripts/strix-container-ips.sh
set -e

echo "Strix 沙箱容器 => IP"
echo "=============================================="

if ! command -v docker &>/dev/null; then
  echo "未检测到 docker 命令"
  exit 1
fi

names=$(docker ps --filter "name=strix-scan" --format "{{.Names}}" 2>/dev/null)
if [[ -z "$names" ]]; then
  echo "当前无运行中的 strix-scan 容器"
  exit 0
fi

while IFS= read -r name; do
  [[ -z "$name" ]] && continue
  ip=$(docker inspect "$name" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)
  echo "$name => ${ip:-（无法获取）}"
done <<< "$names"

echo "=============================================="
echo "本机抓包示例: tcpdump -i any -n 'net 192.168.0.0/25 and tcp port 8080'"
echo "按容器 IP 抓包: 将上面列出的 IP 代入 tcpdump -i any -n host <IP>"
