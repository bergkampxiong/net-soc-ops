const path = require('path');
const fs = require('fs');

// 开发环境是否启用 HTTPS；证书优先使用长期有效的自签名（见 scripts/gen-dev-https-cert.sh）
const devHttps = process.env.REACT_APP_DEV_HTTPS === 'true';
const certDir = path.resolve(__dirname, '.cert');
const keyPath = path.join(certDir, 'key.pem');
const certPath = path.join(certDir, 'cert.pem');
const hasCert = devHttps && fs.existsSync(keyPath) && fs.existsSync(certPath);

module.exports = {
  // 关闭 ESLint 文件缓存，避免 node_modules/.cache 为 root 属主时出现 EACCES
  eslint: {
    enable: true,
    pluginOptions: {
      cache: false,
    },
  },
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
    // 显式配置 /api 代理，避免 craco 覆盖 package.json 的 proxy（HTTPS 开发时尤其需要）
    proxy: {
      '/api': {
        target: process.env.REACT_APP_API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        onProxyReq: (proxyReq, req) => {
          // 优先保留上游（如 Nginx）已设置的真实 IP，否则用本代理看到的客户端地址
          const forwarded = req.headers['x-forwarded-for'];
          let clientIp = forwarded
            ? (typeof forwarded === 'string' ? forwarded.split(',')[0] : forwarded[0]).trim()
            : (req.socket?.remoteAddress || req.connection?.remoteAddress || '127.0.0.1');
          if (clientIp === '::1' || clientIp === '::ffff:127.0.0.1') {
            clientIp = '127.0.0.1';
          }
          proxyReq.setHeader('X-Forwarded-For', forwarded || clientIp);
          proxyReq.setHeader('X-Real-IP', clientIp);
        },
      },
    },
  },
}; 