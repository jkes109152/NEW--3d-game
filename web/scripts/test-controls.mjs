import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  BattleInput,
  validMode,
  KEY_ACTIONS,
  CONTROL_ROWS,
} from '../lib/controls.ts';

const kinds = (input) => input.frame(0.02).commands.map((c) => c.kind);
test('paused inputs cannot move, aim, jump or fire', () => {
  const input = new BattleInput();
  input.keyDown('KeyW');
  input.keyDown('KeyQ');
  input.fireDown('mouse');
  input.touchDown(1, 'move', 0, 0);
  input.touchMove(1, 45, -45);
  assert.deepEqual(input.frame(0.02), {
    commands: [],
    look_delta: [0, 0],
    move_x: 0,
    move_z: 0,
  });
});
test('keyboard edges ignore repeat; slot, jump, aim and reload are distinct', () => {
  const input = new BattleInput();
  input.start();
  kinds(input);
  for (const code of ['Space', 'KeyQ', 'KeyR', 'Digit3', 'KeyF']) {
    input.keyDown(code);
    input.keyDown(code, true);
  }
  assert.deepEqual(kinds(input), [
    'jump',
    'toggle_aim',
    'reload',
    'select_slot',
    'fire_down',
  ]);
  input.keyUp('KeyF');
  assert.deepEqual(kinds(input), ['fire_up']);
  assert.deepEqual(KEY_ACTIONS, {
    Space: 'jump',
    KeyR: 'reload',
    KeyQ: 'toggle_aim',
  });
  assert.ok(
    CONTROL_ROWS.find((row) => row.action === '射擊').desktop.includes('F'),
  );
});
test('movement chords cancel correctly and view keys use frame time', () => {
  const input = new BattleInput();
  input.start();
  kinds(input);
  input.keyDown('KeyW');
  input.keyDown('KeyS');
  input.keyDown('KeyD');
  input.keyDown('ArrowRight');
  input.keyDown('ArrowUp');
  assert.deepEqual(input.frame(0.1, 2), {
    commands: [],
    look_delta: [14, -14],
    move_x: 1,
    move_z: 0,
  });
  input.keyUp('KeyS');
  input.keyUp('KeyD');
  input.keyUp('ArrowRight');
  input.keyUp('ArrowUp');
  assert.deepEqual(input.frame(0.1), {
    commands: [],
    look_delta: [0, 0],
    move_x: 0,
    move_z: 1,
  });
});
test('releasing another button or keyboard source does not stop held mouse fire', () => {
  const input = new BattleInput();
  input.start();
  kinds(input);
  input.fireDown('mouse');
  input.fireDown('keyboard');
  input.fireUp('right-button');
  input.fireUp('keyboard');
  assert.deepEqual(kinds(input), ['fire_down']);
  assert.deepEqual([...input.fireSources], ['mouse']);
  input.fireUp('mouse');
  assert.deepEqual(kinds(input), ['fire_up']);
});
test('touch movement and look never fire and remain independent with third finger', () => {
  const input = new BattleInput();
  input.start();
  kinds(input);
  input.touchDown(10, 'move', 100, 200);
  input.touchDown(11, 'look', 300, 200);
  input.touchMove(10, 145, 155);
  input.touchMove(11, 320, 210);
  let frame = input.frame(0.02);
  assert.deepEqual(frame, {
    commands: [],
    look_delta: [3.2, 1.6],
    move_x: 1,
    move_z: 1,
  });
  input.fireDown('pointer:12');
  assert.deepEqual(kinds(input), ['fire_down']);
  input.releasePointer(11);
  frame = input.frame(0.02);
  assert.equal(frame.move_x, 1);
  assert.equal(input.fireSources.size, 1);
  input.releasePointer(10);
  assert.equal(input.frame(0.02).move_x, 0);
  assert.equal(input.fireSources.size, 1);
  input.releasePointer(12);
  assert.deepEqual(kinds(input), ['fire_up']);
});
test('extra touch cannot steal the current movement finger', () => {
  const input = new BattleInput();
  input.start();
  kinds(input);
  input.touchDown(1, 'move', 0, 0);
  input.touchMove(1, 45, 0);
  input.touchDown(2, 'move', 0, 0);
  input.touchMove(2, -45, 0);
  input.releasePointer(2);
  assert.equal(input.frame(0.02).move_x, 1);
  input.releasePointer(1);
  assert.equal(input.frame(0.02).move_x, 0);
});
test('pause clears held input and resume starts with a release barrier', () => {
  const input = new BattleInput();
  input.start();
  input.keyDown('KeyW');
  input.fireDown('mouse');
  input.touchDown(1, 'look', 0, 0);
  input.touchMove(1, 100, 50);
  input.clear();
  assert.deepEqual(input.frame(0.02), {
    commands: [],
    look_delta: [0, 0],
    move_x: 0,
    move_z: 0,
  });
  input.start();
  let frame = input.frame(0.02);
  assert.deepEqual(
    frame.commands.map((c) => c.kind),
    ['fire_up'],
  );
  assert.ok(frame.commands[0].sequence > 1);
  input.keyDown('KeyF', true);
  assert.deepEqual(kinds(input), []);
  input.keyUp('KeyF');
  input.keyDown('KeyF');
  assert.deepEqual(kinds(input), ['fire_down']);
});
test('preference control modes accept only supported values', () => {
  assert.ok(['mouse', 'keyboard', 'touch'].every(validMode));
  assert.ok([null, undefined, 'auto', 1, {}].every((v) => !validMode(v)));
});
