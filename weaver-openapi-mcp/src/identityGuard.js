const IDENTITY_KEYS = new Set([
  'userid',
  'user_id',
  'useridlist',
  'userid_list',
  'account',
  'loginid',
  'loginname',
  'jobnum',
  'job_num',
  'jobnumlist',
  'job_num_list',
  'employeeid',
  'employee_id',
  'email',
  'mobile',
]);

const AUTH_KEYS = new Set([
  'access_token',
  'acess_token',
  'eteams_token',
  'refresh_token',
  'app_secret',
  'client_secret',
]);

function scalar(value) {
  return value !== undefined && value !== null && value !== '';
}

function allowedIdentityValues(session) {
  const values = [
    session.userid,
    session.employeeId,
    session.email,
    session.mobile,
    session.jobNum,
    session.account,
  ];
  return new Set(values.filter(scalar).map((value) => String(value).toLowerCase()));
}

function identityValueForParam(session, param) {
  const key = String(param).toLowerCase();
  if (key === 'account' || key === 'loginid' || key === 'loginname') {
    return session.account || session.email || session.mobile || '';
  }
  if (key === 'email') return session.email || '';
  if (key === 'mobile') return session.mobile || '';
  if (key === 'jobnum' || key === 'job_num') return session.jobNum || '';
  return session.userid || '';
}

export function findIdentityConflict(value, session) {
  const allowed = allowedIdentityValues(session);
  const walk = (node, path) => {
    if (node === null || typeof node !== 'object') return null;
    if (Array.isArray(node)) {
      for (let i = 0; i < node.length; i += 1) {
        const found = walk(node[i], `${path}[${i}]`);
        if (found) return found;
      }
      return null;
    }
    for (const [key, item] of Object.entries(node)) {
      if (IDENTITY_KEYS.has(key.toLowerCase())) {
        if (Array.isArray(item)) {
          for (let i = 0; i < item.length; i += 1) {
            const value = item[i];
            if (scalar(value) && !allowed.has(String(value).toLowerCase())) {
              return `${path}.${key}[${i}]`;
            }
          }
        } else if (scalar(item) && !allowed.has(String(item).toLowerCase())) {
          return `${path}.${key}`;
        }
      }
      const found = walk(item, path ? `${path}.${key}` : key);
      if (found) return found;
    }
    return null;
  };
  return walk(value, '');
}

function findKeyConflict(value, keys, label) {
  const walk = (node, path) => {
    if (node === null || typeof node !== 'object') return null;
    if (Array.isArray(node)) {
      for (let i = 0; i < node.length; i += 1) {
        const found = walk(node[i], `${path}[${i}]`);
        if (found) return found;
      }
      return null;
    }
    for (const [key, item] of Object.entries(node)) {
      if (keys.has(key.toLowerCase())) {
        return `${path}.${key}`;
      }
      const found = walk(item, path ? `${path}.${key}` : key);
      if (found) return found;
    }
    return null;
  };
  const found = walk(value, '');
  return found ? `${label} ${found}` : null;
}

export function findAuthConflict(value) {
  return findKeyConflict(value, AUTH_KEYS, '拒绝调用：参数');
}

export function injectIdentity(query, body, session, { param = 'userid', enabled = true } = {}) {
  const hasInQuery = Object.keys(query).some((key) => IDENTITY_KEYS.has(key.toLowerCase()));
  const hasInBody = body !== undefined && body !== null && typeof body === 'object' &&
    !Array.isArray(body) && Object.keys(body).some((key) => IDENTITY_KEYS.has(key.toLowerCase()));
  if (!enabled || hasInQuery || hasInBody) return;
  const value = identityValueForParam(session, param);
  if (!value) return;
  query[param] = value;
}
