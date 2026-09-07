import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { loadPyodide } from 'pyodide';
import * as THREE from 'three';
import { ArmoryModels } from '../lib/armory-models.ts';
import {
  WEAPON_DETAILS,
  ARMOR_DETAILS,
  TURRET_DETAILS,
  weaponRows,
  relevantChanges,
} from '../lib/armory-info.ts';
import {
  orientProjectile,
  tracerEndpoints,
  ProjectileTrail,
  worldVector,
} from '../lib/projectile-visuals.ts';
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
const catalog = JSON.parse(py.globals.get('catalog_json')());
const read = () => JSON.parse(py.globals.get('state_json')());
const send = (action, payload = {}) =>
  JSON.parse(py.globals.get('dispatch')(JSON.stringify({ action, payload })));
const tx = (payload) => send('transaction', payload);
function reset() {
  const data = new Map();
  py.globals.get('initialize')({
    getItem: (k) => data.get(k) ?? null,
    setItem: (k, v) => data.set(k, v),
  });
  send('select_slot', { slot: 1 });
  // Explicit offline fixture for transaction coverage; never modifies browser saves.
  py.runPython(
    "app.profile['coins']=1000000\napp.profile['profile_revision']+=1",
  );
  return send('store');
}
function checkChanges(before, after, changes) {
  for (const [key, change] of Object.entries(changes)) {
    assert.deepEqual(change.before, before[key], key + ' before');
    assert.deepEqual(change.after, after[key], key + ' after');
  }
}
test('every weapon has unique model geometry and complete read-only shop data', () => {
  let s = reset();
  const profile = JSON.stringify(s.profile);
  assert.equal(Object.keys(s.shop.weapons).length, 20);
  const bank = new ArmoryModels(),
    signatures = new Set();
  for (const def of Object.values(catalog.weapons)) {
    assert.ok(WEAPON_DETAILS[def.id]?.description);
    const group = bank.weapon(def.id, catalog),
      parts = [];
    group.traverse((m) => {
      if (m.isMesh)
        parts.push([m.geometry.type, m.position.toArray(), m.scale.toArray()]);
    });
    signatures.add(JSON.stringify(parts));
    const stats = s.shop.weapons[def.id].stats;
    assert.equal(stats.base_damage, def.base_damage);
    assert.equal(stats.interval, def.interval);
    assert.equal(stats.range, def.range);
    assert.ok(weaponRows(def, stats).length >= 6);
  }
  assert.equal(
    signatures.size,
    20,
    'silhouettes must differ without relying on color',
  );
  for (const [id, def] of Object.entries(catalog.armors)) {
    assert.ok(ARMOR_DETAILS[id]);
    assert.equal(s.shop.armors[id].max_hp, 100 + def.hp_delta);
  }
  for (const id of Object.keys(catalog.turrets)) assert.ok(TURRET_DETAILS[id]);
  read();
  assert.equal(
    JSON.stringify(read().profile),
    profile,
    'previews cannot purchase or mutate saves',
  );
  bank.dispose();
});
test('all applicable weapon upgrade deltas and prices match committed transactions', () => {
  let s = reset();
  for (const wid of Object.keys(catalog.weapons)) {
    if (!s.profile.owned_weapons[wid])
      s = tx({ kind: 'purchase_weapon', weapon_id: wid });
    for (const key of Object.keys(s.quotes.weapons[wid])) {
      const before = s.shop.weapons[wid].stats,
        q = s.quotes.weapons[wid][key],
        coins = s.profile.coins;
      assert.ok(q.available);
      assert.ok(Object.keys(q.changes).length);
      s = tx({ kind: 'upgrade_weapon', weapon_id: wid, upgrade_id: key });
      assert.equal(s.transaction_result.result_code, 'applied');
      assert.equal(coins - s.profile.coins, q.price);
      checkChanges(before, s.shop.weapons[wid].stats, q.changes);
    }
  }
  const q = s.quotes.player,
    before = s.shop.player;
  s = tx({ kind: 'upgrade_player', upgrade_id: 'max_hp' });
  checkChanges(before, s.shop.player, q.changes);
  assert.equal(s.shop.player.max_hp, 110);
  for (const [id, a] of Object.entries(catalog.armors))
    assert.equal(s.shop.armors[id].max_hp, 110 + a.hp_delta);
});
test('attachment replacement and removal previews include exact tradeoffs for all guns', () => {
  for (const wid of Object.keys(catalog.weapons)) {
    let s = reset();
    if (!s.profile.owned_weapons[wid])
      s = tx({ kind: 'purchase_weapon', weapon_id: wid });
    for (const a of Object.values(catalog.attachments).filter((a) =>
      a.applicable_weapons.includes(wid),
    )) {
      s = tx({
        kind: 'purchase_attachment',
        weapon_id: wid,
        attachment_id: a.id,
      });
      const before = s.shop.weapons[wid].stats,
        q = s.shop.weapons[wid].attachments[a.id];
      const w = s.profile.owned_weapons[wid];
      s = tx({
        kind: 'customize_weapon',
        weapon_id: wid,
        selected_attachments: { ...w.selected_attachments, [a.slot]: a.id },
        selected_color: w.selected_color,
        selected_pattern: w.selected_pattern,
      });
      assert.equal(s.transaction_result.result_code, 'applied');
      checkChanges(before, s.shop.weapons[wid].stats, q.changes);
      const equipped = s.shop.weapons[wid].stats,
        remove = s.shop.weapons[wid].attachments[a.id],
        current = s.profile.owned_weapons[wid];
      assert.equal(remove.equipped, true);
      // Leave the first feed equipped so the next feed tests same-slot replacement.
      if (a.id !== 'extended_magazine') {
        s = tx({
          kind: 'customize_weapon',
          weapon_id: wid,
          selected_attachments: {
            ...current.selected_attachments,
            [a.slot]: null,
          },
          selected_color: current.selected_color,
          selected_pattern: current.selected_pattern,
        });
        checkChanges(equipped, s.shop.weapons[wid].stats, remove.changes);
      }
    }
  }
});
test('failed transactions are distinguishable from successful upgrades and do not claim success', () => {
  reset();
  py.runPython("app.profile['coins']=0\napp.profile['profile_revision']+=1");
  let s = tx({ kind: 'upgrade_player', upgrade_id: 'max_hp' });
  assert.equal(s.transaction_result.result_code, 'rejected');
  assert.equal(s.shop.player.max_hp, 100);
  assert.match(s.message, /金幣/);
  assert.equal(
    relevantChanges(
      {
        burst_interval: { before: 0.45, after: 0.4 },
        interval: { before: 0.2, after: 0.19 },
      },
      catalog.weapons.W03,
    ).length,
    1,
  );
});
test('actual homing simulation forward and reflected model nose match each frame displacement', () => {
  const frames = JSON.parse(
    py.runPython(`
from air_defense.entities import Missile,V3
from types import SimpleNamespace
from math import sin
tracks=[]
for initial in (V3(0,0,1),V3(1,0,0),V3(0,1,0),V3(-1,-.1,1).normalized()):
    m=Missile('visual-test','target',V3(0,12,0),initial)
    target=SimpleNamespace(hp=1,status='approaching',position=V3(20,35,180))
    track=[]
    for step in range(250):
        target.position=V3(40*sin(step*.025),35,180-step*.12)
        previous=m.position
        result=m.update(.01,target)
        track.append(dict(position=m.position.tuple(),previous=previous.tuple(),forward=m.forward.tuple(),age=m.age))
        if result!='flying':break
    tracks.append(track)
json.dumps(tracks)
`),
  );
  for (const track of frames) {
    const model = new THREE.Group(),
      trail = new ProjectileTrail();
    assert.ok(track.length > 100);
    for (const frame of track) {
      orientProjectile(model, frame.forward);
      const nose = new THREE.Vector3(0, 0, -1).applyQuaternion(
          model.quaternion,
        ),
        motion = worldVector(frame.position)
          .sub(worldVector(frame.previous))
          .normalize();
      assert.ok(
        nose.dot(motion) > 1 - 1e-10,
        'nose must point along actual world displacement',
      );
      trail.update(frame.position, frame.age);
    }
    const last = track.at(-1),
      frozen = JSON.stringify(trail.samples);
    trail.update(last.position, last.age);
    assert.equal(JSON.stringify(trail.samples), frozen);
    assert.ok(trail.samples.length <= 24);
    assert.deepEqual(
      trail.samples.at(-1).point.toArray(),
      worldVector(last.position).toArray(),
    );
    trail.dispose();
  }
});
test('only instant bullets create tracers, all eight shotgun endpoints survive, turret direction is exported', () => {
  const endpoints = Array.from({ length: 8 }, (_, i) => [i, 2, 50]);
  for (const w of Object.values(catalog.weapons))
    assert.equal(
      tracerEndpoints(
        {
          kind: 'weapon_fire',
          weapon_id: w.id,
          position: [0, 2, 0],
          endpoints,
        },
        catalog,
        {},
      ).length,
      w.delivery === 'hitscan' ? 8 : 0,
    );
  for (const id of Object.keys(catalog.turrets))
    assert.equal(
      tracerEndpoints(
        {
          kind: 'turret_fire',
          source_id: 'tower',
          position: [0, 1.2, 0],
          target: [3, 20, 40],
        },
        catalog,
        { turrets: [{ id: 'tower', turret_type_id: id }] },
      ).length,
      id === 'T03' ? 0 : 1,
    );
  reset();
  send('menu');
  send('prepare');
  send('next');
  send('next');
  send('next');
  send('start');
  py.runPython(`
from air_defense.entities import Turret,Missile,V3
from air_defense.projectiles import Rocket
target=next(iter(app.battle.aircraft.values()))
app.battle.turrets['fixture']=Turret('fixture',V3(12,0,10),target.id,turret_type_id='T03')
app.battle.missiles['fixture']=Missile('fixture',target.id,V3(0,2,0),V3(1,1,1).normalized())
app.battle.rockets['fixture']=Rocket('fixture','W19',V3(0,2,0),V3(-1,1,1).normalized(),45,60,3,35,6)
`);
  const s = read(),
    turret = s.battle.turrets[0];
  assert.ok(turret.target_id);
  assert.equal(turret.target_position.length, 3);
  assert.deepEqual(turret.origin, [12, 1.2, 10]);
  for (const kind of ['missiles', 'rockets'])
    assert.equal(s.battle[kind][0].forward.length, 3);
  for (const vector of [
    [1, 1, 0],
    [-1, 1, 0],
    [0, 2, -3],
  ]) {
    const head = new THREE.Group();
    orientProjectile(head, vector);
    assert.ok(
      new THREE.Vector3(0, 0, -1)
        .applyQuaternion(head.quaternion)
        .dot(worldVector(vector).normalize()) >
        1 - 1e-10,
    );
  }
});

test('a sniper turret aims at the shot endpoint even when the first shot removes its target', () => {
  reset();
  send('menu');
  send('prepare');
  send('next');
  send('next');
  send('next');
  send('start');
  py.runPython(`
from air_defense.entities import Turret,Enemy,V3
app.battle.turrets={'side-tower':Turret('side-tower',V3(0,0,0),turret_type_id='T02')}
app.battle.enemies={'side-enemy':Enemy('side-enemy','NORMAL',V3(25,0,0),phase='ground',hp=1)}
app.battle.advance(.01,InputFrame())
`);
  const b = read().battle,
    tower = b.turrets[0],
    shot = b.events.find(
      (e) => e.kind === 'turret_fire' && e.source_id === tower.id,
    );
  assert.ok(shot);
  assert.equal(b.enemies.length, 0);
  assert.deepEqual(tower.target_position, shot.target);
  const head = new THREE.Group();
  orientProjectile(
    head,
    tower.target_position.map((v, i) => v - tower.origin[i]),
  );
  assert.ok(
    new THREE.Vector3(0, 0, -1).applyQuaternion(head.quaternion).x > 0.99,
  );
});
