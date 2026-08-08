import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { registerTools } from './tools.js';
import { config } from './config.js';

console.error(`[weaver-openapi-mcp] apiBase=${config.apiBase} appKey=${config.appKey ? 'set' : 'missing'} hostUser=${config.hostUserKey}`);

const server = new McpServer({
  name: 'weaver-openapi-mcp',
  version: '0.1.0',
});

registerTools(server);

const transport = new StdioServerTransport();
await server.connect(transport);
