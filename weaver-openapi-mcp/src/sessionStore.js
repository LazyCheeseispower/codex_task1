import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf8');
}

export function loadSessions() {
  return readJson(config.sessionsFile, {});
}

export function getSession(hostKey = config.hostUserKey) {
  return loadSessions()[hostKey] || null;
}

export function saveSession(session) {
  const sessions = loadSessions();
  const merged = {
    ...session,
    hostKey: session.hostKey || config.hostUserKey,
    updatedAt: new Date().toISOString(),
  };
  sessions[merged.hostKey] = merged;
  writeJson(config.sessionsFile, sessions);
  return merged;
}

export function deleteSession(hostKey = config.hostUserKey) {
  const sessions = loadSessions();
  if (!sessions[hostKey]) return false;
  delete sessions[hostKey];
  writeJson(config.sessionsFile, sessions);
  return true;
}

export function requireActiveSession(hostKey = config.hostUserKey) {
  const session = getSession(hostKey);
  if (!session?.acessToken) {
    throw new Error(`宿主用户 ${hostKey} 尚未绑定泛微账号，请先调用 weaver_login 完成浏览器登录`);
  }
  if (session.expiresAt && new Date(session.expiresAt).getTime() <= Date.now()) {
    throw new Error(`宿主用户 ${hostKey} 的登录已过期，请重新调用 weaver_login`);
  }
  return session;
}

export function loadBindings() {
  return readJson(config.bindingsFile, {});
}

export function verifyBinding(hostKey, identity) {
  const binding = loadBindings()[hostKey];
  if (!binding) {
    if (config.requireBinding) {
      return { allowed: false, reason: `未在 bindings.json 中找到宿主用户 ${hostKey} 的预绑定关系` };
    }
    return { allowed: true, reason: 'first-login' };
  }
  const actual = [identity.userid, identity.email, identity.mobile, identity.jobNum, identity.account]
    .filter((value) => value !== undefined && value !== null && value !== '')
    .map((value) => String(value).toLowerCase());
  const expected = [binding.userid, binding.email, binding.mobile, binding.jobNum, binding.account]
    .filter((value) => value !== undefined && value !== null && value !== '')
    .map((value) => String(value).toLowerCase());
  if (expected.some((value) => actual.includes(value))) {
    return { allowed: true, reason: 'binding-matched' };
  }
  return { allowed: false, reason: `宿主用户 ${hostKey} 预绑定 ${expected.join(' / ') || '(空)'}，但当前登录的是 ${actual.join(' / ')}` };
}
