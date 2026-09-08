// 僅供本機畫面與生命週期驗收：一個腳本房主、六個獨立同伴，保留一格給瀏覽器。
import { setTimeout as sleep } from 'node:timers/promises';
import { testCore } from './pvp-test-core.mjs';
const base = 'http://localhost:3000',
  core = await testCore(),
  count = Number(process.argv[2] || 8);
if (![2, 8].includes(count)) throw Error('只接受二人或八人本機驗收');
const clients = Array.from({ length: count - 1 }, () => ({
    cookie: '',
    id: '',
    instance: crypto.randomUUID(),
    seq: 0,
    stream: '',
    runId: null,
  })),
  host = clients[0];
let stopped = false,
  roomId,
  room,
  packet,
  lastTick = performance.now(),
  sequence = 0,
  loopError = null;
process.on('SIGINT', () => {
  stopped = true;
});
async function call(c, action, extra = {}, retry = 0) {
  const response = await fetch(base + '/api/multiplayer', {
    method: 'POST',
    headers: {
      Origin: base,
      'Content-Type': 'application/json',
      Cookie: c.cookie,
    },
    body: JSON.stringify({
      action,
      roomId,
      protocolVersion: 1,
      instanceId: c.instance,
      runId: c.runId,
      ...extra,
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (response.status >= 500 && retry < 2) {
    console.log('本機開發服務暫時失敗，重試一次');
    await sleep(120);
    return call(c, action, extra, retry + 1);
  }
  const data = await response.json();
  if (!response.ok) throw Error(data.error);
  if (response.headers.has('set-cookie'))
    c.cookie = response.headers.get('set-cookie').split(';')[0];
  if (data.me) c.id = data.me.id;
  return data;
}
function pilot(c, r) {
  const me = r.view?.actors.find((a) => a.id === c.id),
    air = r.roster?.find((a) => a.id === c.id)?.team === 'air';
  if (air)
    return { suspended: false, turn_x: 0.5, look_total: [0, 0], commands: [] };
  const target = r.view?.actors.find((a) => a.team === 'air' && a.alive);
  if (!me || !target) return { suspended: true };
  const dx = target.position[0] - me.position[0],
    dz = target.position[2] - me.position[2],
    dy = target.position[1] - me.position[1] - 1.6;
  const yaw = (Math.atan2(dx, dz) * 180) / Math.PI,
    pitch = (-Math.atan2(dy, Math.hypot(dx, dz)) * 180) / Math.PI;
  return {
    suspended: false,
    look_total: [yaw, pitch],
    commands: [
      { sequence: 1, kind: 'toggle_aim' },
      { sequence: 2, kind: 'fire_down' },
    ],
  };
}
const peers = [];
try {
  for (let i = 0; i < clients.length; i++)
    await call(clients[i], 'identity', {
      name: i ? '飛行驗收同伴' + i : '本機驗收房主',
    });
  roomId = (
    await call(host, 'create', { mode: 'pvp', name: '獨立連線畫面驗收' })
  ).roomId;
  for (const c of clients.slice(1)) await call(c, 'join');
  for (const c of clients) await call(c, 'ready', { ready: true });
  console.log(
    '已建立本機「獨立連線畫面驗收」，瀏覽器加入並準備後自動開始；每局結束後保留結果八秒。',
  );
  let finishedAt = 0,
    rounds = 0;
  for (const c of clients)
    peers.push(
      (async () => {
        while (!stopped) {
          let r = (await call(c, 'sync')).room;
          if (r.status === 'waiting') {
            if (!r.members.find((m) => m.id === c.id)?.ready)
              r = (await call(c, 'ready', { ready: true })).room;
            if (
              c === host &&
              r.members.length === count &&
              r.members.every((m) => m.ready && m.online)
            )
              r = (await call(c, 'start')).room;
          }
          if (c === host) room = r;
          if (['countdown', 'playing'].includes(r.status)) {
            if (c.runId !== r.runId) {
              c.runId = r.runId;
              c.seq = 0;
              c.stream = '';
            }
            if (!c.stream)
              c.stream = (
                await call(c, 'resume', { expectedStream: r.currentStream })
              ).room.currentStream;
            const outgoing = {
              inputStream: c.stream,
              inputSeq: ++c.seq,
              input: pilot(c, r),
            };
            if (
              c === host &&
              packet?.runId === r.runId &&
              r.status === 'playing'
            ) {
              outgoing.snapshot = packet;
              outgoing.sequence = ++sequence;
            }
            r = (await call(c, 'exchange', outgoing)).room;
            if (c === host) {
              room = r;
              if (r.view?.phase === 'finished' && r.status === 'playing')
                room = (await call(c, 'finish')).room;
            }
          }
          if (c === host && r.status === 'finished') {
            if (!finishedAt) {
              finishedAt = Date.now();
              console.log('已確認第 ' + ++rounds + ' 局：' + r.result.reason);
            }
            if (
              Date.now() - finishedAt >
              (process.argv.includes('--lifecycle') ? 200 : 8000)
            ) {
              room = (await call(c, 'again')).room;
              packet = null;
              finishedAt = 0;
            }
          }
          await sleep(120);
        }
      })().catch((e) => {
        loopError = e;
        stopped = true;
      }),
    );
  let activeRun = '';
  while (!stopped) {
    await sleep(1000 / 60);
    const now = performance.now();
    if (
      room?.runId &&
      room.runId !== activeRun &&
      ['countdown', 'playing'].includes(room.status)
    ) {
      activeRun = room.runId;
      packet = core.invoke('pvp_start', {
        runId: activeRun,
        roster: room.roster,
        timeLimitSeconds: room.timeLimitSeconds,
      });
      sequence = 0;
    }
    if (room?.status === 'playing' && packet?.phase === 'active') {
      const frames = Object.fromEntries(
        (room.hostInputs || []).map((m) => [
          m.playerId,
          {
            ...m.input,
            stream: m.inputStream || '',
            inputSeq: m.inputSeq,
            suspended:
              Date.now() - (m.inputReceivedAt || 0) >= 1000 ||
              m.input.suspended !== false,
          },
        ]),
      );
      packet = core.invoke('pvp_tick', {
        dt: (now - lastTick) / 1000,
        frames,
        departedIds: Object.keys(room.departures || {}),
      });
    }
    lastTick = now;
  }
  if (loopError) throw loopError;
} finally {
  stopped = true;
  await Promise.allSettled(peers);
  for (const c of clients.slice().reverse())
    if (roomId) await call(c, 'leave').catch(() => {});
  core.invoke('pvp_dispose');
}
