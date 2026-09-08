'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Settings,
  Plane,
  Crosshair,
  Heart,
  AlertTriangle,
  Eye,
  DoorOpen,
} from 'lucide-react';
const reasonText: Record<string, string> = {
  air_eliminated: '所有飛機已淘汰',
  timeout: '防守時間結束，仍有飛機存活',
  ground_departed: '地面部隊全員退出',
  missile: '遭導彈擊落',
  crash: '飛機撞毀',
  boundary: '越界逾時',
  departed: '已退出',
  all_departed: '雙方全員退出',
  host_reload: '房主重新載入遊戲',
  host_timeout: '房主連線中斷',
  host_left: '房主離開對戰',
  simulation_gap: '房主模擬中斷',
  simulation_error: '戰場無法繼續',
};
const time = (n: number) =>
  `${Math.floor(Math.max(0, Math.ceil(n)) / 60)
    .toString()
    .padStart(
      2,
      '0',
    )}：${(Math.max(0, Math.ceil(n)) % 60).toString().padStart(2, '0')}`;
export function PvpPanel({ pvp, runtime, party }: any) {
  const [tab, setTab] = useState('flight'),
    [page, setPage] = useState(0);
  const r = pvp.room,
    v = pvp.view,
    me = v?.actors.find((a: any) => a.id === party.me?.id),
    team = me?.team || r.roster?.find((p: any) => p.id === party.me?.id)?.team;
  const air = team === 'air',
    host = r.hostId === party.me?.id,
    result = r.result;
  const action = (kind: string, value: any = {}) =>
    runtime.current?.pvpAction(kind, value);
  const leave = () => void runtime.current?.partyAction('leave');
  const teammates = v?.actors.filter((a: any) => a.team === team) || [];
  const alive =
    v?.actors.filter((a: any) => a.team === 'air' && a.alive).length ??
    Math.ceil(r.roster.length / 2);
  const setting = (value: any) => action('configure', value);
  const settings = pvp.settings;
  return (
    <div className={`pvp-layer ${air ? 'pvp-air' : 'pvp-ground'}`}>
      <div className="pvp-status" role="status">
        <span>
          {air ? <Plane size={20} /> : <Crosshair size={20} />}{' '}
          {air ? '空中部隊' : '地面部隊'}
        </span>
        <strong>
          {r.status === 'countdown'
            ? `即將開始 ${pvp.countdown}`
            : time(v?.remainingSeconds || 0)}
        </strong>
        <span>
          存活飛機 {alive}／{Math.ceil(r.roster.length / 2)}
        </span>
      </div>
      {!result && r.status === 'playing' && me?.alive && (
        <>
          <div className="pvp-threat" aria-live="polite">
            {v?.threats.missile && (
              <strong>
                <AlertTriangle size={20} /> 導彈來襲
              </strong>
            )}
            {v?.threats.locked ? (
              <span>已被鎖定</span>
            ) : (
              v?.threats.tracking && <span>正在被鎖定</span>
            )}
            {me.outside > 0 && (
              <strong>
                已越界 · {Math.max(0, 5 - me.outside).toFixed(1)} 秒內返回
              </strong>
            )}
          </div>
          <aside className="pvp-team">
            <strong>隊友狀態</strong>
            {teammates.map((a: any) => (
              <div key={a.id}>
                <span title={a.name}>
                  {a.name}
                  {a.id === me.id ? '（你）' : ''}
                </span>
                <small>
                  {a.alive
                    ? '存活'
                    : reasonText[a.eliminationReason] || '已淘汰'}
                </small>
              </div>
            ))}
          </aside>
          <aside className="pvp-instruments">
            {air ? (
              <>
                <div>
                  <span>速度</span>
                  <strong>
                    {me.speed.toFixed(0)} <small>公尺／秒</small>
                  </strong>
                </div>
                <div>
                  <span>高度</span>
                  <strong>
                    {me.position[1].toFixed(0)} <small>公尺</small>
                  </strong>
                </div>
                <div aria-label={`耐久 ${me.hp}／2`}>
                  <Heart size={18} /> 耐久 {me.hp}／2
                </div>
              </>
            ) : (
              <>
                <strong>雲哨防空炮</strong>
                <span>基礎 · 未改裝</span>
                <div>
                  {v.cooldown > 0
                    ? `冷卻 ${v.cooldown.toFixed(1)} 秒`
                    : '武器已就緒'}
                </div>
              </>
            )}
          </aside>
        </>
      )}
      {!result && r.status === 'playing' && !me?.alive && (
        <div className="pvp-spectating">
          <Eye size={20} />
          <span>
            {pvp.spectator
              ? `觀戰：${v?.actors.find((a: any) => a.id === pvp.spectator)?.name}`
              : '等待共同結果'}
          </span>
          <Button onClick={() => action('spectate')}>切換隊友</Button>
        </div>
      )}
      {!result && r.status === 'playing' && (
        <div className="pvp-shortcuts">
          <span>
            {air
              ? 'W／S 加減速 · Q／E 翻滾 · V 視角'
              : settings.mode === 'keyboard'
                ? 'W／A／S／D 移動 · 方向鍵視角 · Q 瞄準 · F 發射 · 空白鍵跳躍'
                : 'W／A／S／D 移動 · 空白鍵跳躍 · 右鍵瞄準 · 左鍵發射'}
          </span>
          <Button className="secondary" onClick={() => action('settings')}>
            <Settings size={18} /> 設定
          </Button>
        </div>
      )}
      {(pvp.error || party.error) && (
        <p className="pvp-error" role="alert">
          {pvp.error || party.error}
        </p>
      )}
      {result ? (
        <section className="pvp-card">
          <span className="eyebrow">空地對戰 · 對戰結果</span>
          <h1>
            {result.winner === null
              ? '對戰中止'
              : result.winner === 'ground'
                ? '地面部隊獲勝'
                : '空中部隊獲勝'}
          </h1>
          <p>
            {reasonText[result.reason] || '本局已結束'}
            。本模式不發金幣，單人進度不變。
          </p>
          <div className="pvp-results">
            {result.players.slice(page * 4, page * 4 + 4).map((p: any) => (
              <div key={p.id}>
                <strong title={p.name}>{p.name}</strong>
                <span>{p.team === 'air' ? '空中' : '地面'}</span>
                <span>
                  {p.team === 'ground'
                    ? `擊落 ${p.kills} 架`
                    : p.alive
                      ? '存活'
                      : reasonText[p.eliminationReason] || '已淘汰'}
                </span>
              </div>
            ))}
          </div>
          {result.players.length > 4 && (
            <div className="party-pages">
              <Button disabled={!page} onClick={() => setPage(0)}>
                上一頁
              </Button>
              <span>{page + 1}／2</span>
              <Button disabled={page === 1} onClick={() => setPage(1)}>
                下一頁
              </Button>
            </div>
          )}
          <footer>
            {host ? (
              <Button
                className="primary"
                disabled={party.busy}
                onClick={() => void runtime.current.partyAction('again')}
              >
                再戰 · 返回等待室
              </Button>
            ) : (
              <span>等待房主開啟下一局</span>
            )}
            <Button onClick={leave}>離開房間</Button>
          </footer>
        </section>
      ) : pvp.settingsOpen ? (
        <section className="pvp-card">
          <h1>飛行與操作設定</h1>
          <p>設定不會暫停對戰；飛機保持目前航向與速度。</p>
          <nav className="party-mode" aria-label="設定分頁">
            <Button
              aria-pressed={tab === 'flight'}
              onClick={() => setTab('flight')}
            >
              飛行設定
            </Button>
            <Button
              aria-pressed={tab === 'help'}
              onClick={() => setTab('help')}
            >
              操作說明
            </Button>
          </nav>
          {tab === 'flight' ? (
            <div className="pvp-settings">
              <label>
                駕駛操作
                <select
                  value={settings.mode}
                  onChange={(e) => setting({ mode: e.target.value })}
                >
                  <option value="mouse">滑鼠駕駛</option>
                  <option value="keyboard">鍵盤駕駛</option>
                </select>
              </label>
              <label>
                靈敏度 {settings.sensitivity.toFixed(1)}
                <input
                  aria-label="飛行靈敏度"
                  type="range"
                  min="0.2"
                  max="3"
                  step="0.1"
                  value={settings.sensitivity}
                  onChange={(e) =>
                    setting({ sensitivity: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                反轉上下操作
                <input
                  type="checkbox"
                  checked={settings.invertY}
                  onChange={(e) => setting({ invertY: e.target.checked })}
                />
              </label>
              <label>
                預設視角
                <select
                  value={settings.camera}
                  onChange={(e) => setting({ camera: e.target.value })}
                >
                  <option value="chase">機尾第三人稱</option>
                  <option value="cockpit">第一人稱</option>
                </select>
              </label>
            </div>
          ) : (
            <div className="pvp-help">
              <p>
                <strong>空中部隊</strong>：滑鼠或方向鍵轉向；W／S 加減速，Q／E
                翻滾，V
                切換視角。兩次命中淘汰；撞地或障礙立即淘汰。黃色線內為戰區，高度上限
                70 公尺。
              </p>
              <p>
                <strong>地面部隊</strong>：W／A／S／D
                移動、空白鍵跳躍。右鍵瞄準飛機，維持三秒鎖定；冷卻完成後左鍵發射。鍵盤模式可用方向鍵轉向、Q
                切換瞄準、F 發射。準心對應實際飛機。
              </p>
              <p>
                淘汰後按 Tab
                觀戰隊友。房主離線會中止本局，延遲可能造成房主優勢。
              </p>
            </div>
          )}
          <footer>
            <Button className="primary" onClick={() => action('begin')}>
              {r.status === 'countdown' ? '關閉設定' : '返回戰場，取得控制'}
            </Button>
            <Button onClick={leave}>
              <DoorOpen size={16} /> 離開對戰
            </Button>
          </footer>
        </section>
      ) : r.status === 'countdown' ? (
        <section className="pvp-card pvp-countdown-card">
          <span className="eyebrow">每局隨機分隊</span>
          <h1>你是{air ? '空中飛行員' : '地面防空手'}</h1>
          <strong className="pvp-countdown">{pvp.countdown}</strong>
          <p>
            {air
              ? '持續前進，躲避導彈並存活至時間結束。'
              : '維持鎖定，與隊友擊落所有飛機。'}
          </p>
          <footer>
            <Button onClick={() => action('settings')}>查看操作與設定</Button>
            <Button onClick={leave}>離開</Button>
          </footer>
        </section>
      ) : !pvp.controlling && me?.alive ? (
        <section className="pvp-control-card">
          <strong>戰場持續進行</strong>
          <span>
            {air
              ? '飛機仍在向前飛行，請取得控制。'
              : '取得控制後可移動與瞄準。'}
          </span>
          <Button className="primary" onClick={() => action('begin')}>
            取得控制
          </Button>
          <Button onClick={() => action('settings')}>操作設定</Button>
        </section>
      ) : null}
    </div>
  );
}
