# weaver-openapi-mcp

泛微 E10 Open API 的 MCP Server。它通过浏览器打开泛微 E10 登录页，复用默认浏览器里已有的登录态；用户完成登录后，MCP 拿回 `eteams_token`，解析出该用户的信息并绑定到当前宿主用户。后续所有业务调用都只能使用这个已绑定用户的身份，不能传入其他人的 `userid` 来借用权限。

## 登录链路

1. MCP 在 `127.0.0.1` 启动一个临时回调服务。
2. 用默认浏览器打开 `{E10 地址}/api/bs/open/auth/third?app_key=...&redirect_uri=http://127.0.0.1:<port>/callback/<nonce>`。
3. 用户在泛微页面登录，或复用已有登录态，浏览器跳到本地回调并携带 `eteams_token`。
4. MCP 调用 `/oauth2/getUserInfo` 换取用户邮箱/工号/手机号，再调用 `/api/hrm/restful/queryEmployee` 解析出 `userid`。
5. 会话按宿主用户保存到 `data/sessions.json`，工具结果只返回用户信息，不返回令牌。

## 需要你提供

1. 泛微开放平台 API 基础地址，例如 `https://zdyl.zhende.com:11112/papi/openapi`
2. 已创建并通过审核的应用 `app_key`（浏览器免登和身份解析都需要）
3. 可选：企业 `corpId`
4. WorkBuddy/宿主侧能注入当前用户标识，作为 `WEAVER_USER_KEY`

## 配置

| 环境变量 | 说明 |
| --- | --- |
| `WEAVER_API_BASE` | API 基础地址，默认 `https://zdyl.zhende.com:11112/papi/openapi` |
| `WEAVER_APP_KEY` | 应用 app_key，浏览器免登必填 |
| `WEAVER_APP_SECRET` | 应用 app_secret（授权码换 token 流程使用） |
| `WEAVER_CORP_ID` | 可选，企业 corpId |
| `WEAVER_USER_KEY` | 当前宿主用户 ID（WorkBuddy 用户 ID 或业务系统用户 ID），优先于 `WORKBUDDY_USER_ID` |
| `WORKBUDDY_USER_ID` | 兼容别名，宿主注入 WorkBuddy 用户 ID 时使用 |
| `WEAVER_REQUIRE_BINDING` | 设为 `true` 时强制要求 `data/bindings.json` 中有预绑定关系，默认 `false` |
| `WEAVER_BINDINGS_FILE` | 可选，宿主用户到泛微账号的预绑定文件 |
| `WEAVER_SESSIONS_FILE` | 可选，会话文件路径，默认 `data/sessions.json` |
| `WEAVER_CALLBACK_HOST` | 可选，本地回调监听地址，默认 `127.0.0.1` |
| `WEAVER_LOGIN_TIMEOUT_MS` | 可选，浏览器登录等待毫秒数，默认 `300000` |
| `WEAVER_IDENTITY_PARAM` | 可选，自动注入的身份参数名，默认 `userid` |
| `WEAVER_AUTO_INJECT_USERID` | 设为 `false` 时不自动注入身份参数，但仍会拒绝不匹配的身份参数 |
| `WEAVER_API_ALLOWED_PATHS` | 可选，`weaver_api_request` 的接口白名单前缀，逗号分隔；留空表示不限制 |

`data/bindings.json` 示例：

```json
{
  "workbuddy-user-001": {
    "email": "0617001@e.cn",
    "jobNum": "RYGH5612"
  }
}
```

如果设置了预绑定，浏览器登录的泛微账号必须与预绑定至少匹配一项，否则登录会被拒绝。

## 工具

| 工具 | 说明 |
| --- | --- |
| `weaver_login` | 打开默认浏览器登录泛微，登录成功后绑定当前宿主用户并返回用户信息 |
| `weaver_whoami` | 查看当前宿主用户绑定的泛微账号 |
| `weaver_logout` | 清除当前宿主用户的本地会话 |
| `weaver_get_departments` | 查询部门列表（老接口 `/department/v2/list`） |
| `weaver_api_request` | 通用请求，自动带当前登录用户的 `userid`，并拒绝任何指向其他用户的身份参数 |

## 安全模型

- 每个 MCP 进程对应一个宿主用户，宿主通过 `WEAVER_USER_KEY` 或 `WORKBUDDY_USER_ID` 注入自己的用户 ID。
- `weaver_login` 只接受浏览器回调里由泛微返回的 `eteams_token`，MCP 自己解析并绑定身份，不允许 Agent 直接指定 `userid`。
- 通用接口调用前会检查 `query` 和 `body` 里的 `userid`、`user_id`、`useridList`、`account`、`loginid`、`jobNum`、`jobNumList`、`employeeId`、`email`、`mobile` 等身份字段；只要不是当前绑定用户，直接拒绝。
- 未配置身份时自动注入当前用户的 `userid`，令牌不会出现在工具结果里。
- 生产环境建议开启 `WEAVER_REQUIRE_BINDING=true`，并在 `bindings.json` 中预置宿主用户到泛微账号的映射，避免同一台机器上的多个用户串用身份。

## 安装与运行

```bash
npm install
npm test
npm run smoke
```

## 注册到 Codex

在 `.codex/config.toml` 增加：

```toml
[mcp_servers.weaver_openapi]
command = "cmd"
args = ["/c", "node", "D:\\codex项目\\weaver-openapi-mcp\\src\\index.js"]
startup_timeout_sec = 30

[mcp_servers.weaver_openapi.env]
WEAVER_API_BASE = "https://zdyl.zhende.com:11112/papi/openapi"
WEAVER_APP_KEY = "PASTE_YOUR_APP_KEY"
WEAVER_APP_SECRET = "PASTE_YOUR_APP_SECRET"
WEAVER_CORP_ID = ""
WEAVER_USER_KEY = ""
WEAVER_REQUIRE_BINDING = "false"
```

## 注意事项

- MCP 进程必须跑在用户本人电脑上，默认浏览器里需要有泛微 E10 的登录态或允许弹出登录页。
- 如果免登页面提示 `redirect_uri` 不在白名单，需要在泛微开放平台登记本地回调地址，或把 `WEAVER_CALLBACK_HOST` 配置为内网可访问的地址并开放端口。
- `data/sessions.json` 保存的是本地会话令牌，不要提交到 Git，也不要在工具结果里返回。
- 如果平台使用自签名证书，可在启动命令的环境变量中加入 `NODE_TLS_REJECT_UNAUTHORIZED=0`，仅建议在可信内网使用。
