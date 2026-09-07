import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadPyodide } from 'pyodide';
const url = 'http://localhost:3000/api/multiplayer';
const py = await loadPyodide();
py.FS.mkdirTree('/home/pyodide/air_defense');
for (const name of JSON.parse(
  await readFile('public/rules/manifest.json', 'utf8'),
))
  py.FS.writeFile(
    `/home/pyodide/air_defense/${name}.py`,
    await readFile(`public/rules/${name}.py`, 'utf8'),
  );
py.runPython(await readFile('public/bridge.py', 'utf8'));
const storage = new Map();
py.globals.get('initialize')({
  getItem: (k) => storage.get(k) ?? null,
  setItem: (k, v) => storage.set(k, v),
});
const send = (action, payload = {}) =>
  JSON.parse(py.globals.get('dispatch')(JSON.stringify({ action, payload })));
const profile = send('select_slot', { slot: 1 }).profile;
const clients = Array.from({ length: 3 }, () => ({ cookie: '', id: '' }));
async function call(client, action, data = {}, status = 200) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Origin: 'http://localhost:3000',
      Cookie: client.cookie,
    },
    body: JSON.stringify({ action, ...data }),
  });
  const result = await response.json();
  assert.equal(response.status, status, JSON.stringify(result));
  const cookie = response.headers.get('set-cookie');
  if (cookie) client.cookie = cookie.split(';')[0];
  if (result.me) client.id = result.me.id;
  return result;
}
let roomId;
try {
  for (let i = 0; i < clients.length; i++)
    await call(clients[i], 'identity', { name: `驗證玩家${i}` });
  const [host, guest, outsider] = clients;
  roomId = (await call(host, 'create', { name: '多人整合驗證' })).roomId;
  await call(host, 'start', { roomId }, 400);
  await call(guest, 'join', { roomId });
  await call(outsider, 'exchange', { roomId }, 403);
  await call(host, 'ready', { roomId, ready: true, profile });
  const other = JSON.parse(JSON.stringify(profile));
  other.profile_id = 'b'.repeat(32);
  await call(guest, 'ready', { roomId, ready: true, profile: other });
  await call(guest, 'start', { roomId }, 403);
  const started = (await call(host, 'start', { roomId })).room;
  assert.equal(started.roster.length, 2);
  assert.equal(started.status, 'playing');
  await call(outsider, 'join', { roomId }, 400);
  const packet = JSON.parse(
    py.globals.get('party_start')(
      JSON.stringify({
        runId: started.runId,
        level: started.level,
        roster: started.roster,
      }),
    ),
  );
  assert.equal(packet.views[host.id].aircraft.length, 2);
  await call(guest, 'exchange', {
    roomId,
    inputSeq: 1,
    input: { move_x: 1, commands: [], look_delta: [0, 0] },
  });
  const hostExchange = await call(host, 'exchange', { roomId });
  assert.equal(
    hostExchange.room.members.find((m) => m.id === guest.id).input.move_x,
    1,
  );
  const frames = Object.fromEntries(
    hostExchange.room.members.map((m) => [m.id, m.input]),
  );
  const next = JSON.parse(
    py.globals.get('party_tick')(JSON.stringify({ dt: 0.06, frames })),
  );
  await call(host, 'exchange', {
    roomId,
    runId: started.runId,
    sequence: 1,
    snapshot: next,
  });
  const received = (await call(guest, 'exchange', { roomId })).room.snapshot
    .view;
  assert.equal(received.self_id, guest.id);
  assert.equal(received.players.length, 2);
  assert.equal(received.aircraft[0].id, next.views[host.id].aircraft[0].id);
  await call(
    guest,
    'exchange',
    { roomId, runId: started.runId, sequence: 2, snapshot: next },
    403,
  );
  await call(host, 'finish', { roomId, runId: started.runId }, 400);
  // Deterministic terminal fixture; this is a transport/settlement test, not a played-through victory.
  py.runPython(
    'party_battle.aircraft.clear();party_battle.enemies.clear();party_battle.check_outcome()',
  );
  const terminal = JSON.parse(py.globals.get('party_snapshot')());
  await call(host, 'exchange', {
    roomId,
    runId: started.runId,
    sequence: 2,
    snapshot: terminal,
  });
  const first = (await call(host, 'finish', { roomId, runId: started.runId }))
    .room.receipt;
  const replay = (await call(host, 'finish', { roomId, runId: started.runId }))
    .room.receipt;
  const guestReceipt = (await call(guest, 'exchange', { roomId })).room.receipt;
  assert.equal(first.reward, 187);
  assert.equal(guestReceipt.reward, 187);
  assert.deepEqual(first, replay);
  const reward = (receipt) =>
    JSON.parse(py.globals.get('party_reward')(JSON.stringify(receipt)));
  assert.equal(reward(first).profile.coins, 187);
  assert.equal(reward(first).profile.coins, 187);
  await call(host, 'again', { roomId });
  const waiting = (await call(guest, 'exchange', { roomId })).room;
  assert.equal(waiting.status, 'waiting');
  assert.deepEqual(waiting.level, [1, 2, 2]);
  assert.ok(waiting.members.every((m) => !m.ready));
  console.log(
    'PASS: independent sessions, lobby/join, membership and host permissions, readiness, shared world/input, full per-player rewards, replay safety, next round.',
  );
} finally {
  if (roomId) {
    await call(clients[1], 'leave', { roomId }).catch(() => {});
    await call(clients[0], 'leave', { roomId }).catch(() => {});
  }
}
