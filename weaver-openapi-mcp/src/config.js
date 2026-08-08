import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const envFile = path.join(projectRoot, '.env');
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue;
    const eq = trimmed.indexOf('=');
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (key && process.env[key] === undefined) process.env[key] = value;
  }
}

function originOf(apiBase) {
  try {
    return new URL(apiBase).origin;
  } catch {
    return apiBase;
  }
}

const defaultApiBase = 'https://zdyl.zhende.com:11112/papi/openapi';
const callbackHost = process.env.WEAVER_CALLBACK_HOST || '127.0.0.1';

export const config = {
  apiBase: (process.env.WEAVER_API_BASE || defaultApiBase).replace(/\/+$/, ''),
  origin: originOf(process.env.WEAVER_API_BASE || defaultApiBase),
  appKey: process.env.WEAVER_APP_KEY || '',
  appSecret: process.env.WEAVER_APP_SECRET || '',
  corpId: process.env.WEAVER_CORP_ID || '',
  hostUserKey: process.env.WEAVER_USER_KEY || process.env.WORKBUDDY_USER_ID || 'local',
  dataDir: process.env.WEAVER_DATA_DIR || path.join(projectRoot, 'data'),
  sessionsFile: process.env.WEAVER_SESSIONS_FILE || path.join(projectRoot, 'data', 'sessions.json'),
  bindingsFile: process.env.WEAVER_BINDINGS_FILE || path.join(projectRoot, 'data', 'bindings.json'),
  callbackHost,
  callbackPublicHost: process.env.WEAVER_CALLBACK_PUBLIC_HOST || (callbackHost === '0.0.0.0' ? '127.0.0.1' : callbackHost),
  callbackPort: Number(process.env.WEAVER_CALLBACK_PORT || 0),
  loginTimeoutMs: Number(process.env.WEAVER_LOGIN_TIMEOUT_MS || 300000),
  requireBinding: String(process.env.WEAVER_REQUIRE_BINDING || '').toLowerCase() === 'true',
  autoInjectIdentity: String(process.env.WEAVER_AUTO_INJECT_USERID || 'true').toLowerCase() !== 'false',
  identityParam: (process.env.WEAVER_IDENTITY_PARAM || 'userid').trim(),
  allowedApiPaths: (process.env.WEAVER_API_ALLOWED_PATHS || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean),
};
