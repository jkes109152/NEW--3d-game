import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MultiplayerClient } from '../lib/multiplayer-client.ts';
test('加入房間不可保留大廳兩秒排程', () => {
  const set = globalThis.setTimeout,
    clear = globalThis.clearTimeout,
    delays = [];
  globalThis.setTimeout = (_fn, ms) => {
    delays.push(ms);
    return delays.length;
  };
  globalThis.clearTimeout = () => {};
  try {
    const c = new MultiplayerClient(
      () => {},
      () => {},
    );
    c.open = true;
    c.schedule();
    c.accept({ mode: 'pvp', status: 'waiting' });
    assert.deepEqual(delays, [2000, 800]);
    c.dispose();
  } finally {
    globalThis.setTimeout = set;
    globalThis.clearTimeout = clear;
  }
});
test('倒數轉換立即取代等待室慢速排程', () => {
  const oldSet = globalThis.setTimeout,
    oldClear = globalThis.clearTimeout,
    delays = [];
  globalThis.setTimeout = (_fn, delay) => {
    delays.push(delay);
    return delays.length;
  };
  globalThis.clearTimeout = () => {};
  try {
    const c = new MultiplayerClient(
      () => {},
      () => {},
    );
    c.open = true;
    c.room = { mode: 'pvp', status: 'waiting' };
    c.schedule();
    c.accept({ mode: 'pvp', status: 'countdown', runId: 'new' });
    assert.deepEqual(delays, [800, 50]);
    c.dispose();
  } finally {
    globalThis.setTimeout = oldSet;
    globalThis.clearTimeout = oldClear;
  }
});
test('大廳輪詢即時發布新增房間', async () => {
  let changed = 0;
  const c = new MultiplayerClient(
    () => changed++,
    () => {},
    async () =>
      Response.json({
        me: { id: 'p' },
        rooms: [{ id: 'new' }],
        roomId: null,
        receipts: [],
      }),
  );
  c.open = true;
  await c.poll();
  assert.equal(c.rooms[0].id, 'new');
  assert.ok(changed > 0);
  c.dispose();
});
test('首次 sync/resume 串流取得與過時分頁停止搶回', async () => {
  const actions = [];
  let instance = null,
    stream = 'initial';
  const room = () => ({
    id: 'room',
    mode: 'pvp',
    status: 'countdown',
    runId: 'run',
    hostId: 'host',
    currentStream: stream,
    inputInstance: instance,
    roster: [],
    members: [],
  });
  const client = new MultiplayerClient(
    () => {},
    () => {},
    async (_url, options) => {
      const d = JSON.parse(options.body);
      actions.push(d);
      if (d.action === 'resume') {
        instance = d.instanceId;
        stream = 'bound';
      }
      if (d.action === 'exchange' && d.inputStream !== stream)
        return Response.json({ error: '另一分頁已取得控制' }, { status: 409 });
      return Response.json({ room: room() });
    },
  );
  client.me = { id: 'guest' };
  client.room = room();
  await client.poll();
  assert.deepEqual(
    actions.map((a) => a.action),
    ['sync', 'resume', 'exchange'],
  );
  client.setInput({
    suspended: false,
    look_delta: [8, 9],
    commands: [{ sequence: 1, kind: 'fire_down' }],
  });
  await client.poll();
  await client.poll();
  assert.equal(actions.at(-1).input.commands.length, 1);
  assert.deepEqual(actions.at(-1).input.look_total, [8, 9]);
  client.setInput({ suspended: true });
  await client.poll();
  assert.equal(actions.at(-1).input.cancelThrough, 1);
  assert.deepEqual(actions.at(-1).input.look_total, [8, 9]);
  const seq = actions.at(-1).inputSeq;
  client.accept({
    ...room(),
    view: {
      inputAck: {
        stream: 'bound',
        input_seq: seq,
        command_seq: 1,
        look_total: [8, 9],
      },
    },
  });
  client.setInput({ suspended: false, look_delta: [1, 0], commands: [] });
  await client.poll();
  assert.equal(actions.at(-1).input.commands.length, 0);
  assert.deepEqual(actions.at(-1).input.look_total, [9, 9]);
  stream = 'other';
  await assert.rejects(client.poll());
  const length = actions.length;
  await client.poll();
  assert.equal(actions.length, length);
  assert.equal(client.pvpControlState().evicted, true);
  client.dispose();
});
test('新局隔離舊輸入與佇列滿載取消確認', async () => {
  const c = new MultiplayerClient(
    () => {},
    () => {},
  );
  c.me = { id: 'p' };
  const room = {
    id: 'r',
    mode: 'pvp',
    runId: 'one',
    status: 'playing',
    inputInstance: c.instanceId,
    currentStream: 's',
  };
  c.accept(room);
  c.setInput({
    suspended: false,
    look_delta: [5, 2],
    commands: Array.from({ length: 96 }, (_, i) => ({
      sequence: i + 1,
      kind: 'fire_down',
    })),
  });
  c.setInput({ suspended: false, look_delta: [1, 1], commands: [] });
  assert.equal(c.pvpControlState().waiting, true);
  assert.equal(c.pvpControlState().input.commands.length, 0);
  assert.equal(c.pvpControlState().input.cancelThrough, 96);
  c.accept({ ...room, runId: 'two', currentStream: 'new' });
  assert.equal(c.pvpControlState().waiting, false);
  assert.deepEqual(c.pvpControlState().input.look_total, [0, 0]);
  assert.equal(c.pvpControlState().input.suspended, true);
  c.dispose();
});

test('慢連線完成後立即交換最新操作，不疊加輪詢等待且不並送', async () => {
  const oldSet = globalThis.setTimeout,
    oldClear = globalThis.clearTimeout;
  const callbacks = [],
    delays = [];
  globalThis.setTimeout = (fn, ms) => {
    callbacks.push(fn);
    delays.push(ms);
    return callbacks.length;
  };
  globalThis.clearTimeout = () => {};
  try {
    let now = 0,
      active = 0,
      peak = 0;
    const c = new MultiplayerClient(
      () => {},
      () => {},
      undefined,
      () => now,
    );
    c.open = true;
    c.room = { mode: 'pvp', status: 'playing', runId: 'run' };
    c.poll = async () => {
      peak = Math.max(peak, ++active);
      now += 200;
      c.accept(c.room);
      active--;
    };
    c.schedule();
    await callbacks.shift()();
    assert.deepEqual(delays, [50, 0]);
    assert.equal(peak, 1);
    c.poll = async () => {
      throw Error('測試斷線');
    };
    await callbacks.shift()();
    assert.equal(delays.at(-1), 800, '失敗時退避，不能空轉重試');
    c.dispose();
  } finally {
    globalThis.setTimeout = oldSet;
    globalThis.clearTimeout = oldClear;
  }
});

test('快連線以五十毫秒週期交換，不把往返時間額外加上去', async () => {
  const oldSet = globalThis.setTimeout,
    oldClear = globalThis.clearTimeout;
  const callbacks = [],
    delays = [];
  globalThis.setTimeout = (fn, ms) => {
    callbacks.push(fn);
    delays.push(ms);
    return callbacks.length;
  };
  globalThis.clearTimeout = () => {};
  try {
    let now = 0;
    const c = new MultiplayerClient(
      () => {},
      () => {},
      undefined,
      () => now,
    );
    c.open = true;
    c.room = { status: 'playing' };
    c.poll = async () => {
      now += 20;
      c.accept(c.room);
    };
    c.schedule();
    await callbacks.shift()();
    assert.deepEqual(delays, [50, 30]);
    c.dispose();
  } finally {
    globalThis.setTimeout = oldSet;
    globalThis.clearTimeout = oldClear;
  }
});
