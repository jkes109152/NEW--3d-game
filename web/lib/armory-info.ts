export const WEAPON_DETAILS: Record<
  string,
  { role: string; description: string }
> = {
  W01: {
    role: '遠距單體防空',
    description:
      '單根粗發射管搭配圓形導引鏡。鎖定一架敵機後發射追蹤飛彈，適合優先攔截遠方威脅；無法攻擊地面敵人。',
  },
  W02: {
    role: '多目標攔截',
    description:
      '蜂巢發射座與寬雷達翼，白框內所有有效敵機均完成鎖定後，才能同時齊射。鎖定框較大，射程比雲哨短；只對空。',
  },
  W03: {
    role: '靈活備用槍',
    description:
      '短槍管、小方彈匣的輕巧手槍。每次按下射擊發射一發，適合近距離精準補槍與節省換彈時間。',
  },
  W04: {
    role: '三發點放手槍',
    description:
      '雙層滑套與長彈匣，每次扣下扳機連發三顆糖彈。瞄準後短促點放，兩輪點放之間需要冷卻。',
  },
  W05: {
    role: '重擊手槍',
    description:
      '厚滑套、大型方形槍口，以較慢射速換取較高單發傷害。彈匣較小，適合有把握的單點射擊。',
  },
  W06: {
    role: '均衡自動步槍',
    description:
      '通風護木與三角固定托。按住射擊即可持續開火，射程、彈量與射速均衡，適合防守中距離通道。',
  },
  W07: {
    role: '中距三發點放',
    description:
      '分段護木搭配圓盤短匣。三發一組的點放步槍，單發較重、射程較長；每一組需要重新扣下扳機。',
  },
  W08: {
    role: '精準半自動步槍',
    description:
      '細長槍管與高橋鏡座。每次按下射擊打一發，以較高單發傷害和遠距射程，處理遠方地面目標。',
  },
  W09: {
    role: '重型自動火力',
    description:
      '厚護木與大型供彈盒的重步槍。持續射擊的單發傷害較高，代價是較慢節奏、較少彈量與較長換彈。',
  },
  W10: {
    role: '高速輕步槍',
    description:
      '小型多孔槍口與伸縮槍托。大彈匣、高射速，適合持續壓制；單發傷害和射程較低，需留意消耗速度。',
  },
  W11: {
    role: '近距快速反應',
    description:
      '環形護手與握把下方的長直匣。輕快自動射擊、換彈迅速，適合接近城市的敵人。',
  },
  W12: {
    role: '極速近距連射',
    description:
      '上置橫向彈匣與一體托架。衝鋒槍中最快的連射節奏，單發較輕、射程較短，適合集中火力掃射。',
  },
  W13: {
    role: '三發衝鋒槍',
    description:
      '側置彈匣與側折槍托。近中距離三發點放，單發傷害高於高速連射型，適合抓準敵人露出的時機。',
  },
  W14: {
    role: '穩重近距火力',
    description:
      '粗圓槍管與雙架厚槍托。用較慢射速換取衝鋒槍中較高的單發傷害，彈匣較小。',
  },
  W15: {
    role: '近距集中霰彈',
    description:
      '泵動前護木與管狀供彈。每次發射八顆散射彈丸，近距離讓多顆同時命中；兩次射擊間需等待泵動。',
  },
  W16: {
    role: '半自動霰彈',
    description:
      '粗槍管與大型旋鼓。每次按下發射八顆彈丸，可較快再次射擊；單顆傷害及射程低於泵動型。',
  },
  W17: {
    role: '遠距狙擊',
    description:
      '細長槍管、長瞄具與側槍機。高倍率瞄準與遠距單發火力；每次射擊後等待拉栓，適合有掩護的精準狙擊。',
  },
  W18: {
    role: '重型遠距狙擊',
    description:
      '粗長槍管、大型制退器與雙腳架。高單發傷害、長射程，代價是慢拉栓、少彈量與較長換彈。',
  },
  W19: {
    role: '大範圍爆破',
    description:
      '粗火箭管與外露彈頭。火箭沿發射方向直飛，碰撞後造成範圍傷害，適合成群地面敵人；每關有發射配額。',
  },
  W20: {
    role: '快速輕火箭',
    description:
      '細發射管、折疊支架與前方護環。火箭較快、射程較長、每關配額更多；爆炸傷害和半徑比彗星小。',
  },
};
export const ARMOR_DETAILS: Record<string, string> = {
  A01: '柔軟的棉雲背包，提高自動回復速度，生命與移動速度保持基準。適合撤回掩護後迅速恢復。',
  A02: '糖晶肩甲能減少每次受到的傷害，代價是移動速度降低 10%。適合守住固定位置。',
  A03: '果凍胸甲同時增加生命、提供少量減傷並加快回復，移速不變，是均衡的防守選擇。',
  A04: '輕羽鞋翼讓移動速度提高 20%，但生命上限減少 10。適合頻繁移動、尋找射線和掩護。',
  A05: '蜜糖厚胸背增加大量生命，移動速度降低 5%。適合承受較多傷害後退回掩護。',
  A06: '晨露腕環縮短停止受傷後的回復等待，生命和移速不變，適合多次短暫脫離交火。',
};
export const TURRET_DETAILS: Record<string, string> = {
  T01: '雙管自動機槍塔，優先射擊範圍內可見的最近落地敵兵，適合守住入口。地面首領最多削至半血，剩餘由玩家處理。',
  T02: '帶長槍管與瞄具的狙擊塔，以慢射速換取高傷害和遠射程；只打落地敵兵。地面首領最多削至半血，剩餘由玩家處理。',
  T03: '雙側飛彈箱與頂部雷達，鎖定最近的可見敵機後發射追蹤飛彈，負責空中攔截。',
};
export const UPGRADE_DETAILS: Record<string, string> = {
  damage:
    '強化這一把武器的傷害。每級增加原始傷害的 25%；霰彈槍會強化每一顆彈丸。',
  cooldown:
    '縮短這一把武器的射擊間隔。每級減少原始間隔的 5%；點放武器也縮短兩輪點放的等待。換彈與鎖定時間不受影響。',
  range:
    '延長這一把狙擊槍的有效射程，每級增加 30 m，讓更遠的地面目標也能被擊中。',
  lock_time:
    '改善這一把防空炮的鎖定演算，每級縮短基礎鎖定時間 0.15 秒。配件的時間倍率會一起計算。',
  whitebox:
    '擴大這一把防空炮的鎖定白框，每級增加原始框尺寸的 10%，讓移動中的敵機較容易留在框內。',
  aim_assist:
    '開啟這一把防空炮的瞄準輔助。鎖定時輔助視角追隨候選敵機，仍需完成鎖定並自行射擊。',
};
export function attachmentDescription(id: string, category: string) {
  const descriptions: Record<string, string> = {
    zoom_scope: '瞄準倍率 ×1.5，換彈時間 ×1.1。看得更近，但換彈較慢。',
    guidance_scope:
      category === 'anti_air'
        ? '鎖定框尺寸 ×1.1，鎖定時間也 ×1.1。框更大，但完成鎖定較慢。'
        : '瞄準倍率 ×1.5，換彈時間 ×1.1。只改善瞄準視野，火箭仍沿發射方向直飛。',
    heavy_barrel:
      '傷害 ×1.15，射擊間隔 ×1.1。單發更強，但射速變慢；點放的組間等待也會增加。',
    extended_magazine:
      '彈匣容量 ×1.5（取整數），換彈時間 ×1.2。連續射擊更久，換彈較慢。',
    quick_reload:
      '換彈時間 ×0.8，彈匣容量也 ×0.8（取整數）。換彈更快，但每匣更少。',
    cooling_guidance:
      '發射間隔 ×0.85，鎖定時間 ×1.15。發射冷卻較短，但每次重新鎖定較慢。',
    light_loading_rack:
      '發射間隔與換彈時間 ×0.85，爆炸半徑也 ×0.85。裝填更快，爆炸範圍較小。',
  };
  return descriptions[id];
}
export const STAT_LABELS: Record<string, string> = {
  base_damage: '單發傷害',
  interval: '射擊間隔',
  burst_interval: '兩輪點放間隔',
  range: '有效射程',
  magazine_size: '彈匣容量',
  reload_seconds: '換彈時間',
  pellet_count: '每發彈丸',
  spread_angle: '散射角',
  lock_seconds: '鎖定時間',
  lock_box_scale: '鎖定框尺寸',
  aim_assist: '瞄準輔助',
  aim_factor: '瞄準倍率',
  quota: '每關配額',
  projectile_speed: '彈體速度',
  blast_radius: '爆炸半徑',
  max_hp: '生命上限',
  move_speed: '移動速度',
  jump_height: '跳躍高度',
  damage_reduction: '每次減傷',
  regen_delay: '回復等待',
  regen_rate: '每秒回復',
  regen_budget: '每關回復上限',
};
export const number = (v: number) =>
  new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 3 }).format(v);
export function statValue(key: string, value: any) {
  if (typeof value === 'boolean') return value ? '開啟' : '關閉';
  if (value === null) return '無限制';
  if (
    [
      'interval',
      'burst_interval',
      'reload_seconds',
      'lock_seconds',
      'regen_delay',
    ].includes(key)
  )
    return number(value) + ' 秒';
  if (['range', 'blast_radius', 'jump_height'].includes(key))
    return number(value) + ' m';
  if (['move_speed', 'projectile_speed'].includes(key))
    return number(value) + ' m/s';
  if (['lock_box_scale', 'aim_factor'].includes(key))
    return '×' + number(value);
  if (['magazine_size', 'quota'].includes(key)) return number(value) + ' 發';
  if (key === 'spread_angle') return number(value) + '°';
  return number(value);
}
export function relevantChanges(changes: any, definition?: any) {
  return Object.entries(changes || {}).filter(
    ([key]) =>
      STAT_LABELS[key] &&
      (key !== 'burst_interval' || definition?.fire_mode === 'burst'),
  );
}
export function weaponRows(def: any, stats: any): [string, string][] {
  const rows: [string, string][] = [
    [
      stats.pellet_count > 1
        ? '單顆傷害 × 彈丸'
        : def.category === 'anti_air'
          ? '每枚飛彈傷害'
          : '單發傷害',
      stats.pellet_count > 1
        ? `${number(stats.base_damage)} × ${stats.pellet_count}`
        : number(stats.base_damage),
    ],
    [
      def.category === 'anti_air'
        ? '發射冷卻上限'
        : def.fire_mode === 'burst'
          ? '點放內射速'
          : '理論最高射速',
      `${number(1 / stats.interval)} ${def.category === 'anti_air' ? '次' : '發'}／秒`,
    ],
    ['射擊間隔', statValue('interval', stats.interval)],
    [
      def.category === 'anti_air' ? '鎖定射程' : '有效射程',
      statValue('range', stats.range),
    ],
  ];
  if (def.fire_mode === 'burst')
    rows.push([
      '點放節奏',
      `每組 3 發 · 每 ${number(stats.burst_interval)} 秒可起一組`,
    ]);
  if (def.category === 'anti_air')
    rows.push(
      ['鎖定時間', statValue('lock_seconds', stats.lock_seconds)],
      ['鎖定框尺寸', statValue('lock_box_scale', stats.lock_box_scale)],
      ['飛彈速度', statValue('projectile_speed', stats.projectile_speed)],
      ['彈量', '無限 · 每次重新鎖定'],
    );
  else
    rows.push(
      [
        '彈匣 / 換彈',
        `${stats.magazine_size} 發 / ${number(stats.reload_seconds)} 秒`,
      ],
      ['瞄準倍率', statValue('aim_factor', stats.aim_factor)],
    );
  if (def.category === 'rocket')
    rows.push(
      ['每關發射配額', statValue('quota', stats.quota)],
      ['爆炸半徑', statValue('blast_radius', stats.blast_radius)],
      ['火箭速度', statValue('projectile_speed', stats.projectile_speed)],
    );
  if (stats.pellet_count > 1)
    rows.push(['散射角', statValue('spread_angle', stats.spread_angle)]);
  return rows;
}
