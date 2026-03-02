#!/usr/bin/env bash
# 为前端开发环境生成长期有效的自签名证书（默认 10 年），供 REACT_APP_DEV_HTTPS=true 使用
# 使用：bash scripts/gen-dev-https-cert.sh  或从项目根目录执行
set -e

CERT_DAYS="${CERT_DAYS:-3650}"
CERT_DIR="$(cd "$(dirname "$0")/.." && pwd)/netops-frontend/.cert"
KEY_FILE="${CERT_DIR}/key.pem"
CERT_FILE="${CERT_DIR}/cert.pem"

mkdir -p "$CERT_DIR"
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "$KEY_FILE" -out "$CERT_FILE" \
  -subj "/CN=localhost" \
  -days "$CERT_DAYS"
echo "已生成自签名证书（有效期 ${CERT_DAYS} 天）："
echo "  私钥: $KEY_FILE"
echo "  证书: $CERT_FILE"
echo "前端开发 HTTPS 将自动使用上述路径（REACT_APP_DEV_HTTPS=true）。"
