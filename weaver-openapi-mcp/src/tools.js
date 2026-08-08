import { callApi, getUserInfoByEteamsToken, resolveWeaverUser } from './weaverClient.js';
import { startBrowserLogin } from './browserLogin.js';
import { config } from './config.js';
import { deleteSession, getSession, saveSession, verifyBinding } from './sessionStore.js';
import { z } from 'zod';

function textResult(data) {
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
}

export function registerTools(server) {
  server.registerTool(
    'weaver_login',
    {
      title: '浏览器登录泛微',
      description: '打开泛微 E10 登录页（复用默认浏览器登录态），登录成功后把当前宿主用户与泛微账号绑定，并把用户信息返回给 MCP。',
      inputSchema: {
        timeoutMs: z.number().int().positive().max(600000).optional().describe('等待浏览器回调的超时毫秒数，默认 300000'),
      },
    },
    async ({ timeoutMs }) => {
      const { eteamsToken, callbackUrl } = await startBrowserLogin({ timeoutMs });
      const raw = await getUserInfoByEteamsToken(eteamsToken);
      const identity = await resolveWeaverUser(raw);
      const check = verifyBinding(config.hostUserKey, identity);
      if (!check.allowed) throw new Error(`身份绑定校验失败：${check.reason}`);
      const session = saveSession({
        hostKey: config.hostUserKey,
        ...identity,
        acessToken: raw.acessToken,
        expiresAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        loggedInAt: new Date().toISOString(),
      });
      return textResult({
        loggedIn: true,
        hostKey: session.hostKey,
        userid: session.userid,
        employeeId: session.employeeId,
        username: session.username,
        email: session.email,
        mobile: session.mobile,
        jobNum: session.jobNum,
        tokenExpiresAt: session.expiresAt,
        callbackUrl,
      });
    },
  );

  server.registerTool(
    'weaver_whoami',
    {
      title: '查看当前登录身份',
      description: '返回当前宿主用户已绑定的泛微账号；未登录时返回 loggedIn=false。',
      inputSchema: {},
    },
    async () => {
      const session = getSession();
      if (!session?.acessToken) return textResult({ loggedIn: false, hostKey: config.hostUserKey });
      return textResult({
        loggedIn: true,
        hostKey: session.hostKey,
        userid: session.userid,
        employeeId: session.employeeId,
        username: session.username,
        email: session.email,
        mobile: session.mobile,
        jobNum: session.jobNum,
        tokenExpiresAt: session.expiresAt,
      });
    },
  );

  server.registerTool(
    'weaver_logout',
    {
      title: '退出泛微登录',
      description: '清除当前宿主用户在本地保存的泛微会话，后续业务工具需要重新调用 weaver_login。',
      inputSchema: {},
    },
    async () => textResult({ loggedIn: false, hostKey: config.hostUserKey, removed: deleteSession() }),
  );

  server.registerTool(
    'weaver_get_departments',
    {
      title: '查询部门列表',
      description: '调用部门列表接口 /department/v2/list。这是文档标注的老接口，建议后续优先使用组织查询接口。',
      inputSchema: {
        depid: z.string().optional().describe('部门 ID，不传时获取整个部门列表'),
        status: z.string().optional().describe('启用状态（默认 启用；0 禁用；all 查询全部）'),
        isDelete: z.string().optional().describe('是否删除（默认 未删除；1 删除；all 查询全部）'),
      },
    },
    async (args) => {
      const data = await callApi({
        pathname: '/department/v2/list',
        query: { depid: args.depid, status: args.status, isDelete: args.isDelete },
      });
      return textResult(data);
    },
  );

  server.registerTool(
    'weaver_api_request',
    {
      title: '调用任意开放接口',
      description: '通用请求工具，用于调用尚未封装成独立工具的泛微开放接口。路径必须是 / 开头的接口路径，自动带当前登录用户的访问令牌与身份参数，并拒绝其他用户身份。',
      inputSchema: {
        path: z.string().describe('接口路径，例如 /department/v2/list'),
        method: z.enum(['GET', 'POST', 'PUT', 'DELETE']).optional().describe('请求方法，默认 GET'),
        query: z.record(z.string(), z.unknown()).optional().describe('查询参数（键值对）'),
        body: z.record(z.string(), z.unknown()).optional().describe('JSON 请求体（POST/PUT 时使用）'),
      },
    },
    async (args) => {
      if (!/^\/[A-Za-z0-9_./-]+$/.test(args.path)) throw new Error('非法接口路径');
      if (config.allowedApiPaths.length > 0) {
        const allowed = config.allowedApiPaths.some((prefix) => {
          const normalized = prefix.endsWith('/') ? prefix : `${prefix}/`;
          return args.path === prefix || args.path.startsWith(normalized);
        });
        if (!allowed) throw new Error(`接口路径不在 WEAVER_API_ALLOWED_PATHS 白名单内：${args.path}`);
      }
      const data = await callApi({
        pathname: args.path,
        method: args.method || 'GET',
        query: args.query || {},
        body: args.body,
      });
      return textResult(data);
    },
  );
}
