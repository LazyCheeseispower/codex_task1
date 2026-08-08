import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';

export function loadTokens() {
  try {
    return JSON.parse(fs.readFileSync(config.tokenFile, 'utf8'));
  } catch {
    return null;
  }
}

export function saveTokens(tokens) {
  fs.mkdirSync(path.dirname(config.tokenFile), { recursive: true });
  const merged = {
    ...(loadTokens() || {}),
    ...tokens,
    updatedAt: new Date().toISOString(),
  };
  fs.writeFileSync(config.tokenFile, JSON.stringify(merged, null, 2), 'utf8');
  return merged;
}

export function getValidAccessToken() {
  const tokens = loadTokens();
  if (!tokens?.accessToken) return null;
  const expiresAt = tokens.expiresAt ? new Date(tokens.expiresAt).getTime() : 0;
  if (expiresAt > Date.now() + 30_000) return tokens.accessToken;
  return null;
}
