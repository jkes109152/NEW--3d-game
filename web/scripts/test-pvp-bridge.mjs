import assert from 'node:assert/strict';
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
const invoke = (name, value) => {
  const fn = py.globals.get(name);
  try {
    return JSON.parse(fn(JSON.stringify(value)));
  } finally {
    fn?.destroy();
  }
};
const roster = [
  { id: 'ground', name: '地面', team: 'ground' },
  { id: 'air', name: '空中', team: 'air' },
];
// 不呼叫 initialize：PvP 不能依賴單人存檔或其交易物件。
const initial = invoke('pvp_start', {
  runId: 'bridge',
  roster,
  timeLimitSeconds: 180,
});
assert.equal(initial.views.air.actors.length, 2);
assert.equal(initial.views.air.remainingSeconds, 180);
assert.equal(initial.phase, 'active');
assert.equal(initial.views.ground.actors[0].speed, 6);
assert.equal('city' in initial.views.air, false);
const next = invoke('pvp_tick', {
  dt: 1 / 120,
  frames: {
    ground: {
      suspended: true,
      stream: 'new',
      inputSeq: 2,
      look_total: [10, 20],
      cancelThrough: 5,
    },
  },
  departedIds: [],
});
assert.deepEqual(next.views.ground.inputAck, {
  stream: 'new',
  input_seq: 2,
  command_seq: 5,
  look_total: [10, 20],
  tick: 1,
});
assert.equal(next.tick, 1);
invoke('pvp_dispose', {});
assert.equal(py.runPython('pvp_battle is None'), true);
const eight = Array.from({ length: 8 }, (_, i) => ({
  id: 'p' + i,
  name: '隊員' + i,
  team: i < 4 ? 'ground' : 'air',
}));
invoke('pvp_start', { runId: 'eight', roster: eight, timeLimitSeconds: 270 });
const frames = Object.fromEntries(
  eight.map((p, i) => [
    p.id,
    {
      stream: 's' + i,
      inputSeq: 10 + i,
      suspended: false,
      look_total: [i, 0],
      move_z: 1,
      turn_x: 0.2,
      commands: [{ sequence: 1, kind: 'jump' }],
    },
  ]),
);
const eightStep = invoke('pvp_tick', { dt: 1 / 60, frames, departedIds: [] });
for (const [i, p] of eight.entries()) {
  const v = eightStep.views[p.id],
    a = v.actors.find((a) => a.id === p.id);
  assert.equal(v.inputAck.stream, 's' + i);
  assert.equal(v.inputAck.input_seq, 10 + i);
  assert.deepEqual(v.inputAck.look_total, [i < 4 ? i : 2, 0]);
  assert.equal(a.hp, i < 4 ? 1 : 2);
  assert.equal('city' in v, false);
  assert.equal('reward' in v, false);
  if (i < 4) {
    assert.ok(a.position[1] > 0);
    assert.equal(a.speed, 6);
  } else {
    assert.equal(a.speed, 40);
    assert.equal(a.position[1], 40);
  }
}
// 視角不屬於規則輸入；額外欄位也不能操控觀戰對象或引發傷害。
const beforeCamera = eightStep.views.p4.actors;
const cameraOnly = invoke('pvp_tick', {
  dt: 0,
  frames: { p4: { camera: 'cockpit', spectator: 'p5' } },
  departedIds: [],
});
assert.deepEqual(cameraOnly.views.p4.actors, beforeCamera);
py.runPython("pvp_battle.eliminate('p4', 'crash')");
const dead = invoke('pvp_tick', { dt: 1 / 120, frames, departedIds: [] });
const position = dead.views.p4.actors.find((a) => a.id === 'p4').position;
const after = invoke('pvp_tick', {
  dt: 1 / 120,
  frames: { p4: { ...frames.p4, throttle: 1, move_z: 1 } },
  departedIds: [],
});
assert.deepEqual(
  after.views.p4.actors.find((a) => a.id === 'p4').position,
  position,
);
assert.deepEqual(after.views.p4.threats, {
  tracking: false,
  locked: false,
  missile: false,
});
invoke('pvp_dispose', {});
assert.equal(py.runPython('pvp_battle is None'), true);
console.log(
  'PASS：八人獨立操作確認、雙陣營分流、視角零副作用、淘汰禁止控制與威脅清除。',
);
console.log(
  'PASS：Pyodide 獨立 PvP、基礎雙陣營、取消確認與清理；沒有存檔依賴。',
);

// 明確比較不同成長存檔；記憶體儲存器不讀寫任何真實玩家資料。
let baseline;
for (const upgraded of [false, true]) {
  const data = new Map();
  const init = py.globals.get('initialize');
  try {
    init({
      getItem: (k) => data.get(k) ?? null,
      setItem: (k, v) => data.set(k, v),
    });
  } finally {
    init.destroy();
  }
  invoke('dispatch', { action: 'select_slot', payload: { slot: 1 } });
  if (upgraded)
    py.runPython(`
app.profile['coins'] = 20000
app.profile['player_upgrades']['max_hp'] = 5
app.profile['owned_weapons']['W01']['upgrade_levels']['damage'] = 2
app.profile['profile_revision'] += 1
app.repository.save(app.slot, app.profile)
`);
  const saved = [...data.entries()];
  const profile = py.runPython('json.dumps(app.profile, sort_keys=True)');
  for (const end of ['normal', 'abort', 'again']) {
    const packet = invoke('pvp_start', {
      runId: 'save-isolation',
      roster,
      timeLimitSeconds: 180,
    });
    if (!baseline) baseline = packet;
    assert.deepEqual(packet, baseline, '配裝成長不能改變 PvP 初始數值');
    const terminal = invoke('pvp_tick', {
      dt: 1 / 120,
      frames: {},
      departedIds: end === 'abort' ? ['ground', 'air'] : ['air'],
    });
    assert.equal(terminal.phase, end === 'abort' ? 'aborted' : 'finished');
    invoke('pvp_dispose', {});
    assert.deepEqual(
      [...data.entries()],
      saved,
      '存檔位元內容及最後遊玩日期不得改變',
    );
    assert.equal(
      py.runPython('json.dumps(app.profile, sort_keys=True)'),
      profile,
    );
  }
}
console.log(
  'PASS：新手／成長存檔進入、結束、中止、再戰的數值一致，存檔與日期零變更。',
);
