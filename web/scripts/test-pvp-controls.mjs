import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  PvpControls,
  loadFlightSettings,
  saveFlightSettings,
  PredictionHistory,
} from '../lib/pvp-controls.ts';
import { isEditable } from '../lib/controls.ts';
test('地面鍵盤回退沿用方向鍵、Q／F；表單不捕捉操作', () => {
  const c = new PvpControls();
  c.settings.mode = 'keyboard';
  c.enable();
  c.key('ArrowRight', true);
  c.key('KeyQ', true);
  c.key('KeyF', true);
  const f = c.frame(1 / 60, 16 / 9, 'ground');
  assert.deepEqual(f.look_delta, [1.5, 0]);
  assert.deepEqual(
    f.commands.map((c) => c.kind),
    ['toggle_aim', 'fire_down'],
  );
  c.key('KeyF', false);
  assert.equal(c.frame(1 / 60, 1, 'ground').commands[0].kind, 'fire_up');
  for (const tag of ['input', 'select', 'textarea'])
    assert.equal(
      isEditable({ closest: (s) => (s.includes(tag) ? {} : null) }),
      true,
    );
});
test('鍵盤雙向相抵、滑鼠靈敏度、取消及本機視角', () => {
  const c = new PvpControls();
  c.enable();
  c.settings.mode = 'keyboard';
  c.key('KeyW', true);
  c.key('KeyS', true);
  c.key('ArrowRight', true);
  c.key('KeyE', true);
  let f = c.frame(1 / 60, 16 / 9, 'air');
  assert.equal(f.throttle, 0);
  assert.equal(f.turn_x, 1);
  assert.equal(f.roll, 1);
  c.settings.mode = 'mouse';
  c.settings.sensitivity = 2;
  c.settings.invertY = true;
  c.mouse(10, 10);
  f = c.frame(1 / 60, 16 / 9, 'air');
  assert.deepEqual(f.look_delta, [2.4, -2.4]);
  assert.equal(f.turn_x, 0);
  c.key('KeyV', true);
  assert.equal(c.camera, 'cockpit');
  assert.equal(c.frame(1 / 60, 1, 'air').commands.length, 0);
  c.suspend();
  f = c.frame(1 / 60, 1, 'air');
  assert.equal(f.suspended, true);
  c.enable();
  assert.equal(c.frame(1 / 60, 1, 'air').throttle, 0);
});
test('保存偏好、壞值回退、儲存拒絕明示', () => {
  const values = new Map();
  const storage = {
    getItem: (k) => values.get(k) || null,
    setItem: (k, v) => values.set(k, v),
  };
  const settings = {
    version: 1,
    mode: 'keyboard',
    sensitivity: 2,
    invertY: true,
    camera: 'cockpit',
  };
  assert.equal(saveFlightSettings(storage, settings), '');
  assert.deepEqual(loadFlightSettings(storage).settings, settings);
  values.set('candy-defense-web:pvp-controls:v1', 'broken');
  assert.ok(loadFlightSettings(storage).error);
  assert.ok(
    saveFlightSettings(
      {
        setItem() {
          throw Error();
        },
      },
      settings,
    ),
  );
});
test('預測步號與控制包序號分開；120 步滿載與換代清空', () => {
  for (const fps of [30, 60, 144]) {
    const h = new PredictionHistory();
    let tick = 0,
      remainder = 0;
    for (let n = 0; n < fps; n++) {
      remainder += 1 / fps;
      while (remainder >= 1 / 120 - 1e-10) {
        remainder -= 1 / 120;
        assert.ok(
          h.push({
            runId: 'run',
            stream: 's',
            tick: ++tick,
            inputSeqAtCapture: 99,
            dt: 1 / 120,
            input: {},
          }),
        );
      }
    }
    assert.equal(tick, 120);
    assert.equal(h.push({ runId: 'run', stream: 's', tick: 121 }), false);
    const remaining = h.after(60, 's');
    assert.equal(remaining.length, 60);
    assert.equal(remaining[0].tick, 61);
    assert.equal(h.after(40, 's').length, 60);
    assert.equal(h.after(120, 's').length, 0);
    h.push({ runId: 'run', stream: 's', tick: 130 });
    h.push({ runId: 'run', stream: 'new', tick: 1 });
    assert.equal(h.after(0, 'new').length, 1);
  }
});
