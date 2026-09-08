// 真實本機 HTTP 傳輸；各玩家使用獨立 Cookie。只綁定回環介面，沒有正式服務參數。
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { setTimeout as sleep } from 'node:timers/promises';
import { multiplayerRequest } from '../lib/multiplayer-server.ts';
import { neutralInput } from '../lib/pvp-types.ts';
import { testDb } from './pvp-test-db.mjs';
import { testCore } from './pvp-test-core.mjs';
if (process.argv.slice(2).some((x) => /^https?:/.test(x)))
  throw Error('測試自行建立本機服務，不接受外部網址');
const db = testDb(),
  core = await testCore();
const server = createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const part of req) chunks.push(part);
    const response = await multiplayerRequest(
      new Request(base + req.url, {
        method: 'POST',
        headers: req.headers,
        body: Buffer.concat(chunks),
      }),
      db,
    );
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(await response.text());
  } catch (e) {
    res.writeHead(500);
    res.end(JSON.stringify({ error: e.message }));
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
async function call(c, action, extra = {}, rtt = 0) {
  await sleep(rtt / 2);
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
      ...extra,
    }),
    signal: AbortSignal.timeout(5000),
  });
  const v = await r.json();
  assert.equal(r.status, 200, JSON.stringify(v));
  if (r.headers.has('set-cookie'))
    c.cookie = r.headers.get('set-cookie').split(';')[0];
  if (v.me) c.id = v.me.id;
  await sleep(rtt / 2);
  return v;
}
try {
  for (const [n, rtt, abort] of [
    [2, 200, false],
    [2, 500, true],
    [8, 500, false],
    [8, 200, true],
  ]) {
    const clients = Array.from({ length: n }, () => ({
        id: '',
        cookie: '',
        instance: crypto.randomUUID(),
        seq: 0,
        stream: '',
        result: null,
        doneAt: 0,
      })),
      host = clients[0];
    let roomId,
      runId,
      stopped = false,
      loops = [],
      packet,
      sequence = 0,
      published = 0,
      confirmedAt = 0;
    try {
      for (let i = 0; i < n; i++)
        await call(clients[i], 'identity', { name: `連線測試${i + 1}` });
      roomId = (await call(host, 'create', { mode: 'pvp' })).roomId;
      for (const c of clients.slice(1)) await call(c, 'join', { roomId });
      for (const c of clients) await call(c, 'ready', { roomId, ready: true });
      const started = (await call(host, 'start', { roomId })).room;
      runId = started.runId;
      for (const c of clients) {
        const s = (await call(c, 'sync', { roomId })).room;
        c.stream = (
          await call(c, 'resume', {
            roomId,
            runId,
            expectedStream: s.currentStream,
          })
        ).room.currentStream;
      }
      while (Date.now() < started.startsAt) {
        await Promise.all(clients.map((c) => call(c, 'sync', { roomId })));
        await sleep(120);
      }
      await Promise.all(clients.map((c) => call(c, 'sync', { roomId })));
      packet = core.invoke('pvp_start', {
        runId,
        roster: started.roster,
        timeLimitSeconds: started.timeLimitSeconds,
      });
      let tickAt = performance.now(),
        elapsedWall = 0;
      loops = clients.map((c, i) =>
        (async () => {
          while (!stopped && !c.result) {
            const seq = ++c.seq;
            const outgoing = {
              roomId,
              runId,
              inputStream: c.stream,
              inputSeq: seq,
              input: neutralInput(),
            };
            // 每五次跳過一次快照；每四次重送相同輸入序號。控制仍持續送出。
            if (i === 0 && seq % 5 !== 0) {
              outgoing.snapshot = structuredClone(packet);
              outgoing.sequence = ++sequence;
              published++;
            }
            let r = (await call(c, 'exchange', outgoing, rtt)).room;
            if (seq % 4 === 0) r = (await call(c, 'exchange', outgoing)).room;
            if (
              i === 0 &&
              r.view?.phase === 'finished' &&
              r.status === 'playing'
            ) {
              r = (await call(c, 'finish', { roomId, runId }, rtt)).room;
              confirmedAt = Date.now();
            }
            if (r.result) {
              c.result = r.result;
              c.doneAt = Date.now();
              break;
            }
            await sleep(120);
          }
        })(),
      );
      while (!clients.every((c) => c.result)) {
        await sleep(1000 / 60);
        const next = performance.now(),
          dt = (next - tickAt) / 1000;
        tickAt = next;
        elapsedWall += dt;
        assert.ok(elapsedWall < 25, '本機連線未如期結束');
        if (packet.phase === 'active' && !abort)
          packet = core.invoke('pvp_tick', { dt, frames: {}, departedIds: [] });
        if (packet.phase === 'active' && abort) {
          packet = core.invoke('pvp_tick', { dt, frames: {}, departedIds: [] });
          if (elapsedWall >= 2) {
            await call(host, 'abort', {
              roomId,
              runId,
              reason: 'simulation_gap',
            });
            confirmedAt = Date.now();
          }
        }
      }
      stopped = true;
      await Promise.all(loops);
      for (const c of clients) assert.deepEqual(c.result, host.result);
      assert.equal(host.result.winner, abort ? null : 'ground');
      assert.equal(
        host.result.reason,
        abort ? 'simulation_gap' : 'air_eliminated',
      );
      const alignment =
        Math.max(...clients.map((c) => c.doneAt)) -
        Math.min(...clients.map((c) => c.doneAt));
      assert.ok(alignment < 1000, `共同結果對齊超時：${alignment}`);
      assert.equal(
        db.sql.prepare('SELECT count(*) AS n FROM mp_results').get().n,
        0,
      );
      console.log(
        JSON.stringify({
          players: n,
          roundTripMs: rtt,
          scenario: abort ? '中止' : '自然飛行越界終局',
          droppedSnapshots: Math.floor(host.seq / 5),
          replayedInputs: clients.reduce(
            (sum, c) => sum + Math.floor(c.seq / 4),
            0,
          ),
          publishedSnapshots: published,
          resultAlignmentMs: alignment,
          winner: host.result.winner,
          receiptCount: 0,
        }),
      );
    } finally {
      stopped = true;
      await Promise.allSettled(loops);
      for (const c of clients.slice().reverse())
        if (roomId) await call(c, 'leave', { roomId, runId }).catch(() => {});
      core.invoke('pvp_dispose');
    }
  }
  // 傳輸延遲量測使用固定位置靶機；鎖定與傷害仍由 Python 真實規則產生。
  // 此夾具只隔離運動，不作真人飛行驗收證據。
  for (const n of [2, 8]) {
    const clients = Array.from({ length: n }, () => ({
      cookie: '',
      id: '',
      instance: crypto.randomUUID(),
      seq: 0,
    }));
    const host = clients[0];
    let roomId, runId;
    try {
      for (const [i, c] of clients.entries())
        await call(c, 'identity', { name: '同步量測' + i });
      roomId = (await call(host, 'create', { mode: 'pvp' })).roomId;
      for (const c of clients.slice(1)) await call(c, 'join', { roomId });
      for (const c of clients) await call(c, 'ready', { roomId, ready: true });
      const start = (await call(host, 'start', { roomId })).room;
      runId = start.runId;
      for (const c of clients) {
        const sync = (await call(c, 'sync', { roomId })).room;
        c.stream = (
          await call(c, 'resume', {
            roomId,
            runId,
            expectedStream: sync.currentStream,
          })
        ).room.currentStream;
      }
      while (Date.now() < start.startsAt) {
        await Promise.all(clients.map((c) => call(c, 'sync', { roomId })));
        await sleep(120);
      }
      await Promise.all(clients.map((c) => call(c, 'sync', { roomId })));
      core.invoke('pvp_start', {
        runId,
        roster: start.roster,
        timeLimitSeconds: start.timeLimitSeconds,
      });
      core.py.runPython(`
from unittest.mock import patch
from air_defense.entities import angles, V3
fixture_ground = next(k for k,a in pvp_battle.actors.items() if a['team']=='ground')
fixture_air = next(k for k,a in pvp_battle.actors.items() if a['team']=='air')
pvp_battle.actors[fixture_ground].update(position=[0,0,0])
pvp_battle.actors[fixture_air].update(position=[0,10,50])
fixture_yaw, fixture_pitch = angles(V3(0,8.4,50))
pvp_battle.actors[fixture_ground].update(yaw=fixture_yaw,pitch=fixture_pitch)
fixture_frame = dict(suspended=False, stream='fixture', inputSeq=1, commands=[dict(sequence=1,kind='toggle_aim')])
def fixture_advance(seconds):
    with patch('air_defense.pvp.move_actor'):
        for _ in range(round(seconds*120)):
            pvp_battle.advance(1/120,{fixture_ground:fixture_frame})
`);
      const target = core.py.runPython('fixture_air'),
        ground = core.py.runPython('fixture_ground');
      let sequence = 0;
      for (const [label, seconds] of [
        ['追蹤', 1],
        ['鎖定', 2],
        ['傷害', 0.6],
      ]) {
        if (label === '傷害')
          core.py.runPython(
            "fixture_frame['commands'].append(dict(sequence=2,kind='fire_down'))",
          );
        core.py.runPython(`fixture_advance(${seconds})`);
        const packet = core.invoke('pvp_tick', { dt: 0 });
        if (label === '追蹤')
          assert.equal(packet.views[target].threats.tracking, true);
        if (label === '鎖定')
          assert.equal(packet.views[target].threats.locked, true);
        if (label === '傷害')
          assert.equal(
            packet.views[target].actors.find((a) => a.id === target).hp,
            1,
          );
        const createdAt = performance.now();
        const accepted = (
          await call(
            host,
            'exchange',
            {
              roomId,
              runId,
              inputStream: host.stream,
              inputSeq: ++host.seq,
              input: neutralInput(),
              snapshot: packet,
              sequence: ++sequence,
            },
            200,
          )
        ).room;
        const received = await Promise.all(
          clients.map(async (c) => {
            const r =
              c === host
                ? accepted
                : (await call(c, 'sync', { roomId }, 200)).room;
            assert.deepEqual(r.view.actors, packet.views[c.id].actors);
            assert.deepEqual(r.view.threats, packet.views[c.id].threats);
            if (c.id === ground)
              assert.deepEqual(r.view.locks, packet.views[ground].locks);
            return performance.now() - createdAt;
          }),
        );
        const alignment = Math.ceil(Math.max(...received));
        assert.ok(alignment < 1000, `${label}對齊超時：${alignment}`);
        console.log(
          JSON.stringify({
            players: n,
            roundTripMs: 200,
            stage: label,
            stateAlignmentMs: alignment,
          }),
        );
      }
    } finally {
      for (const c of clients.slice().reverse())
        if (roomId) await call(c, 'leave', { roomId, runId }).catch(() => {});
      core.invoke('pvp_dispose');
    }
  }
} finally {
  await new Promise((resolve) => server.close(resolve));
  db.sql.close();
}
