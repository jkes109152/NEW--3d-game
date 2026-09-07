import { env } from 'cloudflare:workers';
export function multiplayerDb(): D1Database {
  const db = (env as unknown as { DB?: D1Database }).DB;
  if (!db) throw Error('多人服務尚未就緒，請稍後重試');
  return db;
}
