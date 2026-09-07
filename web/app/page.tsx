'use client';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import {
  Shield,
  Coins,
  ArrowRight,
  Volume2,
  VolumeX,
  BookOpen,
  Trash2,
  Clock3,
} from 'lucide-react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from '@/components/ui/alert-dialog';
import { PlayGuide } from '@/components/play-guide';
import { BattlePanel } from '@/components/battle-panel';
import { MultiplayerLobby } from '@/components/multiplayer-lobby';
import { DeploymentMap } from '@/components/deployment-map';
import { ArmoryShop } from '@/components/armory-shop';
import { isEditable } from '@/lib/controls';
import { lastPlayedLabel } from '@/lib/slot-display';

function Choice({ label, value, items, onChange }: any) {
  return (
    <label className="choice">
      <span>{label}</span>
      <Select
        value={value ?? 'none'}
        onValueChange={(v) => onChange(v === 'none' ? null : v)}
      >
        <SelectTrigger aria-label={label}>
          <SelectValue>
            {items.find((i: any) => i[0] === (value ?? 'none'))?.[1]}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {items.map(([id, name]: any) => (
            <SelectItem key={id} value={id}>
              {name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  );
}
export default function Home() {
  const [s, setState] = useState<any>(null),
    [c, setCatalog] = useState<any>(null);
  const [loading, setLoading] = useState('正在準備遊戲…'),
    [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [category, setCategory] = useState('weapons'),
    [custom, setCustom] = useState<string | null>(null),
    [tower, setTower] = useState<string | null>(null);
  const [rebirth, setRebirth] = useState(false),
    [help, setHelp] = useState(false),
    [end, setEnd] = useState(false);
  const surface = useRef<HTMLDivElement>(null),
    runtime = useRef<any>(null);
  useEffect(() => {
    let alive = true;
    import('../lib/game')
      .then(async ({ createGame }) => {
        const g = await createGame(
          surface.current!,
          (v) => {
            if (alive) {
              setState(v);
              if (v.message) setNotice(v.message);
            }
          },
          setLoading,
        );
        if (!alive) {
          g.dispose();
          return;
        }
        runtime.current = g;
        setCatalog(g.catalog);
        setState(g.getState());
        setLoading('');
      })
      .catch((e) => {
        if (alive) setError('遊戲無法載入：' + e.message);
      });
    return () => {
      alive = false;
      runtime.current?.dispose();
    };
  }, []);
  const p = s?.profile,
    screen = s?.screen,
    b = s?.battle,
    d = s?.draft,
    muted = s?.controls?.muted ?? false;
  const send = (action: string, payload: any = {}) => {
    setNotice('');
    try {
      return runtime.current?.send(action, payload, {
        screen,
        revision: p?.profile_revision,
        generation: s?.generation,
      });
    } catch (e: any) {
      setError(e.message);
    }
  };
  const openHelp = () => {
    runtime.current?.pause('help');
    setHelp(true);
  };
  const btn = (
    label: string,
    fn: () => void,
    secondary = false,
    disabled = false,
  ) => (
    <Button
      className={secondary ? 'secondary' : 'primary'}
      disabled={disabled}
      onClick={fn}
    >
      {label}
    </Button>
  );
  useEffect(() => {
    surface.current?.parentElement
      ?.querySelectorAll<HTMLElement>(':scope > .panel')
      .forEach((panel) =>
        panel.scrollTo({ top: 0, left: 0, behavior: 'instant' }),
      );
  }, [screen, custom]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        !s ||
        e.repeat ||
        help ||
        rebirth ||
        end ||
        s.delete_confirmation ||
        (s.party?.open && screen === 'profile_menu') ||
        isEditable(e.target)
      )
        return;
      if (e.code === 'KeyH') {
        e.preventDefault();
        openHelp();
        return;
      }
      if (screen === 'battle') return;
      // Let a focused button or open selector handle its own activation exactly once.
      if (
        ['Enter', 'Space'].includes(e.code) &&
        (e.target as Element)?.closest?.('button,a,[role="button"]')
      )
        return;
      if (screen === 'slot_select' && /^Digit[1-5]$/.test(e.code)) {
        e.preventDefault();
        send('select_slot', { slot: Number(e.code.slice(-1)) });
      } else if (e.code === 'Escape' && screen === 'store') {
        e.preventDefault();
        if (custom) setCustom(null);
        else send('menu');
      } else if (e.code === 'Escape' && screen?.startsWith('result_')) {
        e.preventDefault();
        send('menu');
      } else if (screen === 'profile_menu' && e.code === 'Space') {
        e.preventDefault();
        send('prepare');
      } else if (
        screen?.startsWith('prepare_') &&
        ['Enter', 'Escape'].includes(e.code)
      ) {
        e.preventDefault();
        send(
          e.code === 'Escape'
            ? 'back'
            : screen === 'prepare_confirm'
              ? 'start'
              : 'next',
        );
      }
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, [
    screen,
    s?.generation,
    s?.delete_confirmation,
    p?.profile_revision,
    help,
    rebirth,
    end,
    custom,
  ]);
  return (
    <main className={`game ${screen === 'battle' ? 'in-battle' : ''}`}>
      <div ref={surface} className="world" aria-label="3D 糖果防線戰場" />
      <header className="topbar">
        <div className="brand">
          <Shield size={25} />
          <span>
            糖果防線<small>3D 防空守衛</small>
          </span>
        </div>
        <div className="top-actions">
          {p && (
            <span className="wallet">
              <Coins size={18} />
              {p.coins.toLocaleString()}
              <span className="muted">重生 {p.rebirth_count}</span>
            </span>
          )}
          {!loading && !error && (
            <Button className="help-entry secondary" onClick={openHelp}>
              <BookOpen size={18} />
              <span>遊玩方法</span>
            </Button>
          )}
          <Button
            className="icon sound-toggle"
            aria-label={muted ? '開啟音效' : '靜音'}
            aria-pressed={muted}
            title={muted ? '目前靜音，點擊開啟音效' : '音效已開啟，點擊靜音'}
            disabled={!s}
            onClick={() => runtime.current?.setMuted(!muted)}
          >
            {muted ? (
              <VolumeX size={22} aria-hidden="true" />
            ) : (
              <Volume2 size={22} aria-hidden="true" />
            )}
            <span className="sound-label">{muted ? '已靜音' : '音效開啟'}</span>
          </Button>
        </div>
      </header>
      {(loading || error) && (
        <section className="panel loading">
          <Shield size={40} />
          <h1>糖果防線</h1>
          <p role="status">{error || loading}</p>
          {error && btn('重新載入', () => location.reload())}
          <p className="muted">
            首次載入需要下載遊戲環境。可使用滑鼠、鍵盤或觸控遊玩。
          </p>
        </section>
      )}
      {!loading && !error && s && c && (
        <>
          {screen === 'slot_select' && (
            <section className="panel start">
              <span className="eyebrow">守住城市，迎擊天空</span>
              <h1>
                準備好
                <br />
                守住這道防線？
              </h1>
              <p>選擇一個存檔欄位，開始你的防守戰役。</p>
              <div className="slots">
                {(s.slots || []).map((slot: any) => (
                  <article className="save-slot" key={slot.slot}>
                    <Button
                      className="slot"
                      disabled={
                        slot.status === 'unavailable' ||
                        slot.status === 'corrupt'
                      }
                      aria-label={`${slot.status === 'empty' ? '建立' : '繼續'}存檔 ${slot.slot}`}
                      onClick={() => send('select_slot', { slot: slot.slot })}
                    >
                      <span className="slot-number">0{slot.slot}</span>
                      <span className="slot-copy">
                        <strong>存檔 {slot.slot}</strong>
                        <span>
                          {slot.status === 'empty'
                            ? '空白欄位・開始新遊戲'
                            : slot.status === 'corrupt'
                              ? '資料無法讀取・可刪除重建'
                              : slot.status === 'unavailable'
                                ? '瀏覽器拒絕讀取'
                                : `重生 ${slot.rebirth_count} 次・${slot.coins.toLocaleString()} 金幣`}
                        </span>
                      </span>
                      <ArrowRight size={18} aria-hidden="true" />
                    </Button>
                    {slot.status !== 'empty' && (
                      <div className="slot-meta">
                        <span>
                          <Clock3 size={15} aria-hidden="true" />
                          最後遊玩：{lastPlayedLabel(slot.last_played_at)}
                        </span>
                        <Button
                          className="slot-delete"
                          disabled={slot.status === 'unavailable'}
                          aria-label={`刪除存檔 ${slot.slot}`}
                          onClick={() =>
                            send('request_delete', { slot: slot.slot })
                          }
                        >
                          <Trash2 size={16} aria-hidden="true" />
                          刪除
                        </Button>
                      </div>
                    )}
                  </article>
                ))}
              </div>
              <p className="muted">
                快捷鍵 1–5
                選擇存檔。日期依本機時區顯示；舊存檔再次遊玩後會補上日期。進度保存在此瀏覽器，不同網址的存檔彼此獨立。
              </p>
            </section>
          )}
          {s.party?.open && screen === 'profile_menu' && (
            <MultiplayerLobby party={s.party} runtime={runtime} profile={p} />
          )}
          {screen === 'profile_menu' && !s.party?.open && (
            <section className="panel start">
              <span className="eyebrow">
                存檔 {s.slot} · 下一關 {s.cursor.join('-')}
              </span>
              <h1>
                天空來襲。
                <br />
                防線由你守護。
              </h1>
              <p>裝配你的武器，擊落敵機，再清除空降敵兵。</p>
              <div className="menu-buttons">
                {btn('開始防守', () => send('prepare'))}
                {btn(
                  '多人遊戲',
                  () => void runtime.current?.partyAction('open'),
                )}
                {btn('裝備商店', () => send('store'), true)}
                {btn('更換存檔', () => send('slots'), true)}
                {btn('重生', () => setRebirth(true), true)}
              </div>
              <div className="control-guide">
                <strong>第一次遊玩？</strong>
                <p>先閱讀遊玩方法。出戰後會先暫停，選好操作方式才開始。</p>
                {btn('查看遊玩方法', openHelp, true)}
                <p className="muted">Space 開始準備 · H 開啟說明</p>
              </div>
            </section>
          )}
          {screen?.startsWith('prepare_') && (
            <section
              className={`panel preparation ${screen === 'prepare_deployment' ? 'deployment-preparation' : ''}`}
            >
              <span className="eyebrow">
                出戰準備 · 關卡 {s.cursor.join('-')}
              </span>
              <nav className="steps" aria-label="出戰步驟">
                {['裝甲', '武器', '砲塔', '確認'].map((x, i) => (
                  <span
                    key={x}
                    aria-current={
                      [
                        'prepare_armor',
                        'prepare_weapons',
                        'prepare_deployment',
                        'prepare_confirm',
                      ].indexOf(screen) === i
                        ? 'step'
                        : undefined
                    }
                    className={
                      [
                        'prepare_armor',
                        'prepare_weapons',
                        'prepare_deployment',
                        'prepare_confirm',
                      ].indexOf(screen) === i
                        ? 'current'
                        : ''
                    }
                  >
                    {i + 1} {x}
                  </span>
                ))}
              </nav>
              {screen === 'prepare_armor' && (
                <>
                  <h1>選擇你的裝甲</h1>
                  <Choice
                    label="本次穿戴"
                    value={d.armor_id}
                    items={[
                      ['none', '不穿裝甲'],
                      ...p.owned_armors.map((id: string) => [
                        id,
                        c.armors[id].name,
                      ]),
                    ]}
                    onChange={(id: string) => send('armor', { id })}
                  />
                  <p>最多穿戴一件裝甲。新裝甲可在商店購買。</p>
                </>
              )}
              {screen === 'prepare_weapons' && (
                <>
                  <h1>安排五個武器槽</h1>
                  <p>
                    至少攜帶一把防空與一把對地武器。戰場使用相同的 1–5 槽位。
                  </p>
                  {d.weapon_slots.map((id: string, i: number) => (
                    <Choice
                      key={i}
                      label={`武器槽 ${i + 1}`}
                      value={id}
                      items={[
                        ['none', '空槽'],
                        ...Object.keys(p.owned_weapons).map((k) => [
                          k,
                          c.weapons[k].name,
                        ]),
                      ]}
                      onChange={(id: string) =>
                        send('weapon', { slot: i + 1, id })
                      }
                    />
                  ))}
                </>
              )}
              {screen === 'prepare_deployment' && (
                <>
                  <h1>部署自動防禦</h1>
                  <DeploymentMap
                    c={c}
                    p={p}
                    d={d}
                    tower={tower}
                    setTower={setTower}
                    send={send}
                  />
                </>
              )}
              {screen === 'prepare_confirm' && (
                <>
                  <h1>確認出戰配置</h1>
                  <p>裝甲：{c.armors[d.armor_id]?.name || '無'}</p>
                  <ol className="loadout-list">
                    {d.weapon_slots.map((id: string, i: number) => (
                      <li key={i}>{c.weapons[id]?.name || '空槽'}</li>
                    ))}
                  </ol>
                  <p>
                    已部署 {d.deployments.length}{' '}
                    台砲塔。確認後保存配置，進入暫停的戰鬥就緒畫面。
                  </p>
                </>
              )}
              <footer>
                {btn('返回', () => send('back'), true)}
                {btn(
                  screen === 'prepare_confirm'
                    ? s.party?.room
                      ? '保存配置並準備'
                      : '確認並出戰'
                    : '下一步',
                  () => send(screen === 'prepare_confirm' ? 'start' : 'next'),
                )}
              </footer>
              <p className="shortcut-hint">
                Enter 下一步 · Esc 返回 · H 遊玩方法
              </p>
            </section>
          )}
          {screen === 'store' && (
            <ArmoryShop
              c={c}
              s={s}
              category={category}
              setCategory={setCategory}
              custom={custom}
              setCustom={setCustom}
              send={send}
            />
          )}
          {screen === 'battle' && b && (
            <BattlePanel
              b={b}
              c={c}
              p={p}
              controls={s.controls}
              runtime={runtime}
              onHelp={openHelp}
              onEnd={() => setEnd(true)}
            />
          )}
          {screen?.startsWith('result_') && (
            <section className="panel pause">
              <span className="eyebrow">關卡 {s.result?.level}</span>
              <h1>{s.result?.success ? '防線守住了！' : '防線失守'}</h1>
              <p>
                {s.result?.success
                  ? `獲得 ${s.result.reward} 金幣。`
                  : s.result?.reason === 'impact'
                    ? '敵機突破防空線'
                    : s.result?.reason === 'city'
                      ? '城市遭到摧毀'
                      : '防守者倒下'}
              </p>
              {s.result?.success &&
                btn(`前往下一關 ${s.cursor.join('-')}`, () => send('prepare'))}
              {btn('返回主選單', () => send('menu'), true)}
            </section>
          )}
          {screen === 'save_error' && (
            <section className="panel pause">
              <h1>進度尚未保存</h1>
              <p>{s.error}</p>
              <p>本次結果仍保留，重試不會重複扣款或發放獎勵。</p>
              {btn('重試保存', () => send('retry'))}
            </section>
          )}
          <PlayGuide
            open={help}
            onOpenChange={setHelp}
            mode={s.controls.mode}
          />
          <AlertDialog
            open={!!s.delete_confirmation}
            onOpenChange={(open) => {
              if (!open) send('cancel_delete');
            }}
          >
            <AlertDialogContent>
              <AlertDialogTitle>
                刪除存檔 {s.delete_confirmation?.slot}？
              </AlertDialogTitle>
              <AlertDialogDescription>
                此欄位的金幣、裝備、重生進度與遊玩日期將永久刪除，無法復原。其他欄位不受影響。
              </AlertDialogDescription>
              <AlertDialogFooter>
                <AlertDialogCancel>保留存檔</AlertDialogCancel>
                <AlertDialogAction
                  className="delete-confirm"
                  onClick={() => send('confirm_delete', s.delete_confirmation)}
                >
                  確認刪除
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <AlertDialog open={end} onOpenChange={setEnd}>
            <AlertDialogContent>
              <AlertDialogTitle>結束本局？</AlertDialogTitle>
              <AlertDialogDescription>
                本局不發放獎勵，下一次從 1-1 開始。取消後仍保持暫停。
              </AlertDialogDescription>
              <AlertDialogFooter>
                <AlertDialogCancel>繼續整備</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => {
                    send('menu');
                    setEnd(false);
                  }}
                >
                  結束並返回主選單
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          {p && (
            <AlertDialog open={rebirth} onOpenChange={setRebirth}>
              <AlertDialogContent>
                <AlertDialogTitle>確認重生？</AlertDialogTitle>
                <AlertDialogDescription>
                  需要 {1000 * (p.rebirth_count + 1)}{' '}
                  金幣及重生資格。本輪金幣、購買與升級將全部清空，重新配發三把基礎武器。
                </AlertDialogDescription>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => {
                      send('rebirth');
                      setRebirth(false);
                    }}
                  >
                    確認重生
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
          <Button aria-label="關閉提示" onClick={() => setNotice('')}>
            ×
          </Button>
        </div>
      )}
    </main>
  );
}
