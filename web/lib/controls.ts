export type ControlMode = 'mouse' | 'keyboard' | 'touch';
export const CONTROL_MODES = [
  ['mouse', '滑鼠視角'],
  ['keyboard', '鍵盤視角'],
  ['touch', '觸控'],
] as const;
export const KEY_ACTIONS: Record<string, string> = {
  Space: 'jump',
  KeyR: 'reload',
  KeyQ: 'toggle_aim',
};
export const MOVEMENT_KEYS = {
  left: 'KeyA',
  right: 'KeyD',
  forward: 'KeyW',
  back: 'KeyS',
} as const;
export const CONTROL_ROWS = [
  { action: '移動', desktop: 'W / A / S / D', touch: '左側移動區拖曳' },
  {
    action: '視角',
    desktop: '移動滑鼠；鍵盤模式用方向鍵',
    touch: '右側視角區拖曳',
  },
  {
    action: '射擊',
    desktop: '滑鼠左鍵 / F',
    touch: '按住「射擊」；半自動武器逐次點按',
  },
  { action: '切換瞄準', desktop: '滑鼠右鍵 / Q', touch: '點按「瞄準」' },
  { action: '跳躍', desktop: 'Space', touch: '點按「跳躍」' },
  { action: '換彈', desktop: 'R', touch: '點按「換彈」' },
  {
    action: '切換武器',
    desktop: '1–5；鍵盤模式也能點下方武器槽',
    touch: '點按下方武器槽',
  },
  {
    action: '暫停',
    desktop: 'Esc；鍵盤模式也能點「暫停」',
    touch: '點按「暫停」',
  },
  {
    action: '遊玩方法',
    desktop: 'H；或暫停後點「遊玩方法」',
    touch: '點按「遊玩方法」',
  },
] as const;
export function validMode(value: unknown): value is ControlMode {
  return CONTROL_MODES.some(([id]) => id === value);
}
export function isEditable(target: any) {
  return !!target?.closest?.(
    'input,textarea,select,[contenteditable="true"],[role="combobox"],[role="dialog"],[role="alertdialog"]',
  );
}
export class BattleInput {
  keys = new Set<string>();
  fireSources = new Set<string>();
  commands: any[] = [];
  look: [number, number] = [0, 0];
  sequence = 0;
  touches = new Map<number, { role: 'move' | 'look'; x: number; y: number }>();
  move: [number, number] = [0, 0];
  enabled = false;
  enqueue(kind: string, value: number | null = null) {
    if (this.enabled)
      this.commands.push({ sequence: ++this.sequence, kind, value });
  }
  start() {
    this.clear();
    this.enabled = true;
    this.enqueue('fire_up');
  }
  clear() {
    this.enabled = false;
    this.keys.clear();
    this.fireSources.clear();
    this.commands = [];
    this.look = [0, 0];
    this.touches.clear();
    this.move = [0, 0];
  }
  fireDown(source: string) {
    if (!this.enabled || this.fireSources.has(source)) return;
    this.fireSources.add(source);
    if (this.fireSources.size === 1) this.enqueue('fire_down');
  }
  fireUp(source: string) {
    if (this.fireSources.delete(source) && this.fireSources.size === 0)
      this.enqueue('fire_up');
  }
  keyDown(code: string, repeat = false) {
    if (!this.enabled) return;
    this.keys.add(code);
    if (repeat) return;
    if (code === 'KeyF') this.fireDown('keyboard');
    else if (KEY_ACTIONS[code]) this.enqueue(KEY_ACTIONS[code]);
    else if (/^Digit[1-5]$/.test(code))
      this.enqueue('select_slot', Number(code.slice(-1)));
  }
  keyUp(code: string) {
    this.keys.delete(code);
    if (code === 'KeyF') this.fireUp('keyboard');
  }
  touchDown(id: number, role: 'move' | 'look', x: number, y: number) {
    if (
      !this.enabled ||
      [...this.touches.values()].some((t) => t.role === role)
    )
      return;
    this.touches.set(id, { role, x, y });
  }
  touchMove(id: number, x: number, y: number, sensitivity = 1) {
    const t = this.touches.get(id);
    if (!t || !this.enabled) return;
    const dx = x - t.x,
      dy = y - t.y;
    if (t.role === 'move') {
      this.move = [
        Math.max(-1, Math.min(1, dx / 45)),
        Math.max(-1, Math.min(1, -dy / 45)),
      ];
    } else {
      this.look[0] += dx * 0.16 * sensitivity;
      this.look[1] += dy * 0.16 * sensitivity;
      t.x = x;
      t.y = y;
    }
  }
  releasePointer(id: number) {
    const t = this.touches.get(id);
    if (t?.role === 'move') this.move = [0, 0];
    this.touches.delete(id);
    this.fireUp('pointer:' + id);
  }
  frame(dt: number, sensitivity = 1) {
    const out = {
      commands: this.commands,
      look_delta: [
        this.look[0] +
          (Number(this.keys.has('ArrowRight')) -
            Number(this.keys.has('ArrowLeft'))) *
            70 *
            dt *
            sensitivity,
        this.look[1] +
          (Number(this.keys.has('ArrowDown')) -
            Number(this.keys.has('ArrowUp'))) *
            70 *
            dt *
            sensitivity,
      ],
      move_x: Math.max(
        -1,
        Math.min(
          1,
          Number(this.keys.has(MOVEMENT_KEYS.right)) -
            Number(this.keys.has(MOVEMENT_KEYS.left)) +
            this.move[0],
        ),
      ),
      move_z: Math.max(
        -1,
        Math.min(
          1,
          Number(this.keys.has(MOVEMENT_KEYS.forward)) -
            Number(this.keys.has(MOVEMENT_KEYS.back)) +
            this.move[1],
        ),
      ),
    };
    this.commands = [];
    this.look = [0, 0];
    return out;
  }
}
