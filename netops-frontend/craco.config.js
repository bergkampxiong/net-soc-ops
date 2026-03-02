const path = require('path');
const fs = require('fs');

// 开发环境是否启用 HTTPS；证书优先使用长期有效的自签名（见 scripts/gen-dev-https-cert.sh）
const devHttps = process.env.REACT_APP_DEV_HTTPS === 'true';
const certDir = path.resolve(__dirname, '.cert');
const keyPath = path.join(certDir, 'key.pem');
const certPath = path.join(certDir, 'cert.pem');
const hasCert = devHttps && fs.existsSync(keyPath) && fs.existsSync(certPath);

module.exports = {
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@services': path.resolve(__dirname, 'src/services'),
      '@components': path.resolve(__dirname, 'src/components'),
      '@pages': path.resolve(__dirname, 'src/pages'),
      '@utils': path.resolve(__dirname, 'src/utils'),
    },
  },
  devServer: {
    port: 8080,
    // 仅当 REACT_APP_DEV_HTTPS=true 时启用 HTTPS；有 .cert 则用长期有效证书，否则用 dev-server 默认自签名
    ...(devHttps ? (hasCert ? { https: { key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) } } : { https: true }) : {}),
  },
}; 