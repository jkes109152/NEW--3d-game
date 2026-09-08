import assert from 'node:assert/strict';
import { multiplayerRequest } from '../lib/multiplayer-server.ts';
import { testDb } from './pvp-test-db.mjs';
import { testCore } from './pvp-test-core.mjs';
import { neutralInput } from '../lib/pvp-types.ts';
const db = testDb();
const core = await testCore();
let now = 1_800_000_000_000;
const clients = Array.from({ length: 9 }, () => ({
  cookie: '',
  id: '',
  instance: crypto.randomUUID(),
}));
async function call(c, action, payload = {}, expected = 200) {
  const response = await multiplayerRequest(
    new Request('http://localhost:3000/api/multiplayer', {
      method: 'POST',
      headers: {
        Origin: 'http://localhost:3000',
        'Content-Type': 'application/json',
        Cookie: c.cookie,
      },
      body: JSON.stringify({
        action,
        protocolVersion: 1,
        instanceId: c.instance,
        ...payload,
      }),
    }),
    db,
    now,
  );
  const v = await response.json();
  assert.equal(response.status, expected, JSON.stringify(v));
  if (response.headers.has('set-cookie'))
    c.cookie = response.headers.get('set-cookie').split(';')[0];
  if (v.me) c.id = v.me.id;
  return v;
}
try {
  for (let i = 0; i < 9; i++)
    await call(clients[i], 'identity', { name: '規格測試' + i });
  const [host, guest] = clients;
  let roomId = (await call(host, 'create', { name: '空地測試', mode: 'pvp' }))
    .roomId;
  await call(guest, 'join', { roomId });
  await call(host, 'start', { roomId }, 400);
  await call(host, 'ready', { roomId, ready: true });
  await call(guest, 'ready', { roomId, ready: true });
  await call(guest, 'start', { roomId }, 403);
  const start = (await call(host, 'start', { roomId })).room;
  assert.equal(start.status, 'countdown');
  assert.equal(start.timeLimitSeconds, 180);
  assert.equal(start.roster.filter((x) => x.team === 'air').length, 1);
  const sync = (await call(guest, 'sync', { roomId })).room;
  const resumed = (
    await call(guest, 'resume', {
      roomId,
      runId: start.runId,
      expectedStream: sync.currentStream,
    })
  ).room;
  assert.ok(resumed.currentStream);
  assert.equal(resumed.inputInstance, guest.instance);
  const again = (
    await call(guest, 'resume', {
      roomId,
      runId: start.runId,
      expectedStream: sync.currentStream,
    })
  ).room;
  assert.equal(again.currentStream, resumed.currentStream);
  await call(
    guest,
    'exchange',
    { roomId, runId: start.runId, inputStream: 'old', inputSeq: 1, input: {} },
    409,
  );
  await call(guest, 'leave', { roomId, runId: start.runId });
  assert.equal((await call(host, 'sync', { roomId })).room.status, 'waiting');
  await call(host, 'leave', { roomId });
  roomId = (await call(host, 'create', { mode: 'pvp' })).roomId;
  for (const c of clients.slice(1, 7)) await call(c, 'join', { roomId });
  const contenders = await Promise.allSettled(
    clients.slice(7).map((c) => call(c, 'join', { roomId })),
  );
  assert.equal(
    contenders.filter((r) => r.status === 'fulfilled').length,
    1,
    '同時搶最後席位只能成功一人',
  );
  const full = (await call(host, 'sync', { roomId })).room;
  assert.equal(full.members.length, 8);
  for (const c of clients
    .slice(1)
    .filter((c) => full.members.some((m) => m.id === c.id)))
    await call(c, 'leave', { roomId });
  await call(host, 'leave', { roomId });
  for (let n = 2; n <= 8; n++) {
    roomId = (await call(host, 'create', { mode: 'pvp' })).roomId;
    for (const c of clients.slice(1, n)) await call(c, 'join', { roomId });
    for (const c of clients.slice(0, n))
      await call(c, 'ready', { roomId, ready: true });
    const started = (await call(host, 'start', { roomId })).room;
    assert.equal(
      started.roster.filter((p) => p.team === 'air').length,
      Math.ceil(n / 2),
    );
    assert.equal(
      started.timeLimitSeconds,
      [180, 300, 210, 330, 240, 390, 270][n - 2],
    );
    await call(clients[n], 'join', { roomId }, 400);
    for (let step = 0; step < 6; step++) {
      now += 500;
      for (const c of clients.slice(0, n)) {
        const r = (await call(c, 'sync', { roomId })).room;
        assert.equal(r.status, step === 5 ? 'playing' : 'countdown');
        assert.equal(r.timeLimitSeconds, started.timeLimitSeconds);
      }
    }
    for (const c of clients.slice(1, n))
      await call(c, 'leave', { roomId, runId: started.runId });
    await call(host, 'leave', { roomId, runId: started.runId });
  }
  assert.equal(
    db.sql.prepare('SELECT count(*) AS n FROM mp_results').get().n,
    0,
  );
  async function openBattle(n = 2) {
    roomId = (await call(host, 'create', { mode: 'pvp' })).roomId;
    for (const c of clients.slice(1, n)) await call(c, 'join', { roomId });
    for (const c of clients.slice(0, n))
      await call(c, 'ready', { roomId, ready: true });
    const r = (await call(host, 'start', { roomId })).room;
    for (const c of clients.slice(0, n)) {
      c.runId = r.runId;
      c.seq = 0;
      const s = (await call(c, 'sync', { roomId })).room;
      c.stream = (
        await call(c, 'resume', {
          roomId,
          runId: r.runId,
          expectedStream: s.currentStream,
        })
      ).room.currentStream;
    }
    for (let i = 0; i < 6; i++) {
      now += 500;
      for (const c of clients.slice(0, n)) await call(c, 'sync', { roomId });
    }
    core.invoke('pvp_start', {
      runId: r.runId,
      roster: r.roster,
      timeLimitSeconds: r.timeLimitSeconds,
    });
    return r;
  }
  const exchange = (c, extra = {}, expected = 200) =>
    call(
      c,
      'exchange',
      {
        roomId,
        runId: c.runId,
        inputStream: c.stream,
        inputSeq: ++c.seq,
        input: neutralInput(),
        ...extra,
      },
      expected,
    );
  const closeBattle = async (n = 2) => {
    for (const c of clients.slice(1, n))
      await call(c, 'leave', { roomId, runId: c.runId });
    await call(host, 'leave', { roomId, runId: host.runId });
  };
  let battle = await openBattle();
  let snap = core.invoke('pvp_tick', {
    dt: 1 / 120,
    frames: {},
    departedIds: [],
  });
  await exchange(guest, { snapshot: snap, sequence: 1 }, 403);
  assert.equal(
    db.sql
      .prepare('SELECT input_seq FROM mp_members WHERE player_id=?')
      .get(guest.id).input_seq,
    0,
    '偽造快照不得順便修改輸入',
  );
  await call(guest, 'finish', { roomId, runId: guest.runId }, 403);
  await call(
    guest,
    'abort',
    { roomId, runId: guest.runId, reason: 'simulation_error' },
    403,
  );
  await exchange(host, { snapshot: snap, sequence: 1 });
  await exchange(guest);
  const received = now;
  now += 990;
  await call(guest, 'sync', { roomId });
  await exchange(guest, { inputSeq: guest.seq - 1 });
  let h = (await call(host, 'sync', { roomId })).room.hostInputs.find(
    (x) => x.playerId === guest.id,
  );
  assert.equal(h.inputReceivedAt, received);
  assert.equal(now - h.inputReceivedAt, 990);
  now += 10;
  h = (await call(host, 'sync', { roomId })).room.hostInputs.find(
    (x) => x.playerId === guest.id,
  );
  assert.equal(now - h.inputReceivedAt, 1000, '心跳不續舊操作');
  const corrupt = structuredClone(snap);
  corrupt.views[host.id].missiles = [{ id: 'broken' }];
  await exchange(host, { snapshot: corrupt, sequence: 2 }, 400);
  // 真實規則產生終局，再只竄改結果條件，檢查提前空中勝利及不一致資料。
  core.py.runPython('pvp_battle.finish("air", "timeout")');
  const early = core.invoke('pvp_tick', { dt: 0, frames: {}, departedIds: [] });
  await exchange(host, { snapshot: early, sequence: 2 }, 400);
  await closeBattle();

  battle = await openBattle();
  const disconnectedAt = now;
  for (let i = 0; i < 9; i++) {
    now += 1000;
    snap = core.invoke('pvp_tick', { dt: 0.01, frames: {}, departedIds: [] });
    await exchange(host, { snapshot: snap, sequence: i + 1 });
  }
  now = disconnectedAt + 9990;
  const reconnected = { ...guest, instance: crypto.randomUUID() };
  const rebound = (
    await call(reconnected, 'resume', {
      roomId,
      runId: guest.runId,
      expectedStream: guest.stream,
    })
  ).room;
  assert.notEqual(rebound.currentStream, guest.stream);
  await exchange(guest, {}, 409);
  guest.instance = reconnected.instance;
  guest.stream = rebound.currentStream;
  guest.seq = 0;
  const oldRoom = roomId,
    oldRun = guest.runId;
  await call(guest, 'leave', { roomId, runId: oldRun });
  const newRoom = (await call(guest, 'create', { mode: 'pvp' })).roomId;
  await call(guest, 'leave', { roomId: oldRoom, runId: oldRun });
  assert.equal(
    db.sql
      .prepare('SELECT room_id FROM mp_members WHERE player_id=?')
      .get(guest.id).room_id,
    newRoom,
  );
  await call(guest, 'leave', { roomId: newRoom });
  await call(host, 'leave', { roomId: oldRoom, runId: host.runId });

  battle = await openBattle();
  const expiredAt = now;
  for (let i = 0; i < 10; i++) {
    now += 1000;
    snap = core.invoke('pvp_tick', { dt: 0.01, frames: {}, departedIds: [] });
    await exchange(host, { snapshot: snap, sequence: i + 1 });
  }
  assert.equal(now - expiredAt, 10000);
  await call(
    { ...guest, instance: crypto.randomUUID() },
    'resume',
    { roomId, runId: guest.runId, expectedStream: guest.stream },
    403,
  );
  assert.ok((await call(host, 'sync', { roomId })).room.departures[guest.id]);
  await closeBattle();

  for (const beforeSnapshot of [true, false]) {
    battle = await openBattle();
    if (!beforeSnapshot)
      await exchange(host, {
        snapshot: core.invoke('pvp_tick', {
          dt: 0.01,
          frames: {},
          departedIds: [],
        }),
        sequence: 1,
      });
    const reload = (
      await call({ ...host, instance: crypto.randomUUID() }, 'sync', { roomId })
    ).room;
    assert.equal(reload.result.winner, null);
    assert.equal(reload.result.reason, 'host_reload');
    await closeBattle();
  }
  battle = await openBattle();
  now += 10000;
  const timeout = (await call(host, 'sync', { roomId })).room;
  assert.equal(timeout.result.reason, 'host_timeout');
  await closeBattle();

  battle = await openBattle(8);
  const initialLevel = db.sql
    .prepare('SELECT level_a,level_b FROM mp_rooms WHERE id=?')
    .get(roomId);
  for (const p of battle.roster.filter((p) => p.team === 'air'))
    core.py.runPython(`pvp_battle.eliminate('${p.id}', 'crash')`);
  snap = core.invoke('pvp_tick', { dt: 1 / 120, frames: {}, departedIds: [] });
  await exchange(host, { snapshot: snap, sequence: 1 });
  const finished = (await call(host, 'finish', { roomId, runId: host.runId }))
    .room;
  assert.equal(finished.result.winner, 'ground');
  now += 11000;
  assert.deepEqual(
    (await call(host, 'sync', { roomId })).room.result,
    finished.result,
    '斷線不可覆寫已確認結果',
  );
  for (const c of clients.slice(1, 8)) await call(c, 'sync', { roomId });
  const waiting = (await call(host, 'again', { roomId, runId: host.runId }))
    .room;
  assert.equal(waiting.status, 'waiting');
  assert.equal(waiting.runId, null);
  assert.ok(waiting.members.every((m) => !m.ready));
  assert.deepEqual(
    db.sql
      .prepare('SELECT level_a,level_b FROM mp_rooms WHERE id=?')
      .get(roomId),
    initialLevel,
  );
  await closeBattle(8);
  assert.equal(
    db.sql.prepare('SELECT count(*) AS n FROM mp_results').get().n,
    0,
  );
  console.log(
    'PASS：十秒重連邊界、輸入時刻、退出資格、權限、結果條件、房主重載／租約、八人結算再戰及零收據。',
  );
  console.log(
    'PASS：獨立 Cookie 的 PvP 房間／權限／準備／分隊／串流初始化／滿房與倒數取消。',
  );
} finally {
  db.sql.close();
}
await import('./test-pvp-transport.mjs');
