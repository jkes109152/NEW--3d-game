'use client';
import { createContext, useContext, useEffect, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Shield,
  Sparkles,
  Wrench,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import type {
  Appearance,
  ModelKind,
  createArmoryPreview,
} from '@/lib/armory-models';
import {
  ARMOR_DETAILS,
  TURRET_DETAILS,
  WEAPON_DETAILS,
  UPGRADE_DETAILS,
  STAT_LABELS,
  number,
  statValue,
  relevantChanges,
  weaponRows,
  attachmentDescription,
} from '@/lib/armory-info';

type Preview = ReturnType<typeof createArmoryPreview>;
const PreviewContext = createContext<Preview | null>(null);
function ModelPreview({
  kind,
  id,
  name,
  appearance,
}: {
  kind: ModelKind;
  id: string;
  name: string;
  appearance?: Appearance;
}) {
  const preview = useContext(PreviewContext);
  const [src, setSrc] = useState(''),
    [failed, setFailed] = useState(false);
  const appearanceKey = JSON.stringify(appearance || {});
  useEffect(() => {
    let live = true;
    setSrc('');
    setFailed(false);
    if (preview)
      preview
        .render(kind, id, JSON.parse(appearanceKey))
        .then((url) => {
          if (live) setSrc(url);
        })
        .catch(() => {
          if (live) setFailed(true);
        });
    return () => {
      live = false;
    };
  }, [preview, kind, id, appearanceKey]);
  return (
    <div className="armory-model">
      {src ? (
        <img src={src} alt={name + '的實際裝備外觀'} width={600} height={320} />
      ) : (
        <span>
          {failed ? '外觀載入失敗，請重新開啟商店' : '正在準備裝備外觀…'}
        </span>
      )}
    </div>
  );
}
function Stats({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="armory-stats">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
function Changes({ changes, definition }: { changes: any; definition?: any }) {
  const values = relevantChanges(changes, definition);
  if (!values.length) return null;
  return (
    <dl className="stat-changes">
      {values.map(([key, change]: any) => (
        <div key={key}>
          <dt>
            {key === 'base_damage' && definition?.pellet_count > 1
              ? '單顆彈丸傷害'
              : STAT_LABELS[key]}
          </dt>
          <dd>
            <span>{statValue(key, change.before)}</span>
            <ArrowRight aria-label="變為" size={14} />
            <strong>{statValue(key, change.after)}</strong>
          </dd>
        </div>
      ))}
    </dl>
  );
}
function WeaponStats({ definition, stats }: { definition: any; stats: any }) {
  return <Stats rows={weaponRows(definition, stats)} />;
}
export function ArmoryShop({
  c,
  s,
  category,
  setCategory,
  custom,
  setCustom,
  send,
}: any) {
  const p = s.profile;
  const [preview, setPreview] = useState<Preview | null>(null);
  const [modelError, setModelError] = useState('');
  const [receipt, setReceipt] = useState<any>(null);
  const [weaponFilter, setWeaponFilter] = useState('all');
  const [look, setLook] = useState<Appearance | null>(null);
  useEffect(() => {
    let live = true,
      instance: Preview | undefined;
    import('@/lib/armory-models')
      .then(({ createArmoryPreview }) => {
        if (!live) return;
        instance = createArmoryPreview(c);
        setPreview(instance);
      })
      .catch(() => {
        if (live) setModelError('裝備外觀無法載入，請重新開啟商店。');
      });
    return () => {
      live = false;
      void instance?.dispose();
    };
  }, [c]);
  useEffect(() => {
    setLook(null);
    setReceipt(null);
  }, [custom, category]);
  const w = custom ? p.owned_weapons[custom] : null,
    def = custom ? c.weapons[custom] : null;
  const appearance: Appearance = w
    ? {
        selected_color: w.selected_color,
        selected_pattern: w.selected_pattern,
        selected_attachments: w.selected_attachments,
      }
    : {};
  const tx = (
    payload: any,
    title?: string,
    changes?: any,
    definition?: any,
  ) => {
    const next = send('transaction', payload);
    if (title && next?.transaction_result?.result_code === 'applied') {
      setReceipt({ title, changes, definition });
      setLook(null);
    }
  };
  const purchase = (kind: string, item: any) =>
    tx(
      { kind: 'purchase_' + kind, [kind + '_id']: item.id },
      `已購買 ${item.name}。${kind === 'turret' ? '請在出戰準備中部署。' : '請在出戰準備中選擇攜帶。'}`,
    );
  const customize = (updates: Appearance, title: string) =>
    tx(
      {
        kind: 'customize_weapon',
        weapon_id: custom,
        ...appearance,
        ...updates,
      },
      title,
    );
  const upgrade = (quote: any, payload: any, name: string, definition?: any) =>
    tx(payload, `升級完成：${name}`, quote.changes, definition);
  const canBuy = (price: number) => p.coins >= price;
  const buyButton = (kind: string, item: any, locked = false) => (
    <Button
      className="primary"
      disabled={locked || !canBuy(item.price)}
      onClick={() => purchase(kind, item)}
    >
      {locked
        ? '首次重生後開放'
        : canBuy(item.price)
          ? `購買 · ${item.price} 金幣`
          : `購買需 ${item.price} 金幣 · 還差 ${item.price - p.coins}`}
    </Button>
  );
  const upgradeButton = (
    quote: any,
    payload: any,
    name: string,
    definition?: any,
  ) => (
    <Button
      className="primary"
      disabled={!quote.available || !canBuy(quote.price)}
      onClick={() => upgrade(quote, payload, name, definition)}
    >
      {!quote.available
        ? quote.reason
        : canBuy(quote.price)
          ? `升級 · ${quote.price} 金幣`
          : `升級需 ${quote.price} 金幣 · 還差 ${quote.price - p.coins}`}
    </Button>
  );
  return (
    <PreviewContext.Provider value={preview}>
      <section className="panel store armory">
        <div className="section-head">
          <div>
            <span className="eyebrow">
              補給站 / {custom ? '武器工坊' : '裝備圖鑑'}
            </span>
            <h1>{custom ? def.name : '挑選你的下一步火力'}</h1>
          </div>
          <Button
            className="secondary"
            onClick={() => (custom ? setCustom(null) : send('menu'))}
          >
            <ArrowLeft size={16} />
            {custom ? '返回商店' : '返回主選單'}
          </Button>
        </div>
        {modelError && <p role="alert">{modelError}</p>}
        {receipt && (
          <div className="upgrade-receipt" role="status">
            <Check size={20} />
            <div>
              <strong>{receipt.title}</strong>
              <Changes
                changes={receipt.changes}
                definition={receipt.definition}
              />
            </div>
            <Button
              className="secondary"
              aria-label="關閉升級通知"
              onClick={() => setReceipt(null)}
            >
              ×
            </Button>
          </div>
        )}
        {!custom ? (
          <>
            <p className="armory-intro">
              看清外觀、比較能力，再決定配置。武器升級只強化指定槍枝；「自身升級」提升角色的基礎生命。
            </p>
            <nav className="filters" aria-label="商店分類">
              {[
                ['weapons', '槍枝'],
                ['armors', '裝甲'],
                ['turrets', '自動防禦'],
                ['player', '自身升級'],
              ].map(([id, label]) => (
                <Button
                  key={id}
                  aria-pressed={category === id}
                  className={category === id ? 'primary' : 'secondary'}
                  onClick={() => setCategory(id)}
                >
                  {label}
                </Button>
              ))}
            </nav>
            {category === 'weapons' && (
              <>
                <div className="weapon-filters" aria-label="武器種類">
                  {[['all', '全部 20 把'], ...Object.entries(c.categories)].map(
                    ([id, label]: any) => (
                      <Button
                        key={id}
                        aria-pressed={weaponFilter === id}
                        className={
                          weaponFilter === id ? 'primary' : 'secondary'
                        }
                        onClick={() => setWeaponFilter(id)}
                      >
                        {label}
                      </Button>
                    ),
                  )}
                </div>
                <p className="muted">
                  已擁有武器顯示目前升級與配件後的數值。射速不含換彈、重新鎖定及手動按鍵的等待。
                </p>
              </>
            )}
            {category === 'armors' && (
              <p className="callout">
                每次出戰可穿一件裝甲。下方「穿戴後」已包含自身生命升級；每關可自動回復的總量為生命上限的
                20%。
              </p>
            )}
            {category === 'turrets' && (
              <p className="callout">
                首次重生後可購買砲塔，目前部署容量 {p.rebirth_count * 2}{' '}
                台。購買後須在出戰準備放置，且目標與砲塔之間必須沒有掩體遮擋。
              </p>
            )}
            <div className="armory-grid">
              {category === 'weapons' &&
                Object.values(c.weapons)
                  .filter(
                    (item: any) =>
                      weaponFilter === 'all' || item.category === weaponFilter,
                  )
                  .map((item: any) => {
                    const owned = p.owned_weapons[item.id],
                      info = WEAPON_DETAILS[item.id];
                    return (
                      <article
                        className="armory-card"
                        key={item.id}
                        aria-label={item.name}
                      >
                        <div className="armory-card-top">
                          <span>
                            {item.id} · {c.categories[item.category]}
                          </span>
                          {owned && (
                            <span className="owned">
                              <Check size={14} />
                              已擁有
                            </span>
                          )}
                        </div>
                        <ModelPreview
                          kind="weapons"
                          id={item.id}
                          name={item.name}
                          appearance={
                            owned && {
                              selected_color: owned.selected_color,
                              selected_pattern: owned.selected_pattern,
                              selected_attachments: owned.selected_attachments,
                            }
                          }
                        />
                        <div className="armory-card-body">
                          <span className="weapon-role">{info.role}</span>
                          <h2>{item.name}</h2>
                          <p className="weapon-description">
                            {info.description}
                          </p>
                          <div className="equipment-tags">
                            <span>
                              {item.target_kind === 'aircraft'
                                ? '對空'
                                : '對地'}
                            </span>
                            <span>{c.modes[item.fire_mode]}</span>
                            <span>{owned ? '目前能力' : '基礎能力'}</span>
                          </div>
                          <WeaponStats
                            definition={item}
                            stats={s.shop.weapons[item.id].stats}
                          />
                          <div className="card-action">
                            {owned ? (
                              <Button
                                className="secondary"
                                onClick={() => setCustom(item.id)}
                              >
                                <Wrench size={16} />
                                改裝與升級
                              </Button>
                            ) : (
                              buyButton('weapon', item)
                            )}
                          </div>
                        </div>
                      </article>
                    );
                  })}
              {category === 'armors' &&
                Object.values(c.armors).map((item: any) => {
                  const stats = s.shop.armors[item.id],
                    owned = p.owned_armors.includes(item.id);
                  return (
                    <article
                      className="armory-card"
                      key={item.id}
                      aria-label={item.name}
                    >
                      <div className="armory-card-top">
                        <span>{item.id} · 裝甲</span>
                        {owned && <span className="owned">已擁有</span>}
                      </div>
                      <ModelPreview
                        kind="armors"
                        id={item.id}
                        name={item.name}
                      />
                      <div className="armory-card-body">
                        <h2>{item.name}</h2>
                        <p className="weapon-description">
                          {ARMOR_DETAILS[item.id]}
                        </p>
                        <Stats
                          rows={[
                            [
                              '生命加成',
                              (item.hp_delta >= 0 ? '+' : '') + item.hp_delta,
                            ],
                            ['穿戴後生命', number(stats.max_hp)],
                            [
                              '穿戴後移速',
                              statValue('move_speed', stats.move_speed),
                            ],
                            ['每次減傷', number(stats.damage_reduction)],
                            [
                              '未受傷後等待',
                              statValue('regen_delay', stats.regen_delay),
                            ],
                            ['每秒回復生命', number(stats.regen_rate)],
                            ['每關回復上限', number(stats.regen_budget)],
                          ]}
                        />
                        <div className="card-action">
                          {owned ? (
                            <p className="muted">在出戰準備中選擇穿戴</p>
                          ) : (
                            buyButton('armor', item)
                          )}
                        </div>
                      </div>
                    </article>
                  );
                })}
              {category === 'turrets' &&
                Object.values(c.turrets).map((item: any) => (
                  <article
                    className="armory-card"
                    key={item.id}
                    aria-label={item.name}
                  >
                    <div className="armory-card-top">
                      <span>
                        {item.id} ·{' '}
                        {item.target_kind === 'aircraft'
                          ? '自動防空'
                          : '自動對地'}
                      </span>
                      <span>
                        持有{' '}
                        {
                          p.owned_turrets.filter(
                            (t: any) => t.turret_id === item.id,
                          ).length
                        }{' '}
                        台
                      </span>
                    </div>
                    <ModelPreview
                      kind="turrets"
                      id={item.id}
                      name={item.name}
                    />
                    <div className="armory-card-body">
                      <h2>{item.name}</h2>
                      <p className="weapon-description">
                        {TURRET_DETAILS[item.id]}
                      </p>
                      <Stats
                        rows={[
                          ['單發傷害', number(item.damage)],
                          ['射速', `${number(1 / item.interval)} 發／秒`],
                          ['發射間隔', statValue('interval', item.interval)],
                          ['水平射程', statValue('range', item.range)],
                          [
                            '鎖定等待',
                            statValue('lock_seconds', item.lock_seconds),
                          ],
                          ['單台部署容量', '1 台'],
                        ]}
                      />
                      <div className="card-action">
                        {buyButton('turret', item, p.rebirth_count < 1)}
                      </div>
                    </div>
                  </article>
                ))}
              {category === 'player' && (
                <article className="armory-card player-upgrade">
                  <ModelPreview kind="player" id="player" name="防守者" />
                  <div className="armory-card-body">
                    <span className="weapon-role">強化角色自身</span>
                    <h2>
                      <Shield size={20} />
                      生命上限 · Lv.{p.player_upgrades.max_hp}
                    </h2>
                    <p>
                      每級讓角色的基礎生命增加
                      10，並提高每關可回復的總量。效果適用於任何槍枝配置；裝甲的生命加成會再疊加。
                    </p>
                    <Stats
                      rows={[
                        ['目前基礎生命', number(s.shop.player.max_hp)],
                        [
                          '目前移動速度',
                          statValue('move_speed', s.shop.player.move_speed),
                        ],
                        [
                          '目前跳躍高度',
                          statValue('jump_height', s.shop.player.jump_height),
                        ],
                      ]}
                    />
                    <p className="muted">
                      此項升級提升生命與回復上限。想調整移動能力，可在裝甲分類選擇。
                    </p>
                    <h3>升級後會改變</h3>
                    <Changes changes={s.quotes.player.changes} />
                    {upgradeButton(
                      s.quotes.player,
                      { kind: 'upgrade_player', upgrade_id: 'max_hp' },
                      '防守者生命上限',
                    )}
                  </div>
                </article>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="weapon-workbench">
              <div>
                <ModelPreview
                  kind="weapons"
                  id={custom}
                  name={def.name}
                  appearance={look || appearance}
                />
                <p className="model-caption">
                  {look
                    ? '外觀試看 · 尚未套用'
                    : '目前外觀 · 與戰場手持武器一致'}
                </p>
              </div>
              <div>
                <span className="weapon-role">
                  {WEAPON_DETAILS[custom].role}
                </span>
                <p>{WEAPON_DETAILS[custom].description}</p>
                <div className="equipment-tags">
                  <span>{c.categories[def.category]}</span>
                  <span>{c.modes[def.fire_mode]}</span>
                  <span>目前能力</span>
                </div>
                <WeaponStats
                  definition={def}
                  stats={s.shop.weapons[custom].stats}
                />
              </div>
            </div>
            <section className="workbench-section">
              <h2>
                <Wrench size={20} />
                強化這把武器
              </h2>
              <p>
                以下升級只作用於「{def.name}
                」。數值已包含目前配件，每次按升級提升一級；下次出戰即可使用。
              </p>
              <div className="upgrade-grid">
                {Object.entries(s.quotes.weapons[custom]).map(
                  ([key, q]: any) => (
                    <article className="upgrade-card" key={key}>
                      <span className="item-code">
                        {def.name} · Lv.{w.upgrade_levels[key]}
                        {q.available ? ` → ${w.upgrade_levels[key] + 1}` : ''}
                      </span>
                      <h3>{c.upgrade_names[key]}</h3>
                      <p>{UPGRADE_DETAILS[key]}</p>
                      <Changes changes={q.changes} definition={def} />
                      {upgradeButton(
                        q,
                        {
                          kind: 'upgrade_weapon',
                          weapon_id: custom,
                          upgrade_id: key,
                        },
                        def.name + '・' + c.upgrade_names[key],
                        def,
                      )}
                    </article>
                  ),
                )}
              </div>
            </section>
            <section className="workbench-section">
              <h2>配件與取捨</h2>
              <p>
                每個槽位可裝一件。同槽的新配件會替換原配件；購買後再按「裝備」。下方數值顯示現在到裝備或卸下之後的差異。
              </p>
              <div className="upgrade-grid">
                {Object.values(c.attachments)
                  .filter((a: any) => a.applicable_weapons.includes(custom))
                  .map((a: any) => {
                    const owned = w.owned_attachments.includes(a.id),
                      equipped = w.selected_attachments[a.slot] === a.id;
                    const q = s.shop.weapons[custom].attachments[a.id];
                    return (
                      <article className="upgrade-card" key={a.id}>
                        <span className="item-code">
                          {
                            {
                              optic: '瞄具槽',
                              barrel: '槍管槽',
                              feed: '供彈槽',
                            }[a.slot as 'optic' | 'barrel' | 'feed']
                          }{' '}
                          ·{' '}
                          {equipped ? '裝備中' : owned ? '已擁有' : '尚未購買'}
                        </span>
                        <h3>{a.name}</h3>
                        <p>{attachmentDescription(a.id, def.category)}</p>
                        <span className="muted">
                          {equipped ? '卸下後' : '裝備後'}
                        </span>
                        <Changes changes={q.changes} definition={def} />
                        <Button
                          className="secondary"
                          disabled={!owned && !canBuy(a.price)}
                          onClick={() =>
                            owned
                              ? customize(
                                  {
                                    selected_attachments: {
                                      ...w.selected_attachments,
                                      [a.slot]: equipped ? null : a.id,
                                    },
                                  },
                                  `${def.name}已${equipped ? '卸下' : '裝備'}${a.name}`,
                                )
                              : tx(
                                  {
                                    kind: 'purchase_attachment',
                                    weapon_id: custom,
                                    attachment_id: a.id,
                                  },
                                  `已購買${a.name}，按「裝備」即可使用。`,
                                )
                          }
                        >
                          {owned
                            ? equipped
                              ? '卸下'
                              : '裝備'
                            : canBuy(a.price)
                              ? `購買 · ${a.price} 金幣`
                              : `購買需 ${a.price} 金幣 · 還差 ${a.price - p.coins}`}
                        </Button>
                      </article>
                    );
                  })}
              </div>
            </section>
            <section className="workbench-section">
              <h2>
                <Sparkles size={20} />
                外觀工作台
              </h2>
              <p>
                顏色與圖案只改變外觀，傷害與射速維持原數值。先試看，再購買與套用；預覽同樣顯示已裝備的配件。
              </p>
              <div className="cosmetic-workbench">
                <div className="cosmetic-preview">
                  <ModelPreview
                    kind="weapons"
                    id={custom}
                    name={def.name}
                    appearance={look || appearance}
                  />
                  <p className="model-caption">
                    {look
                      ? '試看：' +
                        c.colors[look.selected_color || w.selected_color] +
                        ' / ' +
                        c.patterns[look.selected_pattern || w.selected_pattern]
                      : '目前使用：' +
                        c.colors[w.selected_color] +
                        ' / ' +
                        c.patterns[w.selected_pattern]}
                  </p>
                  {look && (
                    <Button className="secondary" onClick={() => setLook(null)}>
                      還原試看
                    </Button>
                  )}
                </div>
                <div>
                  {[
                    ['color', 'colors', '顏色'],
                    ['pattern', 'patterns', '圖案'],
                  ].map(([kind, key, label]) => (
                    <div className="cosmetic-options" key={kind}>
                      <h3>{label}</h3>
                      {Object.entries(c[key]).map(([id, name]: any) => {
                        const owned = w['owned_' + key].includes(id),
                          selected = w['selected_' + kind] === id,
                          price = kind === 'color' ? 75 : 100;
                        return (
                          <div className="cosmetic-row" key={id}>
                            <strong>{name}</strong>
                            <Button
                              className="secondary"
                              onClick={() =>
                                setLook({
                                  ...appearance,
                                  ...look,
                                  ['selected_' + kind]: id,
                                })
                              }
                            >
                              試看
                            </Button>
                            <Button
                              className="secondary"
                              disabled={selected || (!owned && !canBuy(price))}
                              onClick={() =>
                                owned
                                  ? customize(
                                      { ['selected_' + kind]: id },
                                      `${def.name}已套用${name}`,
                                    )
                                  : tx(
                                      {
                                        kind: 'purchase_cosmetic',
                                        weapon_id: custom,
                                        cosmetic_kind: kind,
                                        cosmetic_id: id,
                                      },
                                      `已購買${name}，按「套用」即可使用。`,
                                    )
                              }
                            >
                              {selected
                                ? '使用中'
                                : owned
                                  ? '套用'
                                  : canBuy(price)
                                    ? `${price} 金幣`
                                    : `${price} 金幣 · 還差 ${price - p.coins}`}
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}
        <p className="shortcut-hint">
          Esc {custom ? '返回商店' : '返回主選單'} · H 遊玩方法
        </p>
      </section>
    </PreviewContext.Provider>
  );
}
