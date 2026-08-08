import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'weaver-mcp-test-'));
fs.writeFileSync(path.join(tmpDir, 'sessions.json'), JSON.stringify({
  local: {
    hostKey: 'local',
    userid: 'fake-user',
    employeeId: 'fake-employee',
    username: '测试用户',
    email: 'me@example.com',
    mobile: '',
    jobNum: 'J001',
    account: 'me@example.com',
    acessToken: 'fake-token',
    expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
  },
}));
process.env.WEAVER_SESSIONS_FILE = path.join(tmpDir, 'sessions.json');

const child = spawn(process.execPath, ['src/index.js'], {
  cwd: root,
  stdio: ['pipe', 'pipe', 'pipe'],
});

let buffer = '';
let nextId = 0;
const pending = new Map();

function send(method, params = {}) {
  const id = ++nextId;
  child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method, params })}\n`);
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

child.stdout.on('data', (chunk) => {
  buffer += chunk.toString('utf8');
  let newline;
  while ((newline = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, newline).trim();
    buffer = buffer.slice(newline + 1);
    if (!line) continue;
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      continue;
    }
    const entry = pending.get(message.id);
    if (!entry) continue;
    pending.delete(message.id);
    if (message.error) entry.reject(new Error(JSON.stringify(message.error)));
    else entry.resolve(message.result);
  }
});

child.stderr.on('data', () => {});
child.on('error', (error) => {
  for (const entry of pending.values()) entry.reject(error);
  pending.clear();
});

try {
  const init = await send('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'weaver-tools-test', version: '1.0.0' },
  });
  assert.equal(init.serverInfo.name, 'weaver-openapi-mcp');

  child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} })}\n`);

  const tools = await send('tools/list', {});
  const names = tools.tools.map((tool) => tool.name);
  for (const expected of ['weaver_login', 'weaver_whoami', 'weaver_logout', 'weaver_get_departments', 'weaver_api_request']) {
    assert.ok(names.includes(expected), `missing tool ${expected}`);
  }

  const whoami = await send('tools/call', { name: 'weaver_whoami', arguments: {} });
  const whoamiText = whoami.content[0].text;
  assert.ok(whoamiText.includes('"loggedIn": true'), `unexpected whoami: ${whoamiText}`);
  assert.ok(whoamiText.includes('"userid": "fake-user"'), `unexpected whoami: ${whoamiText}`);

  const blocked = await send('tools/call', {
    name: 'weaver_api_request',
    arguments: { path: '/department/v2/list', query: { userid: 'someone-else' } },
  });
  assert.ok(blocked.isError, 'api request with another userid should be rejected');
  assert.ok(blocked.content[0].text.includes('拒绝调用'), `unexpected error: ${blocked.content[0].text}`);

  const blockedTokenQuery = await send('tools/call', {
    name: 'weaver_api_request',
    arguments: { path: '/department/v2/list', query: { access_token: 'stolen-token' } },
  });
  assert.ok(blockedTokenQuery.isError, 'api request with caller-supplied access_token should be rejected');
  assert.ok(blockedTokenQuery.content[0].text.includes('不允许由调用方传入'), `unexpected error: ${blockedTokenQuery.content[0].text}`);

  const blockedTokenBody = await send('tools/call', {
    name: 'weaver_api_request',
    arguments: { path: '/department/v2/list', body: { eteams_token: 'stolen-token' } },
  });
  assert.ok(blockedTokenBody.isError, 'api request with caller-supplied eteams_token should be rejected');
  assert.ok(blockedTokenBody.content[0].text.includes('不允许由调用方传入'), `unexpected error: ${blockedTokenBody.content[0].text}`);

  console.log('mcp tool tests passed');
} finally {
  child.kill();
}
