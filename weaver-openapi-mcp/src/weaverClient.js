import { config } from './config.js';
import { loadTokens, saveTokens } from './tokenStore.js';
import { requireActiveSession } from './sessionStore.js';
import { findIdentityConflict, injectIdentity } from './identityGuard.js';

function buildUrl(pathname, params = {}) {
  const url = new URL(config.apiBase + pathname);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }
  return url;
}

async function parseJsonResponse(res) {
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}: ${text.slice(0, 500)}`);
  }
  const errcode = data?.errcode ?? data?.message?.errcode;
  if (errcode !== undefined && errcode !== '0' && errcode !== 0) {
    throw new Error(`API error ${errcode}: ${data?.errmsg || data?.message?.errmsg || 'unknown'}`);
  }
  return data;
}

async function apiRequest({ pathname, method = 'GET', query = {}, body, token }) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const params = { ...query };
  if (token) params.access_token = token;
  const res = await fetch(buildUrl(pathname, params), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return parseJsonResponse(res);
}

function saveTokenResponse(data) {
  const accessToken = data.accessToken || data.acessToken;
  const expiresIn = Number(data.expires_in || 7200);
  return saveTokens({
    accessToken,
    refreshToken: data.refreshToken || undefined,
    expiresAt: accessToken ? new Date(Date.now() + expiresIn * 1000).toISOString() : undefined,
  });
}

export async function getAccessToken(code) {
  const body = {
    app_key: config.appKey,
    app_secret: config.appSecret,
    grant_type: 'authorization_code',
    code,
  };
  const data = await apiRequest({ pathname: '/oauth2/access_token', method: 'POST', body });
  saveTokenResponse(data);
  return data;
}

export async function refreshAccessToken(refreshToken) {
  const stored = loadTokens();
  const token = refreshToken || stored?.refreshToken;
  if (!token) throw new Error('缺少 refresh_token，请先调用 weaver_get_access_token');
  const body = {
    app_key: config.appKey,
    app_secret: config.appSecret,
    grant_type: 'refresh_token',
    refresh_token: token,
  };
  const data = await apiRequest({ pathname: '/oauth2/refresh_token', method: 'POST', body });
  saveTokenResponse(data);
  return data;
}

export async function getUserInfoByEteamsToken(eteamsToken) {
  const data = await apiRequest({
    pathname: '/oauth2/getUserInfo',
    method: 'POST',
    query: { eteams_token: eteamsToken },
  });
  if (!data.acessToken) throw new Error('getUserInfo 未返回 acessToken，浏览器登录链路不完整');
  return data;
}

export async function resolveWeaverUser({ acessToken, email, mobile, jobNum }) {
  const body = { access_token: acessToken };
  if (jobNum) body.jobNumList = [String(jobNum)];
  if (!jobNum && email) body.account = email;
  if (!jobNum && !email && mobile) body.account = mobile;
  if (!body.jobNumList && !body.account) throw new Error('getUserInfo 未返回可用于解析 userid 的工号/邮箱/手机号');

  const data = await apiRequest({
    pathname: '/api/hrm/restful/queryEmployee',
    method: 'POST',
    body,
    token: acessToken,
  });
  const rows = data?.data?.data || [];
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('未能在通讯录中找到当前登录用户');

  const match = rows.find((row) => {
    if (jobNum && String(row.job_num) !== String(jobNum)) return false;
    if (!jobNum && email && String(row.email).toLowerCase() !== String(email).toLowerCase()) return false;
    if (!jobNum && !email && mobile && String(row.mobile) !== String(mobile)) return false;
    return true;
  }) || rows[0];

  return {
    userid: String(match.user_id ?? match.userid ?? ''),
    employeeId: String(match.id ?? ''),
    username: match.username || '',
    email: match.email || email || '',
    mobile: match.mobile || mobile || '',
    jobNum: match.job_num || jobNum || '',
    account: match.account || '',
  };
}

export async function callApi({ pathname, method = 'GET', query = {}, body, hostUserKey = config.hostUserKey }) {
  const session = requireActiveSession(hostUserKey);
  const queryCopy = { ...query };
  const bodyCopy = body === undefined ? undefined : structuredClone(body);

  const queryConflict = findIdentityConflict(queryCopy, session);
  if (queryConflict) throw new Error(`拒绝调用：query 参数 ${queryConflict} 不是当前登录用户的身份，禁止使用其他用户权限`);
  const bodyConflict = findIdentityConflict(bodyCopy, session);
  if (bodyConflict) throw new Error(`拒绝调用：body 参数 ${bodyConflict} 不是当前登录用户的身份，禁止使用其他用户权限`);

  injectIdentity(queryCopy, bodyCopy, session, {
    param: config.identityParam,
    enabled: config.autoInjectIdentity,
  });

  if (!queryCopy.access_token && !(bodyCopy && bodyCopy.access_token)) {
    queryCopy.access_token = session.acessToken;
  }
  return apiRequest({ pathname, method, query: queryCopy, body: bodyCopy });
}
