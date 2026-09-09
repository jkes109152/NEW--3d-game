// 只平滑呈現遠端角色；不參與鎖定、命中或勝負判定。
export function playbackFraction(gapMs: number, sinceReceivedMs: number) {
  if (!Number.isFinite(gapMs) || gapMs <= 0) return 1;
  const bufferMs = Math.min(100, gapMs);
  const offsetMs = Math.min(200, Math.max(0, sinceReceivedMs) - bufferMs);
  return Math.max(0, 1 + offsetMs / gapMs);
}
