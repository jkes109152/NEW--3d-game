// 本機畫面驗收用獨立玩家，不連正式服務，不保存 Cookie。
import { setTimeout as sleep } from 'node:timers/promises';
const base = 'http://localhost:3000';
const name = process.argv[2] || '本機空地驗收',
  count = Number(process.argv[3] || 7);
if (!Number.isInteger(count) || count < 1 || count > 7)
  throw Error('測試同伴人數需為 1 至 7');
let stopped = false;
process.on('SIGINT', () => {
  stopped = true;
});
const clients = Array.from({ length: count }, () => ({
  cookie: '',
  instance: crypto.randomUUID(),
  stream: '',
  run: null,
  id: '',
  seq: 0,
  roomId: null,
}));
async function call(c, action, data = {}) {
  const r = await fetch(base + '/api/multiplayer', {
    method: 'POST',
    headers: {
      Origin: base,
      'Content-Type': 'application/json',
      Cookie: c.cookie,
    },
    body: JSON.stringify({
      action,
      protocolVersion: 1,
      instanceId: c.instance,
      ...data,
    }),
    signal: AbortSignal.timeout(8000),
  });
  const v = await r.json();
  if (!r.ok) throw Error(v.error);
  if (r.headers.has('set-cookie'))
    c.cookie = r.headers.get('set-cookie').split(';')[0];
  if (v.me) c.id = v.me.id;
  return v;
}
try {
  const lobby = await call(clients[0], 'lobby');
  const room = lobby.rooms.find((r) => r.name === name && r.mode === 'pvp');
  if (!room) throw Error('找不到指定的本機驗收房間');
  for (let i = 0; i < count; i++) {
    const c = clients[i];
    await call(c, 'identity', { name: '測試隊員' + (i + 1) });
    c.roomId = room.id;
    await call(c, 'join', { roomId: room.id });
    await call(c, 'ready', { roomId: room.id, ready: true });
  }
  console.log(
    `本機房間已有 ${count} 位独立測試同伴，等待房主開始。`.replace(
      '独立',
      '獨立',
    ),
  );
  await Promise.all(
    clients.map(async (c) => {
      while (!stopped) {
        try {
          let r = (await call(c, 'sync', { roomId: c.roomId })).room;
          if (r.runId && ['countdown', 'playing'].includes(r.status)) {
            if (c.run !== r.runId) {
              c.stream = '';
              c.run = r.runId;
              c.seq = 0;
            }
            if (!c.stream) {
              r = (
                await call(c, 'resume', {
                  roomId: c.roomId,
                  runId: c.run,
                  expectedStream: r.currentStream,
                })
              ).room;
              c.stream = r.currentStream;
            }
            const team = r.roster.find((p) => p.id === c.id)?.team;
            await call(c, 'exchange', {
              roomId: c.roomId,
              runId: c.run,
              inputStream: c.stream,
              inputSeq: ++c.seq,
              input: {
                suspended: team !== 'air',
                turn_x: team === 'air' ? 0.5 : 0,
                look_total: [0, 0],
                commands: [],
              },
            });
          } else if (r.status === 'waiting') {
            c.stream = '';
            c.run = null;
            if (!r.members.find((m) => m.id === c.id)?.ready)
              await call(c, 'ready', { roomId: c.roomId, ready: true });
          }
        } catch (e) {
          console.log('本機同伴：' + e.message);
          break;
        }
        await sleep(120);
      }
    }),
  );
} finally {
  for (const c of clients)
    if (c.roomId)
      await call(c, 'leave', {
        roomId: c.roomId,
        ...(c.run ? { runId: c.run } : {}),
      }).catch(() => {});
}
