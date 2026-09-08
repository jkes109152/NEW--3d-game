import type { MultiplayerClient } from './multiplayer-client.ts';
import type {
  PvpSnapshot,
  PvpView,
  PvpActor,
  PredictionFrame,
} from './pvp-types.ts';
import { PVP_STEP, neutralInput } from './pvp-types.ts';
import {
  PvpControls,
  loadFlightSettings,
  saveFlightSettings,
  PredictionHistory,
} from './pvp-controls.ts';
import { PvpScene } from './pvp-scene';
import { isEditable } from './controls';
import type { WebGLRenderer } from 'three';

export class PvpSession {
  room: any = null;
  view: PvpView | null = null;
  packet: PvpSnapshot | null = null;
  controls = new PvpControls();
  settingsOpen = false;
  error = '';
  spectator: string | null = null;
  private receivedAt = 0;
  private run = '';
  private methods: Record<string, any> = {};
  private lastSimAt: number | null = null;
  private aborting = false;
  private scene: PvpScene;
  private off: (() => void)[] = [];
  private history = new PredictionHistory();
  private predicted: PvpActor | null = null;
  private predictionRemainder = 0;
  private predictTick = 0;
  private lastAuthority = -1;
  private overflow = false;
  private cancelCapture: (() => void) | null = null;
  private ended = false;
  private frameTimes: number[] = [];
  constructor(
    private py: any,
    private client: MultiplayerClient,
    private renderer: WebGLRenderer,
    private host: HTMLElement,
    catalog: any,
  ) {
    for (const name of ['pvp_start', 'pvp_tick', 'pvp_predict', 'pvp_dispose'])
      this.methods[name] = py.globals.get(name);
    const prefs = loadFlightSettings(localStorage);
    this.controls.settings = prefs.settings;
    this.controls.camera = prefs.settings.camera;
    this.error = prefs.error;
    this.scene = new PvpScene(renderer, host, catalog);
    const listen = (target: EventTarget, name: string, fn: any) => {
      target.addEventListener(name, fn);
      this.off.push(() => target.removeEventListener(name, fn));
    };
    listen(window, 'keydown', (e: KeyboardEvent) => {
      if (isEditable(e.target)) return;
      if (e.code === 'Escape') {
        this.openSettings();
        return;
      }
      if (e.code === 'Tab' && !this.me()?.alive) {
        e.preventDefault();
        this.nextSpectator();
        return;
      }
      if (
        [
          'ArrowUp',
          'ArrowDown',
          'ArrowLeft',
          'ArrowRight',
          'Space',
          'KeyW',
          'KeyA',
          'KeyS',
          'KeyD',
          'KeyQ',
          'KeyE',
          'KeyV',
          'KeyF',
        ].includes(e.code)
      ) {
        if ((e.target as Element)?.closest?.('button,a,[role="button"]'))
          return;
        e.preventDefault();
        this.controls.key(e.code, true);
      }
    });
    listen(window, 'keyup', (e: KeyboardEvent) =>
      this.controls.key(e.code, false),
    );
    listen(window, 'blur', () => this.suspend());
    listen(document, 'visibilitychange', () => {
      if (document.hidden) this.suspend();
    });
    listen(document, 'pointerlockchange', () => {
      if (document.pointerLockElement !== renderer.domElement) this.suspend();
    });
    listen(document, 'mousemove', (e: MouseEvent) => {
      if (document.pointerLockElement === renderer.domElement)
        this.controls.mouse(e.movementX, e.movementY);
    });
    listen(renderer.domElement, 'mousedown', (e: MouseEvent) => {
      if (!this.controls.enabled || this.me()?.team !== 'ground') return;
      if (e.button === 0) this.controls.command('fire_down');
      if (e.button === 2) this.controls.command('toggle_aim');
    });
    listen(window, 'mouseup', (e: MouseEvent) => {
      if (e.button === 0) this.controls.command('fire_up');
    });
  }
  private me() {
    return this.view?.actors.find((a) => a.id === this.client.me?.id);
  }
  invoke(name: string, value: any = {}) {
    return JSON.parse(this.methods[name](JSON.stringify(value)));
  }
  receive(room: any) {
    this.room = room;
    this.receivedAt = performance.now();
    if (
      room.runId &&
      room.runId !== this.run &&
      ['countdown', 'playing'].includes(room.status)
    ) {
      this.run = room.runId;
      this.lastSimAt = null;
      this.history.clear();
      this.lastAuthority = -1;
      this.predictTick = 0;
      this.predicted = null;
      if (
        room.hostId === this.client.me?.id &&
        room.hostInstanceId === this.client.instanceId
      )
        this.packet = this.invoke('pvp_start', {
          runId: room.runId,
          roster: room.roster,
          timeLimitSeconds: room.timeLimitSeconds,
        });
    }
    const host = room.hostId === this.client.me?.id;
    const next = host
      ? (this.packet?.views[this.client.me?.id] ?? room.view)
      : room.view;
    if (next) {
      this.view = next;
      if (!host && next.tick > this.lastAuthority) {
        const actor = next.actors.find(
          (a: PvpActor) => a.id === this.client.me?.id,
        );
        const stream = this.client.pvpControlState().stream;
        if (actor && next.inputAck.stream === stream) {
          if (this.history.stream && this.history.stream !== stream) {
            this.history.clear();
            this.controls.suspend();
            this.predictTick = next.tick;
          }
          const remaining = this.history.after(next.tick, stream);
          this.predicted = this.invoke('pvp_predict', {
            actor,
            frames: remaining,
          });
          this.predictTick = Math.max(this.predictTick, next.tick);
          this.lastAuthority = next.tick;
          if (this.overflow && !this.client.pvpControlState().waiting) {
            this.overflow = false;
            this.history.clear();
            this.controls.suspend();
          }
        }
      }
    }
    if (this.me() && !this.me()!.alive) {
      this.suspend();
      this.ensureSpectator();
    }
    if (room.status === 'finished' && !this.ended) {
      this.ended = true;
      this.suspend();
      this.history.clear();
    }
  }
  private ensureSpectator() {
    const team = this.me()?.team;
    const available =
      this.view?.actors.filter((a) => a.alive && a.team === team) || [];
    if (!available.some((a) => a.id === this.spectator))
      this.spectator = available[0]?.id || null;
  }
  nextSpectator() {
    this.ensureSpectator();
    const list =
      this.view?.actors.filter((a) => a.alive && a.team === this.me()?.team) ||
      [];
    this.spectator =
      list[(list.findIndex((a) => a.id === this.spectator) + 1) % list.length]
        ?.id || null;
  }
  suspend() {
    this.controls.suspend();
    this.client.setInput({ suspended: true });
    if (document.pointerLockElement === this.renderer.domElement)
      document.exitPointerLock();
  }
  openSettings() {
    this.suspend();
    this.settingsOpen = true;
  }
  async begin() {
    this.settingsOpen = false;
    if (!this.me()?.alive || this.room.status !== 'playing') return;
    try {
      if (this.controls.settings.mode === 'mouse') {
        await new Promise<void>((resolve, reject) => {
          const cleanup = () => {
            this.cancelCapture = null;
            clearTimeout(timer);
            document.removeEventListener('pointerlockchange', changed);
            document.removeEventListener('pointerlockerror', failed);
          };
          const changed = () => {
            if (document.pointerLockElement === this.renderer.domElement) {
              cleanup();
              resolve();
            }
          };
          const failed = () => {
            cleanup();
            reject(Error('pointer-lock'));
          };
          const timer = setTimeout(failed, 1500);
          this.cancelCapture = failed;
          document.addEventListener('pointerlockchange', changed);
          document.addEventListener('pointerlockerror', failed);
          try {
            Promise.resolve(this.renderer.domElement.requestPointerLock()).then(
              changed,
              failed,
            );
          } catch {
            failed();
          }
        });
      }
      this.renderer.domElement.tabIndex = 0;
      this.renderer.domElement.focus();
      this.controls.enable();
      this.error = '';
    } catch {
      this.error = '無法取得滑鼠控制，請重試或改用鍵盤駕駛。';
      this.controls.suspend();
    }
  }
  configure(patch: any) {
    this.suspend();
    this.controls.settings = { ...this.controls.settings, ...patch };
    this.controls.camera = this.controls.settings.camera;
    this.error = saveFlightSettings(localStorage, this.controls.settings);
  }
  private abort(reason: string) {
    if (this.aborting) return;
    this.aborting = true;
    this.suspend();
    void this.client.action('abort', { reason });
  }
  frame(now: number, dt: number) {
    this.frameTimes.push(dt);
    if (this.frameTimes.length > 120) this.frameTimes.shift();
    if (!this.room) return;
    const isHost = this.room.hostId === this.client.me?.id;
    if (this.room.connectionLost) this.suspend();
    if (this.room.status === 'playing' && this.view?.phase === 'active') {
      const me = this.me();
      const frame = this.controls.frame(
        dt,
        this.host.clientWidth / this.host.clientHeight,
        me?.team || 'ground',
      );
      this.client.setInput(frame);
      const local = this.client.pvpControlState();
      if (local.evicted) {
        this.suspend();
        this.error = '另一分頁已取得控制，請離開此對戰。';
      }
      if (isHost) {
        if (this.lastSimAt === null)
          this.lastSimAt =
            this.receivedAt - (this.room.serverNow - this.room.startsAt);
        const elapsed = (now - this.lastSimAt) / 1000;
        if (elapsed > 1) {
          this.abort('simulation_gap');
          return;
        }
        const frames: Record<string, any> = {};
        for (const member of this.room.hostInputs || []) {
          const age =
            this.room.serverNow +
            now -
            this.receivedAt -
            (member.inputReceivedAt ?? -Infinity);
          frames[member.playerId] = {
            ...neutralInput(),
            ...member.input,
            stream: member.inputStream || '',
            inputSeq: member.inputSeq,
            suspended: age >= 1000 || member.input.suspended !== false,
          };
        }
        frames[this.client.me.id] = {
          ...local.input,
          stream: local.stream,
          inputSeq: local.inputSeq,
        };
        try {
          this.packet = this.invoke('pvp_tick', {
            dt: Math.max(0, elapsed),
            frames,
            departedIds: Object.keys(this.room.departures || {}),
          });
          this.lastSimAt = now;
          this.view = this.packet!.views[this.client.me.id];
          this.client.setSnapshot(this.packet);
        } catch {
          this.abort('simulation_error');
          return;
        }
      } else if (me && local.stream && !this.overflow) {
        if (!this.predicted) {
          this.predicted = structuredClone(me);
          this.predictTick = this.view.tick;
        }
        this.predictionRemainder += dt;
        const batch: PredictionFrame[] = [];
        while (this.predictionRemainder >= PVP_STEP) {
          this.predictionRemainder -= PVP_STEP;
          const item: PredictionFrame = {
            runId: this.run,
            stream: local.stream,
            tick: ++this.predictTick,
            dt: PVP_STEP,
            inputSeqAtCapture: local.inputSeq,
            input: structuredClone(local.input) as any,
          };
          if (!this.history.push(item)) {
            this.overflow = true;
            this.suspend();
            this.error = '連線延遲，正在同步';
            break;
          }
          batch.push(item);
        }
        if (batch.length && !this.overflow)
          this.predicted = this.invoke('pvp_predict', {
            actor: this.predicted,
            frames: batch,
          });
      }
    }
    if (this.view) {
      this.ensureSpectator();
      this.scene.render(
        this.view,
        isHost ? this.me() || null : this.predicted,
        this.controls.camera,
        this.spectator,
        Math.min(dt, 0.1),
      );
    }
  }
  fail() {
    this.error = '戰場無法繼續，正在確認對戰中止。';
    this.abort('simulation_error');
  }
  state() {
    return {
      room: this.room,
      view: this.view,
      settings: this.controls.settings,
      camera: this.controls.camera,
      settingsOpen: this.settingsOpen,
      controlling: this.controls.enabled,
      error: this.error,
      spectator: this.spectator,
      diagnostics: {
        listeners: this.off.length,
        predictionSteps: this.history.size,
        fps:
          this.frameTimes.length /
          (this.frameTimes.reduce((a, b) => a + b, 0) || 1),
        geometries: this.renderer.info.memory.geometries,
        textures: this.renderer.info.memory.textures,
      },
      countdown: Math.max(
        0,
        Math.ceil(
          ((this.room?.startsAt || 0) -
            (this.room?.serverNow || 0) -
            (performance.now() - this.receivedAt)) /
            1000,
        ),
      ),
    };
  }
  dispose() {
    this.cancelCapture?.();
    this.suspend();
    for (const off of this.off) off();
    this.off = [];
    this.scene.dispose();
    this.invoke('pvp_dispose');
    for (const fn of Object.values(this.methods)) fn.destroy();
    this.history.clear();
  }
}
