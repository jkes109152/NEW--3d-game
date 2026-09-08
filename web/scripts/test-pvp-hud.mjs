import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pvpGroundHud } from '../lib/pvp-hud.ts';
test('沿用單目標準心，耐久、冷卻與可發射分開', () => {
  const v = {
    selfId: 'g',
    runId: 'run',
    phase: 'active',
    elapsed: 5,
    actors: [
      { id: 'g', team: 'ground', alive: true, aiming: true },
      { id: 'a', team: 'air', position: [0, 10, 50], hp: 2, alive: true },
    ],
    lock_valid: ['a'],
    lock_current: 'a',
    locks: { a: 1 },
    cooldown: 0.5,
    events: [],
  };
  let hud = pvpGroundHud(v);
  assert.equal(hud.weapon_category, 'anti_air');
  assert.equal(hud.lock_box_scale, 1);
  assert.equal(hud.fire_mode, 'lock_single');
  assert.equal(hud.aircraft[0].id, 'a');
  assert.equal(hud.fire_blocked, 'cooldown');
  hud = pvpGroundHud({ ...v, cooldown: 0 });
  assert.equal(hud.fire_blocked, null);
  assert.equal(pvpGroundHud({ ...v, lock_valid: [] }).fire_blocked, 'lock');
  assert.equal(pvpGroundHud({ ...v, selfId: 'a' }), null);
});
