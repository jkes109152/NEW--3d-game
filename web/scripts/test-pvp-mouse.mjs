import { test } from 'node:test';
import assert from 'node:assert/strict';
import { bindPvpMouse } from '../lib/pvp-mouse.ts';
import { PvpControls } from '../lib/pvp-controls.ts';
function setup() {
  const canvas = new EventTarget(),
    doc = new EventTarget(),
    win = new EventTarget(),
    c = new PvpControls();
  doc.pointerLockElement = canvas;
  c.enable();
  let ground = true;
  const dispose = bindPvpMouse(canvas, c, () => ground, doc, win);
  const send = (target, type, button = 2) => {
    const e = new Event(type, { cancelable: true });
    Object.defineProperty(e, 'button', { value: button });
    target.dispatchEvent(e);
    return e;
  };
  return {
    canvas,
    doc,
    win,
    c,
    dispose,
    send,
    air: () => (ground = false),
    commands: () => c.frame(0.016, 1, 'ground').commands.map((c) => c.kind),
  };
}
test('右鍵在指標按下階段攔截，完整滑鼠事件序列只瞄準一次且保持控制', () => {
  const s = setup();
  assert.ok(s.send(s.doc, 'pointerdown').defaultPrevented);
  assert.ok(s.send(s.doc, 'mousedown').defaultPrevented);
  assert.ok(s.send(s.doc, 'contextmenu').defaultPrevented);
  s.send(s.win, 'mouseup');
  assert.ok(s.send(s.doc, 'auxclick').defaultPrevented);
  assert.deepEqual(s.commands(), ['toggle_aim']);
  assert.equal(s.c.enabled, true);
  assert.equal(s.doc.pointerLockElement, s.canvas);
  s.send(s.doc, 'pointerdown');
  s.send(s.doc, 'mousedown');
  s.send(s.win, 'mouseup');
  assert.deepEqual(s.commands(), ['toggle_aim']);
  s.dispose();
});
test('按住左鍵再點右鍵仍可瞄準，右鍵放開不停止射擊', () => {
  const s = setup();
  s.send(s.doc, 'mousedown', 0);
  s.send(s.doc, 'mousedown', 2);
  s.send(s.win, 'mouseup', 2);
  assert.deepEqual(s.commands(), ['fire_down', 'toggle_aim']);
  s.send(s.win, 'mouseup', 0);
  assert.deepEqual(s.commands(), ['fire_up']);
  s.dispose();
});
test('空中不發地面指令，暫停／其他元素及移除監聽後不攔截選單', () => {
  const s = setup();
  s.air();
  s.send(s.doc, 'pointerdown');
  s.send(s.doc, 'mousedown', 0);
  assert.deepEqual(s.commands(), []);
  s.c.suspend();
  assert.equal(s.send(s.doc, 'contextmenu').defaultPrevented, false);
  s.c.enable();
  s.doc.pointerLockElement = null;
  assert.equal(s.send(s.doc, 'contextmenu').defaultPrevented, false);
  s.doc.pointerLockElement = s.canvas;
  s.dispose();
  assert.equal(s.send(s.doc, 'contextmenu').defaultPrevented, false);
  s.send(s.doc, 'mousedown');
  assert.deepEqual(s.commands(), []);
});
test('失焦後重新取得控制，右鍵不會殘留為按住狀態', () => {
  const s = setup();
  s.send(s.doc, 'pointerdown');
  s.commands();
  s.send(s.win, 'blur');
  s.c.suspend();
  s.c.enable();
  s.send(s.doc, 'pointerdown');
  assert.deepEqual(s.commands(), ['toggle_aim']);
  s.dispose();
});

test('預設滑鼠事件被取消時，pointerup 仍重設右鍵供下一次瞄準', () => {
  const s = setup();
  s.send(s.doc, 'pointerdown');
  s.send(s.doc, 'pointerup');
  s.send(s.doc, 'pointerdown');
  s.send(s.doc, 'pointerup');
  assert.deepEqual(s.commands(), ['toggle_aim', 'toggle_aim']);
  s.dispose();
});
