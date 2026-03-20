const path = require('path');
const fs = require('fs');

// 开发环境是否启用 HTTPS；证书优先使用长期有效的自签名（见 scripts/gen-dev-https-cert.sh）
const devHttps = process.env.REACT_APP_DEV_HTTPS === 'true';
const certDir = path.resolve(__dirname, '.cert');
const keyPath = path.join(certDir, 'key.pem');
const certPath = path.join(certDir, 'cert.pem');
const hasCert = devHttps && fs.existsSync(keyPath) && fs.existsSync(certPath);

// /api 代理配置（v4 对象格式与 v5 数组格式共用）
const apiProxyConfig = {
  target: process.env.REACT_APP_API_PROXY_TARGET || 'http://127.0.0.1:8000',
  changeOrigin: true,
  onProxyReq: (proxyReq, req) => {
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
};

module.exports = {
  eslint: {
    enable: true,
    pluginOptions: {
      cache: false,
    },
  },
  webpack: {
    configure: (webpackConfig) => {
      // 忽略 node_modules 中第三方包的 source map 解析失败（如 @antv/util）
      const sourceMapRule = webpackConfig.module.rules.find(
        (r) => r.enforce === 'pre' && r.loader?.includes?.('source-map-loader')
      );
      if (sourceMapRule && sourceMapRule.exclude) {
        sourceMapRule.exclude = /node_modules/;
      } else if (sourceMapRule) {
        sourceMapRule.exclude = /node_modules/;
      }
      return webpackConfig;
    },
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@services': path.resolve(__dirname, 'src/services'),
      '@components': path.resolve(__dirname, 'src/components'),
      '@pages': path.resolve(__dirname, 'src/pages'),
      '@utils': path.resolve(__dirname, 'src/utils'),
    },
  },
  devServer: (devServerConfig, { env, paths, proxy, allowedHost }) => {
    // 检测 webpack-dev-server 5：v5 要求 proxy 为数组，且不支持 onAfterSetupMiddleware
    let isWds5 = false;
    try {
      const wdsVersion = require('webpack-dev-server/package.json').version;
      isWds5 = parseInt(wdsVersion.split('.')[0], 10) >= 5;
    } catch (_) {}
    if (isWds5) {
      // webpack-dev-server 5.x：转换配置以兼容新 API
      const evalSourceMapMiddleware = require('react-dev-utils/evalSourceMapMiddleware');
      const noopServiceWorkerMiddleware = require('react-dev-utils/noopServiceWorkerMiddleware');
      const redirectServedPath = require('react-dev-utils/redirectServedPathMiddleware');

      delete devServerConfig.onBeforeSetupMiddleware;
      delete devServerConfig.onAfterSetupMiddleware;
      devServerConfig.setupMiddlewares = (middlewares, devServer) => {
        const rsPaths = require('react-scripts/config/paths');
        devServer.app.use(evalSourceMapMiddleware(devServer));
        if (fs.existsSync(rsPaths.proxySetup)) {
          require(rsPaths.proxySetup)(devServer.app);
        }
        middlewares.push({
          name: 'redirect-served-path',
          path: '/',
          middleware: redirectServedPath(rsPaths.publicUrlOrPath),
        });
        middlewares.push({
          name: 'noop-service-worker',
          path: '/',
          middleware: noopServiceWorkerMiddleware(rsPaths.publicUrlOrPath),
        });
        return middlewares;
      };
      devServerConfig.proxy = [
        { context: ['/api'], ...apiProxyConfig },
      ];
      if (devServerConfig.https) {
        const httpsOpt = devServerConfig.https;
        delete devServerConfig.https;
        devServerConfig.server = typeof httpsOpt === 'object' && httpsOpt.key
          ? { type: 'https', options: httpsOpt }
          : 'https';
      }
    } else {
      devServerConfig.proxy = { '/api': apiProxyConfig };
    }

    Object.assign(devServerConfig, {
      port: 8080,
      ...(devHttps ? (hasCert ? { https: { key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) } } : { https: true }) : {}),
    });

    if (isWds5 && devHttps) {
      delete devServerConfig.https;
      devServerConfig.server = hasCert
        ? { type: 'https', options: { key: fs.readFileSync(keyPath), cert: fs.readFileSync(certPath) } }
        : 'https';
    }

    return devServerConfig;
  },
}; 