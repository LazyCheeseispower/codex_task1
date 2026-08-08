import http from 'node:http';
import assert from 'node:assert/strict';

const fakeE10 = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  if (url.pathname === '/api/bs/open/auth/third') {
    const redirectUri = url.searchParams.get('redirect_uri');
    if (!redirectUri) {
      res.writeHead(400);
      res.end();
      return;
    }
    const target = new URL(redirectUri);
    target.searchParams.set('eteams_token', 'test-eteams-token');
    res.writeHead(302, { Location: target.toString() });
    res.end();
    return;
  }
  res.writeHead(404);
  res.end();
});

await new Promise((resolve) => fakeE10.listen(0, '127.0.0.1', resolve));
const fakePort = fakeE10.address().port;

process.env.WEAVER_API_BASE = `http://127.0.0.1:${fakePort}/papi/openapi`;
process.env.WEAVER_APP_KEY = 'test-app-key';

const { startBrowserLogin } = await import('../src/browserLogin.js');

try {
  const result = await startBrowserLogin({
    timeoutMs: 5000,
    open: async (authUrl) => {
      const auth = new URL(authUrl);
      assert.equal(auth.pathname, '/api/bs/open/auth/third');
      assert.equal(auth.searchParams.get('app_key'), 'test-app-key');
      const redirectUri = auth.searchParams.get('redirect_uri');
      const target = new URL(redirectUri);
      target.searchParams.set('eteams_token', 'test-eteams-token');
      await fetch(target.toString());
    },
  });
  assert.equal(result.eteamsToken, 'test-eteams-token');
  assert.ok(result.authUrl.startsWith(`http://127.0.0.1:${fakePort}/api/bs/open/auth/third?`));
  console.log('browser login callback test passed');
} finally {
  fakeE10.closeAllConnections?.();
  fakeE10.close();
}
