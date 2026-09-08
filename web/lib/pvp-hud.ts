import type { PvpView } from './pvp-types.ts';
export function pvpGroundHud(view: PvpView) {
  const me = view.actors.find((a) => a.id === view.selfId);
  if (!me || me.team !== 'ground' || !me.alive || view.phase !== 'active')
    return null;
  const locked =
    view.lock_valid.length > 0 &&
    view.lock_valid.every((id) => (view.locks[id] || 0) >= 1 - 1e-9);
  return {
    phase: view.phase,
    attempt_id: view.runId,
    active_weapon_id: 'W01',
    weapon_category: 'anti_air',
    fire_mode: 'lock_single',
    lock_box_scale: 1,
    aiming: me.aiming,
    locks: view.locks,
    lock_current: view.lock_current,
    lock_valid: view.lock_valid,
    elapsed: view.elapsed,
    fire_blocked:
      !me.aiming || !locked ? 'lock' : view.cooldown > 1e-9 ? 'cooldown' : null,
    cooldown: view.cooldown,
    cooldown_seconds: 1.25,
    events: view.events.filter((e) => e.player_id === me.id),
    aircraft: view.actors
      .filter((a) => a.team === 'air')
      .map((a) => ({ ...a, status: a.alive ? 'approaching' : 'destroyed' })),
  };
}
