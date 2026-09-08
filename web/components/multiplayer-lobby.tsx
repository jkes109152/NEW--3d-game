'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Users, DoorOpen, Plus, Check, Crown, WifiOff } from 'lucide-react';
import { partyMultiplier, pvpTimeLimit } from '@/lib/multiplayer-rules';

export function MultiplayerLobby({ party, runtime, profile }: any) {
  const [name, setName] = useState(party.me?.name || ''),
    [roomName, setRoomName] = useState('');
  const [roomPage, setRoomPage] = useState(0);
  const [mode, setMode] = useState('coop'),
    [memberPage, setMemberPage] = useState(0);
  const pvp = party.room?.mode === 'pvp';
  const page = Math.min(
    roomPage,
    Math.max(0, Math.ceil(party.rooms.length / 2) - 1),
  );
  const action = (kind: string, payload: any = {}) =>
      runtime.current.partyAction(kind, payload),
    r = party.room;
  const host = r?.hostId === party.me?.id,
    member = r?.members?.find((m: any) => m.id === party.me?.id);
  const count = r?.members?.length || 1,
    ready = r?.members?.filter((m: any) => m.ready).length || 0;
  return (
    <section className="panel multiplayer-panel">
      <div className="party-heading">
        <Users />
        <div>
          <span className="eyebrow">多人守衛</span>
          <h1>{!party.me ? '設定玩家名稱' : r ? r.name : '多人房間大廳'}</h1>
        </div>
      </div>
      {party.error && (
        <p role="alert" className="callout">
          {party.error}
        </p>
      )}
      {!party.me ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void action('identity', { name });
          }}
        >
          <label htmlFor="party-name">玩家名稱</label>
          <Input
            id="party-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={20}
            placeholder="輸入其他玩家看到的名稱"
            autoComplete="nickname"
          />
          <p>名稱會顯示在房間與戰場中。此瀏覽器會記住你的玩家身分。</p>
          <Button
            type="submit"
            className="primary"
            disabled={party.busy || !name.trim()}
          >
            進入房間大廳
          </Button>
        </form>
      ) : !r ? (
        <>
          <p className="party-identity">
            你好，{party.me.name}。選擇房間加入，或建立自己的房間。
          </p>
          <form
            className="party-create"
            onSubmit={(e) => {
              e.preventDefault();
              void action('create', {
                name: roomName || `${party.me.name}的房間`,
                mode,
              });
            }}
          >
            <Input
              aria-label="新房間名稱"
              value={roomName}
              onChange={(e) => setRoomName(e.target.value)}
              maxLength={20}
              placeholder="房間名稱"
            />
            <Button type="submit" className="primary" disabled={party.busy}>
              <Plus size={18} />
              建立房間
            </Button>
          </form>
          <div className="party-mode" role="group" aria-label="新房間模式">
            <Button
              aria-pressed={mode === 'coop'}
              onClick={() => setMode('coop')}
            >
              合作防守
            </Button>
            <Button
              aria-pressed={mode === 'pvp'}
              onClick={() => setMode('pvp')}
            >
              空地對戰
            </Button>
          </div>
          <div className="party-room-list">
            {!party.rooms.length ? (
              <p className="party-empty">
                目前沒有開放房間，建立房間後請朋友從這裡加入。
              </p>
            ) : (
              party.rooms.slice(page * 2, page * 2 + 2).map((room: any) => (
                <article key={room.id}>
                  <div>
                    <strong>{room.name}</strong>
                    <span>
                      房主 {room.host_name} ·{' '}
                      {room.mode === 'pvp'
                        ? '空地對戰'
                        : `合作 ${room.level_a}-${room.level_b}`}
                    </span>
                  </div>
                  <span>
                    {room.count}／{room.capacity || 4} 人
                  </span>
                  <Button
                    disabled={
                      party.busy ||
                      room.status !== 'waiting' ||
                      room.count >= (room.capacity || 4)
                    }
                    onClick={() => void action('join', { roomId: room.id })}
                  >
                    {['playing', 'countdown'].includes(room.status)
                      ? '戰鬥中'
                      : room.count >= (room.capacity || 4)
                        ? '已滿'
                        : '加入'}
                  </Button>
                </article>
              ))
            )}
          </div>
          {party.rooms.length > 2 && (
            <div className="party-pages">
              <Button disabled={!page} onClick={() => setRoomPage(page - 1)}>
                上一頁
              </Button>
              <span>
                {page + 1}／{Math.ceil(party.rooms.length / 2)}
              </span>
              <Button
                disabled={(page + 1) * 2 >= party.rooms.length}
                onClick={() => setRoomPage(page + 1)}
              >
                下一頁
              </Button>
            </div>
          )}
        </>
      ) : (
        <>
          {pvp ? (
            <div className="party-room-summary">
              <strong>空地對戰</strong>
              <span>{count}／8 人</span>
              <span>
                地面 {Math.floor(count / 2)}：空中 {Math.ceil(count / 2)}
              </span>
              <span>
                時限{' '}
                {count >= 2
                  ? `${Math.floor(pvpTimeLimit(count) / 60)}：${String(pvpTimeLimit(count) % 60).padStart(2, '0')}`
                  : '等待玩家'}
              </span>
            </div>
          ) : (
            <div className="party-room-summary">
              <span>
                關卡 {r.level?.[0]}-{r.level?.[1]}
              </span>
              <span>{count}／4 人</span>
              <span>敵人 ×{partyMultiplier(Math.min(4, count))}</span>
              <span>每人獎勵 ×{partyMultiplier(Math.min(4, count))}</span>
            </div>
          )}
          <p className="party-rule">
            {pvp
              ? '僅基礎防空炮 · 每局隨機分隊 · 不發金幣。空中躲避至時間結束，地面須擊落所有飛機。'
              : '擊退同一批敵人，守護同一座城市。每人都獲得完整獎勵，不按人數瓜分；倍率以本局開始人數固定。'}
          </p>
          <div className="party-members">
            {r.members
              .slice(
                Math.min(memberPage, Math.max(0, Math.ceil(count / 4) - 1)) * 4,
                Math.min(memberPage, Math.max(0, Math.ceil(count / 4) - 1)) *
                  4 +
                  4,
              )
              .map((m: any) => (
                <article key={m.id}>
                  <span className="party-avatar">{m.name.slice(0, 1)}</span>
                  <strong title={m.name}>
                    {m.name}
                    {m.id === party.me.id ? '（你）' : ''}
                  </strong>
                  {m.id === r.hostId && <Crown aria-label="房主" size={18} />}
                  <span>
                    {!m.online ? (
                      <>
                        <WifiOff size={16} />
                        離線
                      </>
                    ) : m.ready ? (
                      <>
                        <Check size={16} />
                        已準備
                      </>
                    ) : (
                      '準備中'
                    )}
                  </span>
                </article>
              ))}
          </div>
          {count > 4 && (
            <div className="party-pages">
              <Button
                disabled={memberPage === 0}
                onClick={() => setMemberPage(0)}
              >
                上一頁
              </Button>
              <span>{memberPage + 1}／2</span>
              <Button
                disabled={memberPage === 1}
                onClick={() => setMemberPage(1)}
              >
                下一頁
              </Button>
            </div>
          )}
          {r.status === 'closed' ? (
            <p role="status">房主已離線或關閉房間。請返回大廳加入其他房間。</p>
          ) : r.status === 'finished' ? (
            <div className="party-result">
              <h2>{r.receipt?.reward > 0 ? '合作防守成功！' : '本局已結束'}</h2>
              <p>
                {r.receipt?.reward > 0
                  ? `你獲得 ${r.receipt.reward} 金幣，完整存入出戰時的存檔。`
                  : '本局沒有勝利獎勵。'}
              </p>
              {host ? (
                <Button
                  className="primary"
                  disabled={party.busy}
                  onClick={() => void action('again')}
                >
                  返回房間，準備下一局
                </Button>
              ) : (
                <p>等待房主開啟下一局。</p>
              )}
            </div>
          ) : r.status === 'waiting' ? (
            <div className="party-wait-actions">
              <div className="party-ready-actions">
                <Button
                  hidden={pvp}
                  className="secondary"
                  disabled={party.busy}
                  onClick={() => void action('configure')}
                >
                  調整我的裝備與砲塔
                </Button>
                <Button
                  className="primary"
                  disabled={party.busy}
                  onClick={() =>
                    void action('ready', {
                      ready: !member?.ready,
                      ...(pvp ? {} : { profile }),
                    })
                  }
                >
                  {member?.ready
                    ? '取消準備'
                    : pvp
                      ? '準備完成'
                      : '使用目前配置，準備完成'}
                </Button>
              </div>
              {host ? (
                <Button
                  className="primary party-start"
                  disabled={party.busy || count < 2 || ready !== count}
                  onClick={() => void action('start')}
                >
                  {count < 2
                    ? '等待至少另一位玩家加入'
                    : ready !== count
                      ? `等待準備完成 ${ready}／${count}`
                      : '全員出戰'}
                </Button>
              ) : (
                <p>全員準備後，由房主開始戰鬥。</p>
              )}
            </div>
          ) : (
            <p role="status">正在同步戰場…</p>
          )}
          <p className="muted">
            {pvp
              ? '房主離線會中止，延遲可能造成房主優勢。設定或失焦不會暫停對戰。'
              : '房主需保持遊戲開啟。房主暫停時全房暫停；其他玩家暫停只停止自己的操作。'}
          </p>
        </>
      )}
      <footer>
        <Button
          className="secondary"
          disabled={party.busy}
          onClick={() => void action(r ? 'leave' : 'close')}
        >
          <DoorOpen size={18} />
          {r ? '離開房間' : '返回單人選單'}
        </Button>
        {party.me && !r && (
          <span className="muted">合作最多 4 人 · 空地對戰最多 8 人</span>
        )}
      </footer>
    </section>
  );
}
