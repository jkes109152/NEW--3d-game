'use client';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { CONTROL_MODES, ControlMode } from '@/lib/controls';
export function BattlePanel({
  b,
  c,
  p,
  controls,
  runtime,
  onHelp,
  onEnd,
}: any) {
  const paused = b.phase !== 'active',
    aa = b.weapon_category === 'anti_air',
    scoped = b.weapon_category === 'sniper' && b.aiming,
    rt = b.weapon_runtime[b.active_weapon_id];
  const status = paused
    ? '已暫停'
    : rt.reload_finish_at
      ? `換彈中 · ${b.reload_remaining.toFixed(1)} 秒`
      : rt.quota_remaining === 0 || rt.magazine_rounds === 0
        ? '彈藥已用完'
        : b.cooldown_remaining > 0.001
          ? `${b.fire_mode === 'bolt' ? '上膛中' : '冷卻中'} · ${b.cooldown_remaining.toFixed(1)} 秒`
          : aa
            ? b.lock_ready && !b.fire_blocked
              ? b.fire_mode === 'lock_multi'
                ? '可齊射'
                : '可發射'
              : !b.aiming
                ? '先切換瞄準'
                : !b.lock_valid.length
                  ? '將敵機保持在方框中'
                  : `鎖定中 ${Math.floor(b.lock_progress * 100)}%`
            : '可以射擊';
  const mode = controls?.mode || 'mouse';
  const touchZone = (role: 'move' | 'look') => ({
    onPointerDown: (e: any) => {
      if (e.pointerType !== 'touch') return;
      e.preventDefault();
      e.currentTarget.setPointerCapture(e.pointerId);
      runtime.current.touchStart(e.pointerId, role, e.clientX, e.clientY);
    },
    onPointerMove: (e: any) =>
      runtime.current.touchMove(e.pointerId, e.clientX, e.clientY),
    onPointerUp: (e: any) => runtime.current.releasePointer(e.pointerId),
    onPointerCancel: (e: any) => runtime.current.releasePointer(e.pointerId),
    onLostPointerCapture: (e: any) =>
      runtime.current.releasePointer(e.pointerId),
  });
  return (
    <>
      {b.cooperative && (
        <div className="party-team-hud" aria-label="合作隊伍">
          {b.players?.map((ally: any) => (
            <span key={ally.id}>
              {ally.name}
              {ally.id === b.self_id ? '（你）' : ''} ·{' '}
              {ally.hp > 0 ? `${Math.ceil(ally.hp)} 生命` : '已倒下'}
            </span>
          ))}
        </div>
      )}
      <div className="hud">
        <div>
          <span>
            關卡 {b.level} · {b.elapsed.toFixed(1)} 秒
          </span>
          <strong>
            生命 {Math.ceil(b.player.hp)} / {b.player.max_hp}
          </strong>
          <meter
            aria-label="生命"
            min={0}
            max={b.player.max_hp}
            value={b.player.hp}
          />
        </div>
        <div>
          <strong>
            {b.aircraft.filter((a: any) => a.hp > 0).length} 架敵機 ·{' '}
            {b.enemies.length} 名敵兵
          </strong>
          <span>
            城市 {Math.ceil(b.city_hp)}% ·{' '}
            {c.armors[b.player.armor_id]?.name || '無裝甲'}
          </span>
        </div>
      </div>
      {!aa && (
        <div
          aria-hidden="true"
          className={`reticle ${scoped ? 'scope-frame' : 'crosshair'}`}
        >
          <i />
        </div>
      )}
      <div className="weapon-status" role="status">
        <strong>{c.weapons[b.active_weapon_id].name}</strong>
        <span>
          {c.modes[b.fire_mode]} · {status}
        </span>
        {aa && (
          <div className="aa-weapon-cooldown">
            <span>
              武器冷卻{' '}
              <strong>
                {b.cooldown_remaining > 0.001
                  ? `${b.cooldown_remaining.toFixed(2)} 秒`
                  : '就緒'}
              </strong>
            </span>
            <div>
              <i
                style={{
                  width: `${Math.min(100, (100 * b.cooldown_remaining) / b.cooldown_seconds)}%`,
                }}
              />
            </div>
          </div>
        )}
        <span>
          {rt.magazine_rounds === null
            ? '無彈匣限制'
            : `彈匣 ${rt.magazine_rounds} / ${b.magazine_capacity}`}{' '}
          ·{' '}
          {rt.quota_remaining === null
            ? '備彈無限'
            : `本關剩餘 ${rt.quota_remaining} 發`}
        </span>
      </div>
      <div className="weaponbar" aria-label="武器槽">
        {b.weapon_slots.map((id: string, i: number) => (
          <Button
            key={i}
            aria-pressed={b.active_weapon_id === id}
            disabled={!id || paused}
            className={b.active_weapon_id === id ? 'selected' : ''}
            onClick={() => runtime.current.command('select_slot', i + 1)}
          >
            <small>{i + 1}</small>
            {c.weapons[id]?.name || '空槽'}
          </Button>
        ))}
      </div>
      {!paused && mode !== 'mouse' && (
        <div className="battle-actions">
          <Button onClick={() => runtime.current.pause()}>暫停</Button>
          <Button onClick={onHelp}>遊玩方法</Button>
        </div>
      )}
      {!paused && mode !== 'touch' && (
        <div className="battle-hint">
          {mode === 'mouse' ? '滑鼠控制視角' : '方向鍵控制視角'} · WASD 移動 ·
          左鍵 / F 射擊 · 右鍵 / Q 瞄準 · R 換彈 · Space 跳躍 · Esc 暫停 · H
          說明
        </div>
      )}
      {!paused && mode === 'touch' && (
        <div className="touch-layer">
          <div
            className="touch-zone move-zone"
            aria-label="移動區"
            {...touchZone('move')}
          >
            <span>移動</span>
          </div>
          <div
            className="touch-zone look-zone"
            aria-label="視角區"
            {...touchZone('look')}
          >
            <span>視角</span>
          </div>
          <div className="touch-buttons">
            <Button
              className="fire-button"
              onPointerDown={(e) => {
                e.preventDefault();
                e.currentTarget.setPointerCapture(e.pointerId);
                runtime.current.fireDown(e.pointerId);
              }}
              onPointerUp={(e) => runtime.current.releasePointer(e.pointerId)}
              onPointerCancel={(e) =>
                runtime.current.releasePointer(e.pointerId)
              }
              onLostPointerCapture={(e) =>
                runtime.current.releasePointer(e.pointerId)
              }
            >
              射擊
            </Button>
            <Button
              aria-pressed={b.aiming}
              onClick={() => runtime.current.command('toggle_aim')}
            >
              瞄準
            </Button>
            <Button onClick={() => runtime.current.command('reload')}>
              換彈
            </Button>
            <Button onClick={() => runtime.current.command('jump')}>
              跳躍
            </Button>
          </div>
        </div>
      )}
      {paused && (
        <section className="panel ready-panel" aria-label="戰鬥就緒與暫停">
          <span className="eyebrow">
            關卡 {b.level} ·{' '}
            {b.cooperative && !b.host_paused
              ? '個人操作暫停，戰鬥仍持續'
              : '時間已停止'}
          </span>
          <h1>
            {controls?.pauseReason === 'ready' ? '防線準備就緒' : '防線已暫停'}
          </h1>
          {controls?.pauseReason === 'capture_failed' ? (
            <p role="alert">
              瀏覽器未能鎖定滑鼠。可再試一次，或改選「鍵盤視角」繼續遊玩。
            </p>
          ) : (
            <p>
              {mode === 'mouse'
                ? '開始後將鎖定滑鼠，以滑鼠移動視角。按 Esc 可隨時釋放游標。'
                : mode === 'keyboard'
                  ? '使用 WASD 移動、方向鍵控制視角、F 射擊、Q 瞄準。'
                  : '左側拖曳移動、右側拖曳視角，使用畫面按鈕射擊與瞄準。'}
            </p>
          )}
          <label className="choice">
            <span>操作方式</span>
            <Select
              value={mode}
              onValueChange={(v) => runtime.current.setMode(v as ControlMode)}
            >
              <SelectTrigger aria-label="操作方式">
                <SelectValue>
                  {CONTROL_MODES.find(([id]) => id === mode)?.[1]}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {CONTROL_MODES.map(([id, name]) => (
                  <SelectItem key={id} value={id}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <label className="sensitivity">
            <span>視角靈敏度 {controls?.sensitivity?.toFixed(1)}×</span>
            <Slider
              aria-label="視角靈敏度"
              min={0.2}
              max={3}
              step={0.1}
              value={[controls?.sensitivity || 1]}
              onValueChange={(v) =>
                runtime.current.setSensitivity(Array.isArray(v) ? v[0] : v)
              }
            />
          </label>
          <div className="ready-buttons">
            <Button
              className="primary"
              disabled={controls?.requesting}
              onClick={() => runtime.current.begin()}
            >
              {controls?.requesting
                ? '正在取得滑鼠控制…'
                : controls?.pauseReason === 'ready'
                  ? '開始遊玩'
                  : '繼續遊玩'}
            </Button>
            <Button className="secondary" onClick={onHelp}>
              遊玩方法
            </Button>
            <Button className="secondary" onClick={onEnd}>
              結束本局，返回主選單
            </Button>
          </div>
          <p className="muted">
            {b.cooperative
              ? '離開會退出房間；房主離開時房間關閉。請保持網路連線。'
              : '主動結束本局不發放獎勵，下一次從 1-1 開始。'}
          </p>
        </section>
      )}
    </>
  );
}
