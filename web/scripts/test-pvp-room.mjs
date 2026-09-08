import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  pvpTimeLimit,
  splitPvpTeams,
  roomCapacity,
  partyMultiplier,
} from '../lib/multiplayer-rules.ts';
test('七種時限與合作容量分開', () => {
  assert.deepEqual(
    Array.from({ length: 7 }, (_, i) => pvpTimeLimit(i + 2)),
    [180, 300, 210, 330, 240, 390, 270],
  );
  assert.equal(roomCapacity('pvp'), 8);
  assert.equal(roomCapacity('coop'), 4);
  assert.equal(roomCapacity(undefined), 4);
  for (const n of [1, 9, 2.5, NaN]) assert.throws(() => pvpTimeLimit(n));
  assert.throws(() => partyMultiplier(5));
});
test('每局等機率抽選，不固定偏向房主', () => {
  for (let n = 2; n <= 8; n++) {
    const roster = Array.from({ length: n }, (_, i) => ({
      id: String(i),
      name: '玩家' + i,
    }));
    const draws = splitPvpTeams(roster, () => 0.999999);
    assert.equal(
      draws.filter((x) => x.team === 'air').length,
      Math.ceil(n / 2),
    );
    assert.equal(new Set(draws.map((x) => x.id)).size, n);
    assert.ok(roster.every((x) => !('team' in x)));
  }
  const counts = [0, 0, 0];
  // 枚舉 Fisher–Yates 的 3×2 種抽法，不用機率性易失敗測試。
  for (let a = 0; a < 3; a++)
    for (let b = 0; b < 2; b++) {
      const values = [(a + 0.5) / 3, (b + 0.5) / 2];
      splitPvpTeams(
        counts.map((_, i) => ({ id: String(i), name: '玩家' })),
        () => values.shift(),
      ).forEach((p) => {
        if (p.team === 'ground') counts[+p.id]++;
      });
    }
  assert.deepEqual(counts, [2, 2, 2]);
});
