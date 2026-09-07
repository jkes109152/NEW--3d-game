import { PerspectiveCamera, Vector3 } from 'three';
export type Point = { x: number; y: number };
export function projectAircraft(
  position: number[],
  camera: PerspectiveCamera,
  width: number,
  height: number,
): Point | null {
  const world = new Vector3(position[0], position[1], -position[2]);
  if (world.clone().applyMatrix4(camera.matrixWorldInverse).z >= 0) return null;
  const projected = world.project(camera);
  if (
    Math.abs(projected.x) > 1 ||
    Math.abs(projected.y) > 1 ||
    projected.z < -1 ||
    projected.z > 1
  )
    return null;
  return {
    x: ((projected.x + 1) * width) / 2,
    y: ((1 - projected.y) * height) / 2,
  };
}
export function movingReticle(
  center: Point,
  target: Point,
  progress: number,
  size: number,
): Point {
  const clamp = (v: number) => Math.max(-size / 2, Math.min(size / 2, v));
  return {
    x: center.x + clamp((target.x - center.x) * progress),
    y: center.y + clamp((target.y - center.y) * progress),
  };
}
type Box = Point & { w: number; h: number };
const overlaps = (a: Box, b: Box) =>
  a.x < b.x + b.w + 5 &&
  a.x + a.w + 5 > b.x &&
  a.y < b.y + b.h + 5 &&
  a.y + a.h + 5 > b.y;
export function labelPosition(
  point: Point,
  width: number,
  height: number,
  occupied: Box[],
  targets: Point[],
  reserved: Box[],
  previous?: Box,
): Box {
  const w = width < 550 ? 98 : 114,
    h = 24;
  const candidates: Box[] = [];
  if (previous && Math.hypot(previous.x - point.x, previous.y - point.y) < 160)
    candidates.push(previous);
  for (const [x, y] of [
    [point.x + 29, point.y - 12],
    [point.x - w - 29, point.y - 12],
    [point.x - w / 2, point.y - 49],
    [point.x - w / 2, point.y + 28],
  ])
    candidates.push({ x, y, w, h });
  const slots: Box[] = [];
  for (let y = 64; y < height - 125; y += 30)
    for (let x = 12; x + w < width - 8; x += w + 12) slots.push({ x, y, w, h });
  slots.sort(
    (a, b) =>
      Math.hypot(a.x - point.x, a.y - point.y) -
      Math.hypot(b.x - point.x, b.y - point.y),
  );
  candidates.push(...slots);
  return (
    candidates.find(
      (box) =>
        box.x >= 8 &&
        box.x + box.w <= width - 8 &&
        box.y >= 56 &&
        box.y + box.h <= height - 105 &&
        !occupied.some((v) => overlaps(v, box)) &&
        !reserved.some((v) => overlaps(v, box)) &&
        !targets.some((v) =>
          overlaps({ x: v.x - 20, y: v.y - 20, w: 40, h: 40 }, box),
        ),
    ) || {
      x: Math.max(8, Math.min(width - w - 8, point.x + 24)),
      y: Math.max(56, Math.min(height - 130, point.y + 26)),
      w,
      h,
    }
  );
}
const corners = (x: number, y: number, size: number, l: number) =>
  `M${x + l} ${y}H${x}V${y + l}M${x + size - l} ${y}H${x + size}V${y + l}M${x} ${y + size - l}V${y + size}H${x + l}M${x + size - l} ${y + size}H${x + size}V${y + size - l}`;
const colors = {
  waiting: '#f1f7ed',
  tracking: '#ffd58e',
  locked: '#9cecd5',
  lost: '#b6c3d3',
};
export class AntiAirHud {
  root: HTMLDivElement;
  private identity = '';
  private numbers = new Map<string, number>();
  private labels = new Map<string, Box>();
  private memory = new Map<string, Point>();
  private completed = new Set<string>();
  private pulses = new Map<string, number>();
  private shotSequence = 0;
  private shotUntil = 0;
  private shotCount = 0;
  private groupWasReady = false;
  private groupPulseUntil = 0;
  constructor(host: HTMLElement) {
    this.root = document.createElement('div');
    this.root.className = 'aa-hud';
    this.root.setAttribute('role', 'img');
    this.root.setAttribute('aria-label', '防空炮取得範圍與目標鎖定狀態');
    this.root.hidden = true;
    host.appendChild(this.root);
  }
  clear() {
    this.numbers.clear();
    this.labels.clear();
    this.memory.clear();
    this.completed.clear();
    this.pulses.clear();
    this.shotUntil = 0;
    this.groupWasReady = false;
  }
  update(b: any, camera: PerspectiveCamera, width: number, height: number) {
    if (!b || b.weapon_category !== 'anti_air') {
      this.root.hidden = true;
      this.clear();
      this.identity = '';
      return;
    }
    this.root.hidden = false;
    const identity = b.attempt_id + ':' + b.active_weapon_id;
    if (identity !== this.identity) {
      this.clear();
      this.identity = identity;
      this.shotSequence = 0;
    }
    if (!b.aiming) this.clear();
    const size = 0.21 * height * b.lock_box_scale,
      cx = width / 2,
      cy = height / 2,
      x = cx - size / 2,
      y = cy - size / 2;
    const multi = b.fire_mode === 'lock_multi',
      valid = new Set<string>(b.lock_valid),
      alive = new Set<string>();
    const targets: {
      id: string;
      p: number;
      valid: boolean;
      point: Point;
      number: number;
    }[] = [];
    for (const a of b.aircraft) {
      if (a.hp <= 0 || a.status !== 'approaching') continue;
      alive.add(a.id);
      if (!b.aiming || (!valid.has(a.id) && !(b.locks[a.id] > 0))) continue;
      if (!multi && a.id !== b.lock_current) continue;
      const point = projectAircraft(a.position, camera, width, height);
      if (!point) continue;
      if (!this.numbers.has(a.id))
        this.numbers.set(a.id, this.numbers.size + 1);
      if (valid.has(a.id)) this.memory.set(a.id, point);
      targets.push({
        id: a.id,
        p: (b.locks[a.id] || 0) >= 1 - 1e-9 ? 1 : b.locks[a.id] || 0,
        valid: valid.has(a.id),
        point,
        number: this.numbers.get(a.id)!,
      });
    }
    for (const key of this.memory.keys())
      if (!alive.has(key)) {
        this.memory.delete(key);
        this.labels.delete(key);
        this.completed.delete(key);
        this.pulses.delete(key);
      }
    const pool = b.lock_valid.filter((id: string) => alive.has(id)),
      locked = pool.filter(
        (id: string) => (b.locks[id] || 0) >= 1 - 1e-9,
      ).length;
    const ready =
      b.aiming &&
      pool.length > 0 &&
      locked === pool.length &&
      !b.fire_blocked &&
      b.phase === 'active';
    if (ready && !this.groupWasReady) this.groupPulseUntil = b.elapsed + 0.3;
    this.groupWasReady = ready;
    for (const e of b.events || [])
      if (
        e.kind === 'weapon_fire' &&
        e.weapon_id === b.active_weapon_id &&
        e.sequence > this.shotSequence
      ) {
        this.shotSequence = e.sequence;
        this.shotUntil = b.elapsed + 0.8;
        this.shotCount = e.endpoints.length;
      }
    let svg = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true"><path class="aa-acquire" d="${corners(x, y, size, Math.min(24, size * 0.13))}"/><text class="aa-frame-label" x="${x}" y="${y - 12}">取得範圍</text>`;
    const single = targets[0],
      progress = single?.p || 0;
    const reserved: Box[] = [
      { x: cx - 125, y: y + size + 7, w: 250, h: 68 },
      { x: 0, y: 75, w: 270, h: 110 },
      { x: width - 280, y: 75, w: 280, h: 110 },
    ];
    const occupied: Box[] = [];
    if (b.aiming) {
      if (!multi && !single)
        svg += `<path class="aa-idle" d="M${cx - 7} ${cy}h4M${cx + 3} ${cy}h4M${cx} ${cy - 7}v4M${cx} ${cy + 3}v4"/>`;
      for (const t of targets) {
        const done = t.valid && t.p >= 1 - 1e-9,
          color = !t.valid
            ? colors.lost
            : done
              ? colors.locked
              : colors.tracking;
        if (done && !this.completed.has(t.id))
          this.pulses.set(t.id, b.elapsed + 0.22);
        if (done) this.completed.add(t.id);
        else this.completed.delete(t.id);
        const point = multi
          ? t.point
          : movingReticle(
              { x: cx, y: cy },
              t.valid ? t.point : this.memory.get(t.id) || t.point,
              t.p,
              size,
            );
        const radius = 14,
          circumference = 2 * Math.PI * radius;
        const pulse = Math.max(
          0,
          ((this.pulses.get(t.id) || 0) - b.elapsed) / 0.22,
        );
        svg += `<g class="aa-mark ${done ? 'aa-complete' : !t.valid ? 'aa-lost' : ''}" style="color:${color}" transform="translate(${point.x} ${point.y})">${done ? '<rect x="-19" y="-19" width="38" height="38" rx="9"/>' : `<path d="${corners(-19, -19, 38, 7)}"/>`}<circle class="aa-track" r="${radius}"/><circle class="aa-progress" r="${radius}" stroke-dasharray="${t.p * circumference} ${circumference}" transform="rotate(-90)"/>${done ? '<text x="22" y="-16">✓</text>' : ''}${pulse > 0 ? `<circle class="aa-confirm-pulse" r="${24 + (1 - pulse) * 8}" style="opacity:${pulse * 0.6}"/>` : ''}</g>`;
        if (multi) {
          const box = labelPosition(
            t.point,
            width,
            height,
            occupied,
            targets.map((v) => v.point),
            reserved,
            this.labels.get(t.id),
          );
          this.labels.set(t.id, box);
          occupied.push(box);
          const endX = Math.max(
              box.x + 5,
              Math.min(box.x + box.w - 5, t.point.x),
            ),
            endY = Math.max(box.y + 4, Math.min(box.y + box.h - 4, t.point.y));
          svg += `<path class="aa-leader" stroke="${color}" d="M${t.point.x} ${t.point.y}L${endX} ${endY}"/><rect class="aa-label-bg" x="${box.x}" y="${box.y}" width="${box.w}" height="${box.h}" rx="5"/><text class="aa-target-label" fill="${color}" x="${box.x + 7}" y="${box.y + 16}">目標 ${t.number} ${!t.valid ? '失鎖' : done ? '鎖定' : Math.floor(t.p * 100) + '%'}</text>`;
        }
      }
    }
    svg += '</svg>';
    let title = '未鎖定',
      detail = '將可見敵機納入取得框',
      color = colors.waiting;
    if (!b.aiming) {
      title = '尚未瞄準';
      detail = '右鍵／Q／瞄準按鈕 開啟鎖定';
    } else if (multi) {
      title = `已鎖定 ${locked}／${pool.length}`;
      detail = ready
        ? '全部完成・可齊射'
        : pool.length && locked === pool.length
          ? '已鎖定・等待武器就緒'
          : pool.length
            ? '每架獨立鎖定'
            : '等待有效目標';
      color =
        locked && locked === pool.length ? colors.locked : colors.tracking;
    } else if (single) {
      title = `${!single.valid ? '失去目標' : progress >= 1 - 1e-9 ? '已鎖定' : '鎖定中'} ${Math.floor(progress * 100)}%`;
      detail = !single.valid
        ? '禁止發射・追蹤記憶衰減中'
        : ready
          ? '目標有效・可發射'
          : progress >= 1 - 1e-9
            ? '已鎖定・等待武器就緒'
            : `目標 ${single.number}・鎖定 ${b.lock_seconds.toFixed(1)} 秒`;
      color = !single.valid
        ? colors.lost
        : progress >= 1 - 1e-9
          ? colors.locked
          : colors.tracking;
    }
    const summaryY = Math.min(height - 150, y + size + 14);
    this.root.innerHTML =
      svg +
      `<div class="aa-summary" style="top:${summaryY}px;color:${color}"><strong>${title}</strong>${!multi && single && b.aiming ? `<div class="aa-lock-track"><i style="width:${progress * 100}%"></i></div>` : ''}<span>${detail}</span></div>${ready ? `<div class="aa-ready ${this.groupPulseUntil > b.elapsed ? 'aa-ready-pulse' : ''}" style="top:${summaryY + 66}px">${multi ? '可齊射' : '可發射'}</div>` : ''}${this.shotUntil > b.elapsed && b.aiming ? `<div class="aa-fired" style="top:${summaryY + 66}px">${multi ? '已齊射' : '已發射'} ${this.shotCount} 枚導彈</div>` : ''}`;
  }
  dispose() {
    this.root.remove();
    this.clear();
  }
}
