'use client';
import { useEffect, useId, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Crosshair,
  Maximize2,
  Minus,
  Plus,
  Radar,
  Trash2,
  X,
  Zap,
} from 'lucide-react';
import { isEditable } from '@/lib/controls';
import {
  mapPoint,
  mapViewport,
  TURRET_KINDS,
  turretStock,
} from '@/lib/deployment-ui';
const visuals = {
  T01: { Icon: Zap, label: '機槍', description: '快速壓制近距離地面敵兵。' },
  T02: {
    Icon: Crosshair,
    label: '狙擊',
    description: '遠距離精準打擊地面敵兵。',
  },
  T03: { Icon: Radar, label: '防空', description: '自動鎖定並攔截空中敵機。' },
};
function TowerIcon({ kind }: { kind: string }) {
  const { Icon } = visuals[kind as keyof typeof visuals] || visuals.T01;
  return <Icon size={22} aria-hidden="true" />;
}
export function DeploymentMap({ c, p, d, tower, setTower, send }: any) {
  const [view, setView] = useState({ x: 0, y: 80, zoom: 1 });
  const [aspect, setAspect] = useState(1),
    [feedback, setFeedback] = useState('');
  const map = useRef<HTMLDivElement>(null),
    drag = useRef<any>(null),
    moved = useRef(false);
  const gridId = useId(),
    viewport = mapViewport(view, aspect),
    capacity = p.rebirth_count * 2;
  const owned = p.owned_turrets.find((t: any) => t.instance_id === tower);
  const placed = d.deployments.find((t: any) => t.instance_id === tower);
  const number = (id: string) =>
    p.owned_turrets.findIndex((t: any) => t.instance_id === id) + 1;
  const name = (t: any) =>
    `${c.turrets[t.turret_id].name} ${number(t.instance_id)} 號`;
  const zoom = (amount: number) =>
    setView((v) => ({ ...v, zoom: Math.max(1, Math.min(4, v.zoom * amount)) }));
  const pan = (x: number, y: number) =>
    setView((v) => ({
      ...v,
      x: Math.max(-60, Math.min(60, v.x + x / v.zoom)),
      y: Math.max(-80, Math.min(240, v.y + y / v.zoom)),
    }));
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) =>
      setAspect(entry.contentRect.width / entry.contentRect.height),
    );
    if (map.current) observer.observe(map.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (tower && !owned) setTower(null);
  }, [tower, owned, setTower]);
  const remove = (id: string) => {
    const result = send('remove', { id });
    if (
      result?.draft &&
      !result.draft.deployments.some((t: any) => t.instance_id === id)
    ) {
      setTower(null);
      setFeedback('已移除部署，砲塔已退回待部署庫存。');
    }
  };
  const select = (id: string) => {
    setTower(id);
    setFeedback('');
  };
  return (
    <div
      className="deployment-workspace"
      onKeyDown={(e) => {
        if (isEditable(e.target)) return;
        const keys: Record<string, [number, number]> = {
          KeyW: [0, 12],
          KeyS: [0, -12],
          KeyA: [-8, 0],
          KeyD: [8, 0],
        };
        if (keys[e.code]) {
          e.preventDefault();
          pan(...keys[e.code]);
        }
        if (e.code === 'Delete' && placed) {
          e.preventDefault();
          remove(tower);
        }
      }}
    >
      <div className="deployment-summary">
        <span>
          已部署 <strong>{d.deployments.length}</strong>／{capacity} 台
        </span>
        <span>剩餘容量 {Math.max(0, capacity - d.deployments.length)} 台</span>
      </div>
      {p.rebirth_count === 0 && (
        <p className="callout">
          首次重生後開放砲塔購買與部署。你仍可直接按「下一步」出戰。
        </p>
      )}
      <div className="deployment-layout">
        <aside className="turret-stock" aria-label="砲塔庫存與新增">
          <h2>新增砲塔</h2>
          <p>選擇種類，再點地圖空地放置。</p>
          {TURRET_KINDS.map((kind) => {
            const item = c.turrets[kind],
              stock = turretStock(p, d.deployments, kind),
              visual = visuals[kind];
            const reason = !p.rebirth_count
              ? '首次重生後開放'
              : !stock.total
                ? '尚未擁有・請至商店購買'
                : !stock.available.length
                  ? '已全部部署'
                  : d.deployments.length >= capacity
                    ? '部署容量已滿'
                    : '';
            return (
              <article className="turret-card" data-kind={kind} key={kind}>
                <div className="turret-card-title">
                  <span className="turret-symbol">
                    <TowerIcon kind={kind} />
                  </span>
                  <div>
                    <h3>{item.name}</h3>
                    <span>
                      {visual.label}・
                      {item.target_kind === 'aircraft' ? '對空' : '對地'}
                    </span>
                  </div>
                </div>
                <p>{visual.description}</p>
                <dl>
                  <div>
                    <dt>射程</dt>
                    <dd>{item.range} 公尺</dd>
                  </div>
                  <div>
                    <dt>射擊間隔</dt>
                    <dd>{item.interval} 秒</dd>
                  </div>
                </dl>
                <div className="turret-stock-count">
                  <span>
                    待部署 <strong>{stock.available.length}</strong>
                  </span>
                  <span>持有 {stock.total} 台</span>
                </div>
                <Button
                  className="primary turret-add"
                  disabled={!!reason}
                  aria-label={`新增${item.name}`}
                  onClick={() => select(stock.available[0].instance_id)}
                >
                  <Plus size={18} />
                  新增{visual.label}塔
                </Button>
                {reason && <small>{reason}</small>}
              </article>
            );
          })}
        </aside>
        <section className="deployment-board" aria-label="部署作戰地圖">
          <div className="deployment-board-head">
            <h2>防線部署圖</h2>
            <span>{view.zoom.toFixed(1)} 倍</span>
          </div>
          <div className="map-tools" aria-label="部署地圖控制">
            <Button aria-label="地圖放大" onClick={() => zoom(1.25)}>
              <Plus />
            </Button>
            <Button aria-label="地圖縮小" onClick={() => zoom(0.8)}>
              <Minus />
            </Button>
            <Button aria-label="地圖向上" onClick={() => pan(0, 12)}>
              <ArrowUp />
            </Button>
            <Button aria-label="地圖向下" onClick={() => pan(0, -12)}>
              <ArrowDown />
            </Button>
            <Button aria-label="地圖向左" onClick={() => pan(-8, 0)}>
              <ArrowLeft />
            </Button>
            <Button aria-label="地圖向右" onClick={() => pan(8, 0)}>
              <ArrowRight />
            </Button>
            <Button onClick={() => setView({ x: 0, y: 80, zoom: 1 })}>
              <Maximize2 size={17} />
              全圖
            </Button>
          </div>
          <div className="deployment-selection" role="status">
            {owned ? (
              <>
                <TowerIcon kind={owned.turret_id} />
                <span>
                  {placed ? '已選取' : '待放置'}：{name(owned)}
                  <small>
                    {placed
                      ? '點地圖空地移動，或移除部署。'
                      : '點地圖空地部署；尚未扣用容量。'}
                  </small>
                </span>
                <Button
                  aria-label="取消選取砲塔"
                  onClick={() => setTower(null)}
                >
                  <X />
                </Button>
              </>
            ) : (
              <span>
                {feedback || '按新增按鈕放置砲塔；點選圖示可移動或移除。'}
              </span>
            )}
          </div>
          <div
            ref={map}
            className="deploy-map tactical-map"
            aria-label="砲塔部署地圖"
            onWheel={(e) => zoom(e.deltaY < 0 ? 1.1 : 1 / 1.1)}
            onContextMenu={(e) => {
              e.preventDefault();
              setTower(null);
            }}
            onPointerDown={(e) => {
              if (e.button === 1) {
                e.preventDefault();
                moved.current = false;
                drag.current = { x: e.clientX, y: e.clientY };
                e.currentTarget.setPointerCapture(e.pointerId);
              }
            }}
            onPointerMove={(e) => {
              if (!drag.current) return;
              const r = e.currentTarget.getBoundingClientRect();
              moved.current = true;
              pan(
                (-(e.clientX - drag.current.x) / r.width) *
                  viewport.width *
                  view.zoom,
                ((e.clientY - drag.current.y) / r.height) *
                  viewport.height *
                  view.zoom,
              );
              drag.current = { x: e.clientX, y: e.clientY };
            }}
            onPointerUp={() => {
              drag.current = null;
            }}
            onPointerCancel={() => {
              drag.current = null;
            }}
            onClick={(e) => {
              if (moved.current) {
                moved.current = false;
                return;
              }
              if (!owned) return;
              const [x, z] = mapPoint(
                  [e.clientX, e.clientY],
                  e.currentTarget.getBoundingClientRect(),
                  viewport,
                ),
                result = send('place', { id: tower, x, z });
              if (
                result?.draft?.deployments.some(
                  (t: any) => t.instance_id === tower && t.x === x && t.z === z,
                )
              )
                setFeedback(`已${placed ? '移動' : '部署'}${name(owned)}。`);
            }}
          >
            <svg
              className="deployment-terrain"
              viewBox={`${viewport.left} ${-viewport.top} ${viewport.width} ${viewport.height}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <defs>
                <pattern
                  id={gridId}
                  width={10}
                  height={10}
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d="M 10 0 L 0 0 0 10"
                    fill="none"
                    stroke="#96bcc41c"
                    strokeWidth={0.35}
                  />
                </pattern>
              </defs>
              <rect
                x={-60}
                y={-240}
                width={120}
                height={320}
                fill="#214c55"
                stroke="#85b9bd"
                strokeWidth={0.5}
              />
              <rect
                x={-60}
                y={-240}
                width={120}
                height={320}
                fill={`url(#${gridId})`}
              />
              <polyline
                points={c.route.map((v: any) => `${v[0]},${-v[2]}`).join(' ')}
                fill="none"
                stroke="#f3b455"
                strokeWidth={7}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {c.covers.map((v: any, i: number) => (
                <rect
                  key={i}
                  x={v[0] - v[3] / 2}
                  y={-v[2] - v[5] / 2}
                  width={v[3]}
                  height={v[5]}
                  fill="#d994b1"
                />
              ))}
              <circle cx={-18} cy={-70} r={4.5} fill="#83ccf0" />
              <rect x={-9} y={53} width={18} height={14} fill="#83ccf0" />
              {placed && owned && (
                <circle
                  cx={placed.x}
                  cy={-placed.z}
                  r={c.turrets[owned.turret_id].range}
                  fill="#9ae8d413"
                  stroke="#9ae8d4"
                  strokeWidth={0.5}
                  strokeDasharray="2 2"
                />
              )}
            </svg>
            {d.deployments.map((t: any) => {
              const item = p.owned_turrets.find(
                  (v: any) => v.instance_id === t.instance_id,
                ),
                left = ((t.x - viewport.left) / viewport.width) * 100,
                top = ((viewport.top - t.z) / viewport.height) * 100;
              if (!item || left < 0 || left > 100 || top < 0 || top > 100)
                return null;
              return (
                <Button
                  key={t.instance_id}
                  className="map-turret"
                  data-kind={item.turret_id}
                  aria-label={`選取${name(item)}`}
                  aria-pressed={tower === t.instance_id}
                  style={{ left: `${left}%`, top: `${top}%` }}
                  onClick={(e) => {
                    e.stopPropagation();
                    select(t.instance_id);
                  }}
                >
                  <TowerIcon kind={item.turret_id} />
                  <span>{number(t.instance_id)}</span>
                </Button>
              );
            })}
            <span className="map-north">北側・敵機進場 ↓</span>
            <span className="map-south">南側・城市防線</span>
          </div>
          <div className="map-legend terrain-legend">
            <span className="route-key">敵軍通道</span>
            <span className="cover-key">掩體</span>
            <span className="spawn-key">出生區／城市</span>
          </div>
          <p className="map-legend">
            圓圈為水平射程。實際攻擊受高度與掩體限制；掩體、通道和出生區不可放置。滾輪縮放，中鍵拖曳平移。
          </p>
          {placed && (
            <Button
              className="secondary remove-deployment"
              onClick={() => remove(tower)}
            >
              <Trash2 size={18} />
              移除所選砲塔
            </Button>
          )}
          <div className="deployed-list">
            <h3>
              已部署砲塔 <span>{d.deployments.length} 台</span>
            </h3>
            {!d.deployments.length && (
              <p>尚未部署。新增後，每台砲塔會以專屬圖示與編號顯示在地圖上。</p>
            )}
            {d.deployments.map((t: any) => {
              const item = p.owned_turrets.find(
                (v: any) => v.instance_id === t.instance_id,
              );
              if (!item) return null;
              return (
                <div
                  className="deployed-row"
                  key={t.instance_id}
                  data-kind={item.turret_id}
                >
                  <Button
                    className="deployed-select"
                    aria-pressed={tower === t.instance_id}
                    onClick={() => {
                      select(t.instance_id);
                      setView((v) => ({ ...v, x: t.x, y: t.z }));
                    }}
                  >
                    <TowerIcon kind={item.turret_id} />
                    <span>{name(item)}</span>
                  </Button>
                  <Button
                    className="slot-delete"
                    aria-label={`移除${name(item)}`}
                    onClick={() => remove(t.instance_id)}
                  >
                    <Trash2 size={16} />
                    移除
                  </Button>
                </div>
              );
            })}
          </div>
          <p className="map-legend">
            移除只退回待部署庫存。按「確認並出戰」才保存本次配置。
          </p>
        </section>
      </div>
    </div>
  );
}
