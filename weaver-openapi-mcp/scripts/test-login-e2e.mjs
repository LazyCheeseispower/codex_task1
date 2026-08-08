import http from 'node:http';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'weaver-login-e2e-'));
const sessionsFile = path.join(tmpDir, 'sessions.json');

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
    });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

async function getFreePort() {
  const probe = http.createServer();
  await new Promise((resolve) => probe.listen(0, '127.0.0.1', resolve));
  const port = probe.address().port;
  await new Promise((resolve) => probe.close(resolve));
  return port;
}

const fakeE10 = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  if (url.pathname === '/api/bs/open/auth/third') {
    const target = new URL(url.searchParams.get('redirect_uri'));
    target.searchParams.set('eteams_token', 'test-eteams-token');
    res.writeHead(302, { Location: target.toString() });
    res.end();
    return;
  }
  if (url.pathname === '/papi/openapi/oauth2/getUserInfo') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      errcode: '0',
      errmsg: 'success',
      acessToken: 'fake-access-token',
      email: 'me@example.com',
      mobile: '',
      jobNum: 'J001',
    }));
    return;
  }
  if (url.pathname === '/papi/openapi/api/hrm/restful/queryEmployee') {
    let body = {};
    try {
      body = JSON.parse(await readBody(req));
    } catch {
      body = {};
    }
    assert.deepEqual(body.jobNumList, ['J001']);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      message: { errcode: '0', errmsg: 'success' },
      data: {
        current: 1,
        total: 1,
        data: [{
          id: 'emp-1',
          user_id: 'user-1',
          username: '测试用户',
          email: 'me@example.com',
          mobile: '',
          job_num: 'J001',
          account: 'me@example.com',
        }],
      },
    }));
    return;
  }
  res.writeHead(404);
  res.end();
});

await new Promise((resolve) => fakeE10.listen(0, '127.0.0.1', resolve));
const fakePort = fakeE10.address().port;

process.env.WEAVER_API_BASE = `http://127.0.0.1:${fakePort}/papi/openapi`;
process.env.WEAVER_APP_KEY = 'test-app-key';
process.env.WEAVER_SESSIONS_FILE = sessionsFile;
process.env.WEAVER_CALLBACK_PORT = String(await getFreePort());

const { startBrowserLogin } = await import('../src/browserLogin.js');
const { getUserInfoByEteamsToken, resolveWeaverUser, callApi } = await import('../src/weaverClient.js');
const { saveSession, getSession } = await import('../src/sessionStore.js');

try {
  const login = await startBrowserLogin({
    timeoutMs: 5000,
    open: async (authUrl) => {
      await fetch(authUrl);
    },
  });

  const raw = await getUserInfoByEteamsToken(login.eteamsToken);
  assert.equal(raw.acessToken, 'fake-access-token');

  const identity = await resolveWeaverUser(raw);
  assert.equal(identity.userid, 'user-1');
  assert.equal(identity.jobNum, 'J001');

  saveSession({
    hostKey: 'local',
    ...identity,
    acessToken: raw.acessToken,
    expiresAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
  });

  const session = getSession();
  assert.equal(session.userid, 'user-1');
  assert.equal(session.email, 'me@example.com');

  await assert.rejects(
    () => callApi({ pathname: '/department/v2/list', query: { userid: 'someone-else' } }),
    /拒绝调用/,
  );

  console.log('browser login e2e test passed');
} finally {
  fakeE10.closeAllConnections?.();
  fakeE10.close();
}
