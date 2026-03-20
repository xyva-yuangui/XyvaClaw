#!/usr/bin/env node
/**
 * xyvaClaw Gateway Proxy
 *
 * Sits in front of OpenClaw Gateway (:18790 internal) on :18789 (public).
 * When models.providers is empty (no API key configured), intercepts the
 * root page request and shows a friendly onboarding guide instead of the
 * blank OpenClaw Dashboard.
 *
 * All other requests (API, WebSocket, assets) are transparently proxied.
 */

import http from 'http';
import fs from 'fs';
import { join } from 'path';

const XYVACLAW_HOME = process.env.OPENCLAW_HOME || process.env.XYVACLAW_HOME || join(process.env.HOME, '.xyvaclaw');
const PUBLIC_PORT = parseInt(process.env.GATEWAY_PORT || '18789', 10);
const INTERNAL_PORT = PUBLIC_PORT + 1; // OpenClaw Gateway runs on PUBLIC_PORT + 1
const CONFIG_PATH = join(XYVACLAW_HOME, '.openclaw', 'openclaw.json');

/**
 * Check if any model provider has an API key configured
 */
function hasProviders() {
  try {
    if (!fs.existsSync(CONFIG_PATH)) return false;
    const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    const providers = config?.models?.providers || {};
    return Object.keys(providers).length > 0;
  } catch {
    return false;
  }
}

/**
 * The onboarding HTML page shown when no providers are configured
 */
function getOnboardingHTML() {
  const assistantName = getAssistantName();
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>xyvaClaw - ${assistantName}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
      color: #333;
    }
    .container {
      background: white;
      border-radius: 24px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.08);
      padding: 48px;
      max-width: 600px;
      width: 90%;
      text-align: center;
    }
    .logo { font-size: 48px; margin-bottom: 16px; }
    h1 {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
      color: #1a1a1a;
    }
    h1 span { color: #6366f1; }
    .subtitle {
      color: #666;
      font-size: 16px;
      margin-bottom: 32px;
    }
    .status-card {
      background: #fef3c7;
      border: 1px solid #fbbf24;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
      text-align: left;
    }
    .status-card .icon { font-size: 20px; margin-right: 8px; }
    .status-card .title {
      font-weight: 600;
      color: #92400e;
      font-size: 15px;
    }
    .status-card .desc {
      color: #a16207;
      font-size: 14px;
      margin-top: 8px;
      line-height: 1.6;
    }
    .actions {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-top: 24px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 14px 28px;
      border-radius: 12px;
      font-size: 16px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s;
      cursor: pointer;
      border: none;
    }
    .btn-primary {
      background: #6366f1;
      color: white;
    }
    .btn-primary:hover {
      background: #4f46e5;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    .btn-secondary {
      background: #f3f4f6;
      color: #374151;
    }
    .btn-secondary:hover {
      background: #e5e7eb;
    }
    .help {
      margin-top: 32px;
      padding-top: 24px;
      border-top: 1px solid #e5e7eb;
    }
    .help-title {
      font-weight: 600;
      font-size: 14px;
      color: #6b7280;
      margin-bottom: 12px;
    }
    .help-links {
      display: flex;
      justify-content: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    .help-links a {
      color: #6366f1;
      text-decoration: none;
      font-size: 13px;
    }
    .help-links a:hover { text-decoration: underline; }
    code {
      background: #f3f4f6;
      padding: 2px 8px;
      border-radius: 6px;
      font-family: 'SF Mono', Monaco, monospace;
      font-size: 13px;
      color: #6366f1;
    }
    .cmd-box {
      background: #1e1e2e;
      border-radius: 12px;
      padding: 16px 20px;
      text-align: left;
      margin-top: 16px;
    }
    .cmd-box code {
      background: none;
      color: #a6e3a1;
      font-size: 14px;
      padding: 0;
    }
    .cmd-box .comment { color: #6c7086; }
    .refresh-hint {
      margin-top: 16px;
      font-size: 13px;
      color: #9ca3af;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">🐾</div>
    <h1><span>xyva</span>Claw</h1>
    <p class="subtitle">${assistantName} 正在等待配置</p>

    <div class="status-card">
      <div><span class="icon">⚠️</span><span class="title">AI 模型未配置</span></div>
      <div class="desc">
        你还没有配置 API Key，助手无法对话。<br>
        请通过下方按钮打开配置向导，完成 API Key 和其他设置。
      </div>
    </div>

    <div class="actions">
      <a class="btn btn-primary" href="http://localhost:19090" onclick="startWizard()">
        🚀 打开配置向导
      </a>
      <a class="btn btn-secondary" href="https://github.com/xyva-yuangui/XyvaClaw" target="_blank">
        📖 查看文档
      </a>
    </div>

    <div class="cmd-box">
      <code><span class="comment"># 或者在终端运行:</span></code><br>
      <code>xyvaclaw setup</code>
    </div>

    <p class="refresh-hint">配置完成后，刷新此页面即可开始对话</p>

    <div class="help">
      <div class="help-title">获取 API Key</div>
      <div class="help-links">
        <a href="https://bailian.console.aliyun.com" target="_blank">百炼 (推荐)</a>
        <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek</a>
        <a href="https://volcengine.com/product/doubao" target="_blank">火山引擎</a>
      </div>
    </div>
  </div>

  <script>
    function startWizard() {
      // Try to start wizard via API (in case it's not running)
      fetch('http://localhost:19090/').catch(() => {
        alert('配置向导未运行。请在终端运行: xyvaclaw setup');
      });
    }

    // Auto-refresh: check if providers are configured every 5 seconds
    setInterval(async () => {
      try {
        const res = await fetch('/api/proxy-status');
        const data = await res.json();
        if (data.hasProviders) {
          window.location.reload();
        }
      } catch {}
    }, 5000);
  </script>
</body>
</html>`;
}

function getAssistantName() {
  try {
    const envPath = join(XYVACLAW_HOME, '.env');
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, 'utf-8');
      const match = content.match(/^ASSISTANT_NAME=(.+)$/m);
      if (match) return match[1].trim();
    }
  } catch {}
  return 'AI Assistant';
}

/**
 * Proxy a request to the internal OpenClaw Gateway
 */
function proxyRequest(clientReq, clientRes) {
  const options = {
    hostname: '127.0.0.1',
    port: INTERNAL_PORT,
    path: clientReq.url,
    method: clientReq.method,
    headers: { ...clientReq.headers, host: `127.0.0.1:${INTERNAL_PORT}` },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(clientRes, { end: true });
  });

  proxyReq.on('error', (err) => {
    // Gateway not ready yet — show a simple waiting page
    clientRes.writeHead(502, { 'Content-Type': 'text/html; charset=utf-8' });
    clientRes.end(`
      <html><body style="font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh">
        <div style="text-align:center">
          <h2>⏳ Gateway 启动中...</h2>
          <p>请稍候，页面将自动刷新</p>
          <script>setTimeout(()=>location.reload(), 3000)</script>
        </div>
      </body></html>
    `);
  });

  clientReq.pipe(proxyReq, { end: true });
}

// Create the proxy server
const server = http.createServer((req, res) => {
  // Status endpoint for the onboarding page's auto-refresh
  if (req.url === '/api/proxy-status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ hasProviders: hasProviders() }));
    return;
  }

  // Check if this is a browser request for the root page
  const isRootPage = req.url === '/' && req.method === 'GET' &&
    (req.headers.accept || '').includes('text/html');

  if (isRootPage && !hasProviders()) {
    // Show onboarding page
    const html = getOnboardingHTML();
    res.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
    });
    res.end(html);
    return;
  }

  // Proxy everything else to OpenClaw Gateway
  proxyRequest(req, res);
});

// Handle WebSocket upgrade (for OpenClaw's real-time features)
server.on('upgrade', (req, socket, head) => {
  const options = {
    hostname: '127.0.0.1',
    port: INTERNAL_PORT,
    path: req.url,
    method: 'GET',
    headers: { ...req.headers, host: `127.0.0.1:${INTERNAL_PORT}` },
  };

  const proxyReq = http.request(options);
  proxyReq.on('upgrade', (proxyRes, proxySocket, proxyHead) => {
    socket.write(
      `HTTP/1.1 101 Switching Protocols\r\n` +
      Object.entries(proxyRes.headers).map(([k, v]) => `${k}: ${v}`).join('\r\n') +
      '\r\n\r\n'
    );
    if (proxyHead.length > 0) socket.write(proxyHead);
    proxySocket.pipe(socket);
    socket.pipe(proxySocket);
  });

  proxyReq.on('error', () => {
    socket.destroy();
  });

  proxyReq.end();
});

server.listen(PUBLIC_PORT, '127.0.0.1', () => {
  console.log(`[xyvaClaw proxy] Listening on http://127.0.0.1:${PUBLIC_PORT}`);
  console.log(`[xyvaClaw proxy] Proxying to OpenClaw Gateway on :${INTERNAL_PORT}`);
  console.log(`[xyvaClaw proxy] Providers configured: ${hasProviders()}`);
});
