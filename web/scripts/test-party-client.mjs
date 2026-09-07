import assert from 'node:assert/strict';
import { test } from 'node:test';
import { MultiplayerClient } from '../lib/multiplayer-client.ts';

test('commands survive a missed host poll; cumulative look recovers skipped packets', async () => {
  const sent = [];
  const transport = async (_url, options) => {
    const data = JSON.parse(options.body);
    sent.push(data);
    return Response.json({
      room: {
        id: 'room',
        hostId: 'host',
        status: 'playing',
        runId: 'round',
        members: [],
      },
    });
  };
  const client = new MultiplayerClient(
    () => {},
    () => {},
    transport,
  );
  client.me = { id: 'guest' };
  client.room = {
    id: 'room',
    hostId: 'host',
    status: 'playing',
    runId: 'round',
  };
  client.setInput({
    commands: [{ sequence: 1, kind: 'fire_down' }],
    look_delta: [4, 2],
  });
  await client.poll();
  client.setInput({
    commands: [{ sequence: 2, kind: 'fire_up' }],
    look_delta: [3, 1],
  });
  await client.poll();
  assert.deepEqual(
    sent[1].input.commands.map((c) => c.kind),
    ['fire_down', 'fire_up'],
  );
  assert.deepEqual(sent[1].input.look_total, [7, 3]);
  const predicted = client.predictView({
    yaw: 7,
    pitch: 3,
    input_stream: sent[1].input.stream,
    command_ack: 2,
    look_total_ack: [7, 3],
  });
  assert.equal(predicted.yaw, 7);
  assert.equal(predicted.pitch, 3);
  await client.poll();
  assert.deepEqual(sent[2].input.commands, []);
  client.setInput({
    commands: [{ sequence: 3, kind: 'fire_down' }],
    look_delta: [0, 0],
  });
  client.setInput({ suspended: true });
  await client.poll();
  assert.deepEqual(sent[3].input.commands, []);
  assert.equal(sent[3].input.suspended, true);
  client.dispose();
});

test('reconnecting client uses a newer input sequence', async () => {
  let sequence;
  const client = new MultiplayerClient(
    () => {},
    () => {},
    async (_url, options) => {
      sequence = JSON.parse(options.body).inputSeq;
      return Response.json({
        room: {
          id: 'room',
          status: 'playing',
          hostId: 'host',
          runId: 'round',
          members: [],
        },
      });
    },
  );
  client.me = { id: 'guest' };
  client.room = {
    id: 'room',
    status: 'playing',
    hostId: 'host',
    runId: 'round',
  };
  await client.poll();
  assert.ok(sequence > 1000000000000);
  client.dispose();
});
