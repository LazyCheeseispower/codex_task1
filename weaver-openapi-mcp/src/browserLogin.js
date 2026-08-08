import http from 'node:http';
import crypto from 'node:crypto';
import { execFile } from 'node:child_process';
import { config } from './config.js';

function openBrowser(url) {
  if (process.platform === 'win32') {
    return new Promise((resolve, reject) => {
      execFile('explorer', [url], { windowsHide: true }, (error) => {
        if (error) reject(new Error(`无法打开默认浏览器：${error.message}`));
        else resolve();
      });
    });
  }
  const command = process.platform === 'darwin' ? 'open' : 'xdg-open';
  const args = [url];
  return new Promise((resolve, reject) => {
    execFile(command, args, { windowsHide: true }, (error) => {
      if (error) reject(new Error(`无法打开默认浏览器：${error.message}`));
      else resolve();
    });
  });
}

function successHtml() {
  return `<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>泛微登录成功</title>
<style>body{font-family:system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0;background:#f5f7fa;color:#1f2937}main{background:#fff;padding:32px 40px;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.08);text-align:center}h1{font-size:20px;margin:0 0 8px}p{color:#6b7280;margin:0}</style>
<body><main><h1>登录成功</h1><p>泛微账号已返回给 MCP，现在可以关闭此页面。</p></main></body>
</html>`;
}

function errorHtml(message) {
  return `<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>泛微登录失败</title>
<style>body{font-family:system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0;background:#f5f7fa;color:#1f2937}main{background:#fff;padding:32px 40px;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.08);text-align:center}h1{font-size:20px;margin:0 0 8px}p{color:#b91c1c;margin:0}</style>
<body><main><h1>登录失败</h1><p>${message}</p></main></body>
</html>`;
}

export async function startBrowserLogin({ timeoutMs = config.loginTimeoutMs, open = openBrowser } = {}) {
  if (!config.appKey) throw new Error('未配置 WEAVER_APP_KEY，无法发起浏览器登录');

  const nonce = crypto.randomBytes(12).toString('hex');
  const callbackPath = `/callback/${nonce}`;
  const server = http.createServer();

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, config.callbackHost, resolve);
  });

  const address = server.address();
  const port = typeof address === 'object' && address ? address.port : 0;
  const callbackUrl = `http://127.0.0.1:${port}${callbackPath}`;
  const params = new URLSearchParams({ app_key: config.appKey, redirect_uri: callbackUrl });
  const authUrl = `${config.origin}/api/bs/open/auth/third?${params.toString()}`;

  let settled = false;
  let timer;
  const callbackPromise = new Promise((resolve, reject) => {
    timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      server.close();
      reject(new Error(`登录超时，请在 ${Math.max(1, Math.round(timeoutMs / 60000))} 分钟内完成浏览器登录`));
    }, timeoutMs);

    server.on('request', (req, res) => {
      if (settled) return;
      let url;
      try {
        url = new URL(req.url, `http://${config.callbackHost}:${port}`);
      } catch {
        res.writeHead(400);
        res.end();
        return;
      }
      if (url.pathname !== callbackPath) {
        res.writeHead(404);
        res.end('Not Found');
        return;
      }
      settled = true;
      clearTimeout(timer);
      const eteamsToken = url.searchParams.get('eteams_token');
      const message = url.searchParams.get('error') || url.searchParams.get('errmsg') || '';
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(eteamsToken ? successHtml() : errorHtml(message || '回调地址缺少 eteams_token'));
      server.close();
      if (eteamsToken) resolve({ eteamsToken, callbackUrl, authUrl });
      else reject(new Error(message || '回调地址缺少 eteams_token'));
    });
  });

  try {
    await open(authUrl);
    return await callbackPromise;
  } catch (error) {
    if (!settled) {
      settled = true;
      clearTimeout(timer);
      server.close();
    }
    throw error;
  }
}
