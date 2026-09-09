import { test } from 'node:test';
import assert from 'node:assert/strict';
import { playbackFraction } from '../lib/pvp-playback.ts';
test('遠端快照僅保留百毫秒緩衝，不因慢網路額外落後整包', () => {
  assert.equal(playbackFraction(500, 0), 0.8);
  assert.equal(playbackFraction(500, 100), 1);
  assert.equal(playbackFraction(500, 300), 1.4);
  assert.equal(playbackFraction(500, 5000), 1.4, '最多外推兩百毫秒');
  assert.equal(playbackFraction(50, 0), 0);
  assert.equal(playbackFraction(50, 50), 1);
  assert.equal(playbackFraction(0, 0), 1);
});
