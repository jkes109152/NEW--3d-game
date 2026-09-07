export function registerGameTools(
  getState: () => any,
  send: (action: string) => any,
) {
  const context = (document as any).modelContext,
    lifecycle = new AbortController();
  if (context?.registerTool) {
    const tools = [
      {
        name: 'read_defense_status',
        title: '讀取防守狀態',
        description:
          '唯讀取得選單、關卡進度、戰鬥時間、操作方式、位置視角、武器及鎖定狀態。',
        annotations: { readOnlyHint: true, untrustedContentHint: false },
        execute: () => {
          const s = getState(),
            b = s.battle;
          return {
            screen: s.screen,
            cursor: s.cursor,
            phase: b?.phase,
            level: b?.level,
            elapsed: b?.elapsed,
            hp: b?.player.hp,
            position: b?.player.position,
            yaw: b?.yaw,
            pitch: b?.pitch,
            controls: s.controls,
            aiming: b?.aiming,
            weaponSlots: b?.weapon_slots,
            activeWeapon: b?.active_weapon_id,
            ammo: b?.weapon_runtime?.[b?.active_weapon_id],
            lockReady: b?.lock_ready,
            lockProgress: b?.lock_progress,
            validTargets: b?.lock_valid,
          };
        },
      },
      {
        name: 'pause_defense_battle',
        title: '暫停防守',
        description: '暫停正在進行的防守戰鬥，顯示暫停選單。',
        annotations: { readOnlyHint: false, untrustedContentHint: false },
        execute: () => {
          if (getState().battle?.phase !== 'active')
            throw Error('目前沒有進行中的戰鬥');
          const s = send('pause');
          return { phase: s.battle.phase };
        },
      },
    ];
    for (const tool of tools)
      try {
        Promise.resolve(
          context.registerTool(
            {
              ...tool,
              inputSchema: {
                type: 'object',
                properties: {},
                additionalProperties: false,
              },
              execute: (input: unknown) => {
                if (
                  !input ||
                  typeof input !== 'object' ||
                  Array.isArray(input) ||
                  Object.keys(input).length
                )
                  throw Error('輸入必須是空物件');
                return tool.execute();
              },
            },
            { signal: lifecycle.signal },
          ),
        ).catch(() => {});
      } catch {}
  }
  return () => lifecycle.abort();
}
