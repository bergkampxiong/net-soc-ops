const http = require('http');
const httpProxy = require('http-proxy');

// 创建代理服务器
const proxy = httpProxy.createProxyServer({
  target: 'http://172.18.40.99:8000',
  changeOrigin: true,
  ws: true,  // 启用WebSocket支持
  secure: false
});

// 创建HTTP服务器
const server = http.createServer((req, res) => {
  // 添加CORS响应头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
  
  // 处理OPTIONS请求
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // 记录请求信息
  console.log('收到请求:', {
    url: req.url,
    method: req.method,
    headers: req.headers
  });

  // 处理代理请求
  proxy.web(req, res, {}, (err) => {
    console.error('代理错误:', err);
    res.writeHead(500, {
      'Content-Type': 'text/plain'
    });
    res.end('代理错误: ' + err.message);
  });
});

// 监听代理事件
proxy.on('proxyReq', (proxyReq, req, res) => {
  // 确保请求路径包含/api前缀
  if (!req.url.startsWith('/api/')) {
    req.url = `/api${req.url}`;
  }
  
  // 获取客户端真实IP
  let clientIp = req.headers['x-real-ip'] || 
                 req.headers['x-forwarded-for']?.split(',')[0] || 
                 req.connection.remoteAddress || 
                 req.socket.remoteAddress;
  
  // 如果是IPv6格式的本地地址，转换为IPv4
  if (clientIp === '::1' || clientIp === '::ffff:127.0.0.1') {
    clientIp = '127.0.0.1';
  }
  
  // 添加X-Forwarded-For和X-Real-IP头
  proxyReq.setHeader('X-Forwarded-For', clientIp);
  proxyReq.setHeader('X-Real-IP', clientIp);
  
  const targetUrl = `http://172.18.40.99:8000${req.url}`;
  console.log('转发请求:', {
    originalUrl: req.url,
    targetUrl: targetUrl,
    method: req.method,
    clientIp: clientIp,
    headers: req.headers
  });
});

// 处理WebSocket连接
server.on('upgrade', (req, socket, head) => {
  console.log('WebSocket连接请求:', {
    url: req.url,
    headers: req.headers
  });

  proxy.ws(req, socket, head, (err) => {
    if (err) {
      console.error('WebSocket代理错误:', err);
      socket.end();
    }
  });
});

// 处理代理响应
proxy.on('proxyRes', (proxyRes, req, res) => {
  // 添加CORS响应头到代理响应
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
  
  console.log('收到响应:', {
    statusCode: proxyRes.statusCode,
    path: req.url
  });
});

// 启动服务器
const PORT = 3000;
server.listen(PORT, () => {
  console.log(`代理服务器运行在 http://localhost:${PORT}`);
}); 