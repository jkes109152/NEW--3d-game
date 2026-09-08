export const MAX_PLAYERS = 4;
export const roomCapacity = (mode?: string) =>
  mode === 'pvp' ? 8 : MAX_PLAYERS;
export function pvpTimeLimit(count: number) {
  const times: Record<number, number> = {
    2: 180,
    3: 300,
    4: 210,
    5: 330,
    6: 240,
    7: 390,
    8: 270,
  };
  if (!Number.isInteger(count) || !times[count])
    throw Error('空地對戰需要 2 至 8 人');
  return times[count];
}
export function splitPvpTeams<T extends { id: string; name: string }>(
  players: T[],
  random: () => number = Math.random,
) {
  pvpTimeLimit(players.length);
  const shuffled = players.map((p) => ({ id: p.id, name: p.name }));
  for (let i = shuffled.length - 1; i > 0; i--) {
    const value = random();
    if (!Number.isFinite(value) || value < 0 || value >= 1)
      throw Error('分隊亂數無效');
    const j = Math.floor(value * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled.map((p, i) => ({
    ...p,
    team:
      i < Math.ceil(players.length / 2)
        ? ('air' as const)
        : ('ground' as const),
  }));
}
export function partyMultiplier(count: number) {
  if (!Number.isInteger(count) || count < 1 || count > MAX_PLAYERS)
    throw Error('房間人數無效');
  return 1.5 ** (count - 1);
}
export function soloReward(
  a: number,
  b: number,
  campaign: number,
  rebirth: number,
) {
  const bosses = a === campaign ? Math.max(0, b - a - 1) : 0;
  return Math.floor(
    (100 + 25 * a + 10 * (b - 1) + 150 * bosses) * (1 + 0.5 * rebirth),
  );
}
export function personalReward(
  a: number,
  b: number,
  campaign: number,
  rebirth: number,
  count: number,
) {
  return Math.floor(
    soloReward(a, b, campaign, rebirth) * partyMultiplier(count),
  );
}
export function cleanName(value: unknown) {
  if (typeof value !== 'string') throw Error('請輸入名稱');
  const name = value.normalize('NFKC').trim();
  if ([...name].length < 1 || [...name].length > 20 || /[\p{C}<>]/u.test(name))
    throw Error('名稱需為 1 至 20 個字，且不可包含控制字元或角括號');
  return name;
}
export function publicLoadout(profile: any) {
  if (
    !profile ||
    typeof profile !== 'object' ||
    !/^[a-f0-9]{32}$/.test(profile.profile_id) ||
    !Number.isInteger(profile.rebirth_count) ||
    profile.rebirth_count < 0 ||
    profile.rebirth_count > 100 ||
    !profile.confirmed_loadout ||
    !profile.owned_weapons ||
    !Array.isArray(profile.owned_turrets)
  )
    throw Error('裝備資料無效，請重新選擇存檔');
  const copy = {
    ...profile,
    coins: 0,
    profile_revision: 0,
    operation_history: [],
    last_completed_a_b: null,
  };
  if (JSON.stringify(copy).length > 64000) throw Error('裝備資料超過房間限制');
  return copy;
}
