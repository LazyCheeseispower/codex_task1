import { fileURLToPath } from 'node:url';
import path from 'node:path';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function originOf(apiBase) {
  try {
    return new URL(apiBase).origin;
  } catch {
    return apiBase;
  }
}

const defaultApiBase = 'https://zdyl.zhende.com:11112/papi/openapi';

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
  callbackHost: process.env.WEAVER_CALLBACK_HOST || '127.0.0.1',
  loginTimeoutMs: Number(process.env.WEAVER_LOGIN_TIMEOUT_MS || 300000),
  requireBinding: String(process.env.WEAVER_REQUIRE_BINDING || '').toLowerCase() === 'true',
  autoInjectIdentity: String(process.env.WEAVER_AUTO_INJECT_USERID || 'true').toLowerCase() !== 'false',
  identityParam: (process.env.WEAVER_IDENTITY_PARAM || 'userid').trim(),
  allowedApiPaths: (process.env.WEAVER_API_ALLOWED_PATHS || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean),
};
