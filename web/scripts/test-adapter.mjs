import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { loadPyodide } from 'pyodide';
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
const dispatch = py.globals.get('dispatch');
const send = (action, payload = {}, expected) =>
  JSON.parse(dispatch(JSON.stringify({ action, payload, expected })));
const read = () => JSON.parse(py.globals.get('state_json')());
function reset() {
  const data = new Map();
  py.globals.get('initialize')({
    getItem: (k) => data.get(k) ?? null,
    setItem: (k, v) => data.set(k, v),
  });
  return send('select_slot', { slot: 1 });
}
const stamp = (s) => ({
  screen: s.screen,
  revision: s.profile?.profile_revision,
  generation: s.generation,
});
function start() {
  send('prepare');
  send('next');
  send('next');
  send('next');
  return send('start');
}
// Explicit test fixtures supply coins/outcomes and lock membership. These are
// adapter regression tests, not claims of human completion in the browser.
test('displayed quotes equal deductions at every player level and cap', () => {
  let s = reset();
  assert.equal(s.quotes.player.price, 250);
  assert.equal(s.quotes.weapons.W01.damage.price, 200);
  const original = JSON.stringify(s.profile);
  read();
  read();
  assert.equal(
    JSON.stringify(read().profile),
    original,
    'quoting must not mutate saves',
  );
  py.runPython(
    "app.profile['coins']=20000\napp.profile['profile_revision']+=1",
  );
  send('store');
  for (let level = 0; level < 5; level++) {
    s = read();
    assert.equal(s.quotes.player.price, 250 * (level + 1));
    const before = s.profile.coins;
    s = send(
      'transaction',
      { kind: 'upgrade_player', upgrade_id: 'max_hp' },
      stamp(s),
    );
    assert.equal(before - s.profile.coins, 250 * (level + 1));
    assert.equal(s.profile.player_upgrades.max_hp, level + 1);
  }
  assert.equal(s.quotes.player.available, false);
  assert.match(s.quotes.player.reason, /上限/);
  for (let level = 0; level < 2; level++) {
    const before = s.profile.coins,
      price = s.quotes.weapons.W01.damage.price;
    assert.equal(price, 200 * (level + 1));
    s = send(
      'transaction',
      { kind: 'upgrade_weapon', weapon_id: 'W01', upgrade_id: 'damage' },
      stamp(s),
    );
    assert.equal(before - s.profile.coins, price);
  }
});
test('stale route and transaction events cannot advance or charge twice', () => {
  reset();
  let s = send('prepare'),
    old = stamp(s);
  s = send('next', {}, old);
  assert.equal(s.screen, 'prepare_weapons');
  assert.match(send('next', {}, old).message, /畫面已更新/);
  send('back');
  assert.equal(read().screen, 'prepare_armor');
  assert.match(
    send('next', {}, old).message,
    /畫面已更新/,
    'returning to the same named screen must not revive stale events',
  );
  send('menu');
  py.runPython("app.profile['coins']=2000\napp.profile['profile_revision']+=1");
  s = send('store');
  old = stamp(s);
  s = send(
    'transaction',
    { kind: 'upgrade_player', upgrade_id: 'max_hp' },
    old,
  );
  const coins = s.profile.coins;
  s = send(
    'transaction',
    { kind: 'upgrade_player', upgrade_id: 'max_hp' },
    old,
  );
  assert.equal(s.profile.coins, coins);
  assert.equal(s.profile.player_upgrades.max_hp, 1);
});
test('next stage survives result and shop; abandoning resets to stage one', () => {
  reset();
  start();
  py.runPython("app.battle.phase='success'\napp.settle()");
  let s = read();
  assert.equal(s.screen, 'result_success');
  assert.deepEqual(s.cursor, [1, 2]);
  s = send('menu');
  assert.deepEqual(s.cursor, [1, 2]);
  send('store');
  s = send('menu');
  assert.deepEqual(s.cursor, [1, 2]);
  s = start();
  assert.equal(s.battle.level, '1-2');
  s = send('menu');
  assert.deepEqual(s.cursor, [1, 1]);
});
test('HUD reports minimum valid lock, ignores history and normalizes ready tolerance', () => {
  reset();
  start();
  py.runPython(
    "app.battle.lock.valid=('one','two')\napp.battle.lock.progress={'one':1.0,'two':0.25,'old':1.0}",
  );
  let s = read();
  assert.equal(s.battle.lock_progress, 0.25);
  assert.equal(s.battle.lock_ready, false);
  py.runPython("app.battle.lock.progress['two']=1-1e-10");
  s = read();
  assert.equal(s.battle.lock_ready, true);
  assert.equal(s.battle.lock_progress, 1);
  py.runPython('app.battle.lock.valid=()');
  s = read();
  assert.equal(s.battle.lock_progress, 0);
  assert.equal(s.battle.lock_ready, false);
});
test('effective AA box reflects weapon and upgrades; exhausted quota blocks fire', () => {
  reset();
  py.runPython(
    "app.profile['coins']=20000\napp.profile['profile_revision']+=1",
  );
  send('store');
  send('transaction', { kind: 'purchase_weapon', weapon_id: 'W02' });
  send('transaction', {
    kind: 'upgrade_weapon',
    weapon_id: 'W02',
    upgrade_id: 'whitebox',
  });
  send('menu');
  send('prepare');
  send('next');
  send('weapon', { slot: 1, id: 'W02' });
  send('next');
  send('next');
  let s = send('start');
  const scale = py.runPython("WEAPONS['W02'].lock_box_scale*1.1");
  assert.ok(Math.abs(s.battle.lock_box_scale - scale) < 1e-10);
  py.runPython(
    'app.battle.runtime[app.battle.active_weapon_id].quota_remaining=0',
  );
  s = read();
  assert.equal(s.battle.fire_blocked, 'ammo');
});
test('empty slots preserve the active weapon; pause freezes time and inputs', () => {
  reset();
  let s = start();
  const id = s.battle.active_weapon_id;
  s = send('tick', {
    dt: 0.05,
    commands: [{ sequence: 1, kind: 'select_slot', value: 5 }],
  });
  assert.equal(s.battle.active_weapon_id, id);
  s = send('pause');
  const before = s.battle;
  for (let i = 0; i < 3; i++)
    s = send('tick', {
      dt: 0.05,
      move_z: 1,
      look_delta: [10, -10],
      commands: [{ sequence: 2, kind: 'toggle_aim', value: null }],
    });
  assert.equal(s.battle.elapsed, before.elapsed);
  assert.deepEqual(s.battle.player.position, before.player.position);
  assert.equal(s.battle.yaw, before.yaw);
  assert.equal(s.battle.aiming, before.aiming);
});
test('switching to a gun removes an earlier anti-air lock error', () => {
  reset();
  start();
  let s = send('tick', {
    dt: 0.05,
    commands: [
      { sequence: 1, kind: 'fire_up', value: null },
      { sequence: 2, kind: 'fire_down', value: null },
    ],
  });
  assert.equal(s.battle.fire_blocked, 'lock');
  s = send('tick', {
    dt: 0.05,
    commands: [{ sequence: 3, kind: 'select_slot', value: 3 }],
  });
  assert.equal(s.battle.active_weapon_id, 'W03');
  assert.equal(s.battle.fire_blocked, null);
  assert.equal(s.battle.weapon_error, null);
});

function slotFixture() {
  const data = new Map();
  let denyDelete = false;
  py.globals.get('initialize')({
    getItem: (k) => data.get(k) ?? null,
    setItem: (k, v) => data.set(k, v),
    removeItem: (k) => {
      if (denyDelete) throw Error('denied');
      data.delete(k);
    },
  });
  return {
    data,
    denyDelete: () => {
      denyDelete = true;
    },
  };
}
test('legacy saves remain intact and last-played metadata updates on selection', () => {
  const { data } = slotFixture();
  const profile = JSON.parse(py.runPython('json.dumps(new_profile())'));
  const legacy = JSON.stringify(profile);
  data.set('candy-defense-web-v2:slot-1', legacy);
  let s = read();
  assert.equal(s.slots[0].status, 'ready');
  assert.equal(s.slots[0].last_played_at, null);
  assert.equal(
    data.get('candy-defense-web-v2:slot-1'),
    legacy,
    'listing must not rewrite old saves',
  );
  s = send('select_slot', { slot: 1 });
  assert.deepEqual(s.profile, profile);
  const envelope = JSON.parse(data.get('candy-defense-web-v2:slot-1'));
  assert.deepEqual(envelope.profile, profile);
  assert.ok(Number.isFinite(Date.parse(envelope.last_played_at)));
  send('slots');
  assert.equal(read().slots[0].last_played_at, envelope.last_played_at);
});
test('delete requires a fresh confirmation and preserves all other slots and preferences', () => {
  const { data } = slotFixture();
  send('select_slot', { slot: 1 });
  send('slots');
  send('select_slot', { slot: 2 });
  send('slots');
  data.set('candy-defense-web:controls', '{"muted":true}');
  const other = data.get('candy-defense-web-v2:slot-2');
  const first = send('request_delete', { slot: 1 }).delete_confirmation;
  send('cancel_delete');
  send('confirm_delete', first);
  assert.ok(data.has('candy-defense-web-v2:slot-1'));
  const confirmation = send('request_delete', { slot: 1 }).delete_confirmation;
  const changed = JSON.parse(data.get('candy-defense-web-v2:slot-1'));
  changed.last_played_at = '2026-09-08T00:00:00Z';
  data.set('candy-defense-web-v2:slot-1', JSON.stringify(changed));
  assert.match(send('confirm_delete', confirmation).message, /已變更/);
  assert.ok(data.has('candy-defense-web-v2:slot-1'));
  const fresh = send('request_delete', { slot: 1 }).delete_confirmation;
  let s = send('confirm_delete', fresh);
  assert.equal(s.slots[0].status, 'empty');
  assert.equal(data.has('candy-defense-web-v2:slot-1'), false);
  assert.equal(data.get('candy-defense-web-v2:slot-2'), other);
  assert.equal(data.get('candy-defense-web:controls'), '{"muted":true}');
  send('select_slot', { slot: 1 });
  send('slots');
  send('confirm_delete', fresh);
  assert.equal(
    read().slots[0].status,
    'ready',
    'old confirmation cannot delete recreated progress',
  );
});
test('failed deletion preserves corrupt bytes; successful current-slot deletion clears memory', () => {
  let fixture = slotFixture();
  fixture.data.set('candy-defense-web-v2:slot-3', 'broken');
  assert.equal(read().slots[2].status, 'corrupt');
  const confirmation = send('request_delete', { slot: 3 }).delete_confirmation;
  fixture.denyDelete();
  assert.match(send('confirm_delete', confirmation).message, /刪除未完成/);
  assert.equal(fixture.data.get('candy-defense-web-v2:slot-3'), 'broken');
  fixture = slotFixture();
  send('select_slot', { slot: 1 });
  send('slots');
  const active = send('request_delete', { slot: 1 }).delete_confirmation;
  const s = send('confirm_delete', active);
  assert.equal(s.profile, null);
  assert.equal(s.slot, null);
  assert.equal(s.draft, null);
  send('select_slot', { slot: 1 });
  assert.equal(read().profile.coins, 0);
});
test('all three turret kinds respect ownership and capacity, and removal keeps inventory', () => {
  reset();
  py.runPython(
    "app.profile['rebirth_count']=2\napp.profile['coins']=10000\napp.profile['profile_revision']+=1",
  );
  send('store');
  for (const id of ['T01', 'T02', 'T03', 'T01', 'T02'])
    send('transaction', { kind: 'purchase_turret', turret_id: id });
  const owned = read().profile.owned_turrets;
  assert.equal(owned.length, 5);
  send('menu');
  send('prepare');
  send('next');
  send('next');
  assert.match(send('place', { id: 'unowned', x: -50, z: 0 }).message, /擁有/);
  for (let i = 0; i < 4; i++) {
    const s = send('place', {
      id: owned[i].instance_id,
      x: -50,
      z: -30 + i * 30,
    });
    assert.equal(s.draft.deployments.length, i + 1);
  }
  assert.match(
    send('place', { id: owned[4].instance_id, x: -50, z: 100 }).message,
    /容量/,
  );
  let s = send('remove', { id: owned[1].instance_id });
  assert.equal(s.draft.deployments.length, 3);
  assert.equal(s.profile.owned_turrets.length, 5);
  s = send('place', { id: owned[4].instance_id, x: -50, z: 100 });
  assert.equal(s.draft.deployments.length, 4);
  s = send('place', { id: owned[0].instance_id, x: -45, z: -30 });
  assert.equal(
    s.draft.deployments.length,
    4,
    'moving a tower cannot consume another unit',
  );
});
