import { neutralInput } from './pvp-types.ts';
import type { PvpCommand, PvpTeam, PredictionFrame } from './pvp-types.ts';
export interface FlightSettings {
  version: 1;
  mode: 'mouse' | 'keyboard';
  sensitivity: number;
  invertY: boolean;
  camera: 'chase' | 'cockpit';
}
const KEY = 'candy-defense-web:pvp-controls:v1';
const defaults = (): FlightSettings => ({
  version: 1,
  mode: 'mouse',
  sensitivity: 1,
  invertY: false,
  camera: 'chase',
});
function valid(s: any): s is FlightSettings {
  return (
    s &&
    s.version === 1 &&
    ['mouse', 'keyboard'].includes(s.mode) &&
    Number.isFinite(s.sensitivity) &&
    s.sensitivity >= 0.2 &&
    s.sensitivity <= 3 &&
    typeof s.invertY === 'boolean' &&
    ['chase', 'cockpit'].includes(s.camera)
  );
}
export function loadFlightSettings(storage: Pick<Storage, 'getItem'>) {
  try {
    const raw = storage.getItem(KEY);
    if (!raw) return { settings: defaults(), error: '' };
    const value = JSON.parse(raw);
    if (!valid(value)) throw Error();
    return { settings: value, error: '' };
  } catch {
    return {
      settings: defaults(),
      error: '飛行偏好無法讀取，已使用預設；原資料保留。',
    };
  }
}
export function saveFlightSettings(
  storage: Pick<Storage, 'setItem'>,
  settings: FlightSettings,
) {
  try {
    if (!valid(settings)) throw Error();
    storage.setItem(KEY, JSON.stringify(settings));
    return '';
  } catch {
    return '飛行偏好尚未保存，本次設定仍可使用。';
  }
}
export class PvpControls {
  settings = defaults();
  camera: 'chase' | 'cockpit' = 'chase';
  enabled = false;
  private keys = new Set<string>();
  private look = [0, 0];
  private commands: PvpCommand[] = [];
  private sequence = 0;
  enable() {
    this.clear();
    this.enabled = true;
  }
  suspend() {
    this.clear();
    this.enabled = false;
  }
  private clear() {
    this.keys.clear();
    this.look = [0, 0];
    this.commands = [];
  }
  key(code: string, down: boolean) {
    if (!this.enabled) return;
    if (down && this.keys.has(code)) return;
    if (down) this.keys.add(code);
    else this.keys.delete(code);
    if (down && code === 'KeyV')
      this.camera = this.camera === 'chase' ? 'cockpit' : 'chase';
    if (down && code === 'Space') this.command('jump');
    if (down && code === 'KeyQ') this.command('toggle_aim');
    if (code === 'KeyF') this.command(down ? 'fire_down' : 'fire_up');
  }
  command(kind: PvpCommand['kind']) {
    if (this.enabled) this.commands.push({ sequence: ++this.sequence, kind });
  }
  mouse(x: number, y: number) {
    if (this.enabled && Number.isFinite(x) && Number.isFinite(y)) {
      this.look[0] += x;
      this.look[1] += y;
    }
  }
  frame(_dt: number, aspect: number, team: PvpTeam) {
    if (!this.enabled) return { ...neutralInput(), aspect, look_delta: [0, 0] };
    const axis = (positive: string, negative: string) =>
      Number(this.keys.has(positive)) - Number(this.keys.has(negative));
    const air = team === 'air',
      mouse = this.settings.mode === 'mouse';
    const sensitivity = air ? this.settings.sensitivity : 1;
    const invert = air && this.settings.invertY ? -1 : 1;
    const frame = {
      ...neutralInput(),
      suspended: false,
      aspect,
      move_x: air ? 0 : axis('KeyD', 'KeyA'),
      move_z: air ? 0 : axis('KeyW', 'KeyS'),
      turn_x: air && !mouse ? axis('ArrowRight', 'ArrowLeft') : 0,
      turn_y: air && !mouse ? axis('ArrowDown', 'ArrowUp') * invert : 0,
      throttle: air ? axis('KeyW', 'KeyS') : 0,
      roll: air ? axis('KeyE', 'KeyQ') : 0,
      look_delta: mouse
        ? [
            this.look[0] * 0.12 * sensitivity,
            this.look[1] * 0.12 * sensitivity * invert,
          ]
        : air
          ? [0, 0]
          : [
              axis('ArrowRight', 'ArrowLeft') * 90 * _dt,
              axis('ArrowDown', 'ArrowUp') * 90 * _dt,
            ],
      commands: air ? [] : this.commands,
    };
    this.look = [0, 0];
    this.commands = [];
    return frame;
  }
}
export class PredictionHistory {
  private rows: PredictionFrame[] = [];
  get stream() {
    return this.rows[0]?.stream;
  }
  get size() {
    return this.rows.length;
  }
  push(frame: PredictionFrame) {
    const last = this.rows[this.rows.length - 1];
    if (last && (frame.stream !== last.stream || frame.runId !== last.runId))
      this.clear();
    else if (last && frame.tick <= last.tick) return true;
    if (this.rows.length >= 120) return false;
    this.rows.push(frame);
    return true;
  }
  after(tick: number, stream: string) {
    this.rows = this.rows.filter((f) => f.stream === stream && f.tick > tick);
    return this.rows.slice();
  }
  clear() {
    this.rows = [];
  }
}
