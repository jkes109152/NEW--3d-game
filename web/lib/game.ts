// 圖像與輸入適配；命中、經濟及戰役僅由原本 Python 規則決定。
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { registerGameTools } from './agent-tools';
import { ArmoryModels } from './armory-models';
import {
  orientProjectile,
  tracerEndpoints,
  ProjectileTrail,
  worldVector,
} from './projectile-visuals';
import { BattleInput, ControlMode, validMode, isEditable } from './controls';
import { MultiplayerClient } from './multiplayer-client';
import { AntiAirHud } from './aiming-hud';
export async function createGame(
  host: HTMLElement,
  onState: (s: any) => void,
  onLoading: (s: string) => void,
) {
  onLoading('正在載入遊戲環境…');
  const loadPyodide = await new Promise<any>((resolve, reject) => {
    if ((window as any).loadPyodide) {
      resolve((window as any).loadPyodide);
      return;
    }
    const script = document.createElement('script');
    script.src = '/runtime/pyodide.js';
    script.async = true;
    script.onload = () => resolve((window as any).loadPyodide);
    script.onerror = () => reject(Error('遊戲環境下載失敗'));
    document.head.appendChild(script);
  });
  const py = await loadPyodide({ indexURL: '/runtime/' });
  const files = (await fetch('/rules/manifest.json', {
    cache: 'no-store',
  }).then((r) => {
    if (!r.ok) throw Error('遊戲規則下載失敗');
    return r.json();
  })) as string[];
  py.FS.mkdirTree('/home/pyodide/air_defense');
  await Promise.all(
    files.map(async (name: string) => {
      const r = await fetch('/rules/' + name + '.py', { cache: 'no-store' });
      if (!r.ok) throw Error('遊戲規則下載失敗');
      py.FS.writeFile(
        '/home/pyodide/air_defense/' + name + '.py',
        await r.text(),
      );
    }),
  );
  py.runPython(
    await fetch('/bridge.py', { cache: 'no-store' }).then((r) => {
      if (!r.ok) throw Error('遊戲介面下載失敗');
      return r.text();
    }),
  );
  // Storage 存取失敗交由原有交易狀態機阻擋，而不是無聲退回暫存。
  const storage = {
    getItem: (k: string) => localStorage.getItem(k),
    setItem: (k: string, v: string) => localStorage.setItem(k, v),
    removeItem: (k: string) => localStorage.removeItem(k),
  };
  py.globals.get('initialize')(storage);
  const invoke = py.globals.get('dispatch'),
    read = py.globals.get('state_json');
  const catalog = JSON.parse(py.globals.get('catalog_json')());
  let state = JSON.parse(read()),
    disposed = false,
    muted = false,
    raf = 0,
    last = performance.now(),
    notifyAt = 0,
    recoil = 0,
    gunId = '',
    requestNumber = 0;
  const input = new BattleInput();
  let partyRun = '',
    partyPacket: any = null,
    partyLocalPaused = true,
    partyPreparing = false,
    partyLeaving = false;
  let partyEventSequence = 0;
  const partyInputs = new Map<string, number>();
  const rewarded = new Set<string>();
  const partyClient = new MultiplayerClient(() => publish(), receivePartyRoom);
  const pyPartyStart = py.globals.get('party_start'),
    pyPartyTick = py.globals.get('party_tick'),
    pyPartyReward = py.globals.get('party_reward');

  let mode: ControlMode = matchMedia('(pointer:coarse)').matches
      ? 'touch'
      : 'mouse',
    pauseReason = 'ready',
    requesting = false,
    sensitivity = 1;
  try {
    const prefs = JSON.parse(
      localStorage.getItem('candy-defense-web:controls') || '{}',
    );
    if (validMode(prefs.mode)) mode = prefs.mode;
    if (typeof prefs.sensitivity === 'number')
      sensitivity = Math.max(0.2, Math.min(3, prefs.sensitivity));
    muted = prefs.muted === true;
  } catch {}
  onLoading('正在建立防線…');
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setSize(host.clientWidth, host.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.appendChild(renderer.domElement);
  const aimingHud = new AntiAirHud(host);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#afd9ed');
  scene.fog = new THREE.Fog('#afd9ed', 160, 480);
  const camera = new THREE.PerspectiveCamera(
    65,
    host.clientWidth / host.clientHeight,
    0.05,
    600,
  );
  scene.add(camera);
  scene.add(new THREE.HemisphereLight('#fff6e4', '#456576', 2));
  const sun = new THREE.DirectionalLight('#fff3d6', 2.5);
  sun.position.set(-70, 100, 60);
  scene.add(sun);
  const geometries: any = {
    round: new RoundedBoxGeometry(1, 1, 1, 2, 0.14),
    sphere: new THREE.SphereGeometry(0.5, 12, 8),
    cylinder: new THREE.CylinderGeometry(0.5, 0.5, 1, 12),
    cone: new THREE.ConeGeometry(0.5, 1, 12),
    ring: new THREE.TorusGeometry(0.36, 0.14, 6, 16),
  };
  const armory = new ArmoryModels();
  await armory.loadPatterns();
  const trails = new Map<string, ProjectileTrail>();
  const materials = new Map<string, THREE.MeshStandardMaterial>();
  function part(
    parent: THREE.Object3D,
    pos: number[],
    scale: number[],
    color: string,
    shape = 'round',
  ) {
    if (!materials.has(color))
      materials.set(
        color,
        new THREE.MeshStandardMaterial({ color, roughness: 0.65 }),
      );
    const m = new THREE.Mesh(
      geometries[shape] || geometries.round,
      materials.get(color),
    );
    m.position.set(pos[0], pos[1], -pos[2]);
    m.scale.set(...(scale as [number, number, number]));
    if (shape === 'cylinder' || shape === 'cone') m.rotation.x = Math.PI / 2;
    parent.add(m);
    return m;
  }
  // 沿用專案世界配置與模型配方；座標 Z 轉為 Three.js 前向。
  part(scene, [0, -0.7, 80], [200, 1, 400], '#a4cdb7');
  part(scene, [0, -0.06, 75], [36, 0.1, 305], '#c5b6df');
  for (let z = -50; z < 230; z += 12)
    part(scene, [0, 0.01, z], [0.25, 0.03, 4], '#fff1bd');
  for (const x of [-60, 60]) part(scene, [x, 1, 80], [1, 2, 320], '#b6d2e7');
  for (const z of [-80, 240]) part(scene, [0, 1, z], [120, 2, 1], '#b6d2e7');
  for (const [x, y, z, w, h, d] of catalog.covers) {
    part(scene, [x, y, z], [w, h, d], '#ecb7d0');
    part(scene, [x, y + h * 0.5, z], [w + 0.25, 0.12, d + 0.25], '#f9dfa6');
  }
  part(scene, [0, 10, -60], [18, 20, 14], '#94cfe2');
  part(scene, [0, 20.2, -60], [20, 0.4, 16], '#f6d493');
  part(scene, [0, 22, -60], [7, 3.2, 7], '#b5a0db');
  for (let y = 2; y < 20; y += 3)
    part(scene, [0, y, -52.95], [17, 0.75, 0.08], '#eef8cf');
  for (const side of [-1, 1])
    for (let z = -72; z < 211; z += 28) {
      const h = 8 + Math.abs(Math.sin(z)) * 9;
      part(scene, [side * 78, h / 2, z], [10, h, 10], '#c1afe1');
      part(scene, [side * 78, h + 0.2, z], [11, 0.4, 11], '#f4cbda');
    }
  const nodes = new Map<string, THREE.Group>(),
    effects: { node: THREE.Object3D; ttl: number }[] = [],
    gun = new THREE.Group();
  camera.add(gun);
  function aircraft(kind: string) {
    const g = new THREE.Group(),
      color = (
        {
          NORMAL: '#e8735e',
          MANPOWER_SUPPORT: '#e2ae61',
          FAST: '#69bee9',
          ARMORED_BOSS: '#bd8ddb',
        } as any
      )[kind];
    part(g, [0, 0, 0], [1.3, 1.1, 5], color);
    part(g, [0, 0.15, 0.1], [7, 0.25, 1.8], color);
    part(g, [0, 0.6, -1.9], [2.8, 0.2, 0.8], '#ffe4a2');
    part(g, [0, 0.9, -1.7], [0.2, 1.5, 0.9], color);
    part(g, [0, 0.5, 0.9], [0.9, 0.45, 1.2], '#245b75', 'sphere');
    if (kind === 'ARMORED_BOSS') g.scale.setScalar(1.4);
    return g;
  }
  function enemy(kind: string) {
    const g = new THREE.Group();
    part(g, [0, 1, 0], [0.7, 1.1, 0.5], '#e89ab4');
    part(g, [0, 1.85, 0], [0.65, 0.65, 0.65], '#ffe7b4', 'sphere');
    for (const x of [-0.22, 0.22])
      part(g, [x, 0.35, 0], [0.26, 0.7, 0.3], '#725893');
    part(g, [0.5, 1.1, 0.3], [0.15, 0.2, 0.7], '#52698d');
    const chute = new THREE.Group();
    chute.name = 'chute';
    part(chute, [0, 4, 0], [3, 1.1, 3], '#ffe29d', 'sphere');
    for (const x of [-1, 1])
      part(chute, [x, 2.9, 0], [0.04, 2, 0.04], '#faf9ef');
    g.add(chute);
    if (kind === 'GROUND_BOSS') g.scale.setScalar(1.5);
    return g;
  }
  function projectile() {
    const g = new THREE.Group();
    armory.part(g, [0, 0, 0], [0.2, 0.2, 0.9], '#fff0c1', 'cylinder');
    armory.part(g, [0, 0, 0.61], [0.2, 0.2, 0.32], '#e99b85', 'cone');
    armory.part(g, [0, 0, -0.38], [0.55, 0.055, 0.27], '#91ccd9');
    armory.part(g, [0, 0, -0.38], [0.055, 0.55, 0.27], '#91ccd9');
    armory.part(g, [0, 0, -0.57], [0.15, 0.15, 0.18], '#ffd289', 'sphere');
    return g;
  }
  function updateGun() {
    const wid = state.battle?.active_weapon_id,
      w = state.profile?.owned_weapons[wid];
    const id = wid + JSON.stringify(w);
    if (id === gunId) return;
    gunId = id;
    gun.clear();
    if (!wid) return;
    gun.add(armory.weapon(wid, catalog, w));
    gun.scale.setScalar(0.26);
    gun.position.set(0.34, -0.3, -0.65);
  }
  const audio = new Map<string, HTMLAudioElement>();
  function sound(key: string) {
    if (muted) return;
    try {
      let a = audio.get(key);
      if (!a) {
        a = new Audio('/audio/' + key + '.wav');
        a.volume = 0.3;
        audio.set(key, a);
      }
      a.currentTime = 0;
      a.play().catch(() => {});
    } catch {}
  }
  function applyEvents() {
    for (const e of state.battle?.events || []) {
      if (e.kind === 'weapon_fire') {
        recoil = 0.07;
        sound(e.audio_key || 'pistol');
      } else if (
        [
          'success',
          'failure',
          'hit',
          'destroyed',
          'explosion',
          'reload_started',
          'reload_finished',
          'lock_complete',
          'player_hurt',
          'turret_fire',
        ].includes(e.kind)
      )
        sound(e.kind);
      for (const endpoint of tracerEndpoints(e, catalog, state.battle)) {
        const geo = new THREE.BufferGeometry().setFromPoints([
          worldVector(e.position),
          worldVector(endpoint),
        ]);
        const line = new THREE.Line(
          geo,
          new THREE.LineBasicMaterial({
            color: '#fff4ad',
            transparent: true,
            opacity: 0.8,
          }),
        );
        scene.add(line);
        effects.push({ node: line, ttl: 0.07 });
      }
    }
  }
  function publish() {
    state = {
      ...state,
      controls: { mode, pauseReason, requesting, sensitivity, muted },
      party: {
        ...partyClient.state(),
        open: partyClient.open && !partyPreparing,
      },
    };
    onState(state);
    return state;
  }
  function savePreferences() {
    try {
      localStorage.setItem(
        'candy-defense-web:controls',
        JSON.stringify({ mode, sensitivity, muted }),
      );
    } catch {
      state.message = '偏好設定無法保存；本次遊玩仍可使用。';
    }
  }
  function releaseControl() {
    requestNumber++;
    requesting = false;
    input.clear();
    if (document.pointerLockElement === renderer.domElement)
      document.exitPointerLock();
  }
  function send(action: string, payload: any = {}, expected?: any) {
    if (action === 'resume') {
      void begin();
      return state;
    }
    if (partyRun && action === 'menu') {
      void partyAction('leave');
      return state;
    }
    if (action === 'start' && partyClient.room?.status === 'waiting')
      action = 'party_confirm';
    const before = state.screen;
    state = JSON.parse(invoke(JSON.stringify({ action, payload, expected })));
    if (before !== state.screen && state.screen === 'battle') {
      state = JSON.parse(invoke(JSON.stringify({ action: 'pause' })));
      pauseReason = 'ready';
      last = performance.now();
    }
    if (state.screen !== 'battle' || state.battle?.phase !== 'active')
      releaseControl();
    if (action === 'pause') pauseReason = 'paused';
    if (action === 'party_confirm' && state.screen === 'profile_menu') {
      partyPreparing = false;
      void partyClient.action('ready', { ready: true, profile: state.profile });
    }
    if (partyPreparing && state.screen === 'profile_menu')
      partyPreparing = false;
    publish();
    return state;
  }
  const active = () =>
    state.screen === 'battle' && state.battle?.phase === 'active';
  function pause(reason = 'paused') {
    if (!active() && !requesting) return;
    if (partyRun) {
      partyLocalPaused = true;
      if (state.battle) state.battle = { ...state.battle, phase: 'paused' };
      partyClient.setInput({ suspended: true });
    } else state = JSON.parse(invoke(JSON.stringify({ action: 'pause' })));
    pauseReason = reason;
    releaseControl();
    publish();
  }
  function resumeSimulation() {
    if (state.screen !== 'battle' || state.battle?.phase !== 'paused') return;
    if (partyRun) {
      partyLocalPaused = false;
      if (state.battle) state.battle = { ...state.battle, phase: 'active' };
    } else state = JSON.parse(invoke(JSON.stringify({ action: 'resume' })));
    last = performance.now();
    input.start();
    pauseReason = '';
    publish();
  }
  async function begin() {
    if (
      state.screen !== 'battle' ||
      state.battle?.phase !== 'paused' ||
      requesting
    )
      return;
    if (mode !== 'mouse') {
      resumeSimulation();
      return;
    }
    const attempt = ++requestNumber;
    requesting = true;
    publish();
    try {
      await renderer.domElement.requestPointerLock();
      if (attempt !== requestNumber) {
        if (document.pointerLockElement === renderer.domElement)
          document.exitPointerLock();
        return;
      }
      if (document.pointerLockElement === renderer.domElement) {
        requesting = false;
        resumeSimulation();
      }
    } catch {
      if (attempt !== requestNumber) return;
      requesting = false;
      pauseReason = 'capture_failed';
      publish();
    }
  }
  function receivePartyRoom(room: any) {
    if (partyLeaving || state.screen === 'save_error') return;
    if (room.connectionLost) {
      pause('connection_lost');
      return;
    }
    if (room.status === 'playing' && room.runId) {
      const isHost = room.hostId === partyClient.me?.id;
      if (partyRun !== room.runId) {
        if (isHost && room.sequence > 0) {
          void partyAction('leave');
          return;
        }
        partyRun = room.runId;
        partyEventSequence = 0;
        partyInputs.clear();
        partyLocalPaused = true;
        partyPreparing = false;
        pauseReason = 'ready';
        if (isHost)
          partyPacket = JSON.parse(
            pyPartyStart(
              JSON.stringify({
                runId: room.runId,
                level: room.level,
                roster: room.roster,
              }),
            ),
          );
      }
      const view = isHost
        ? partyPacket?.views?.[partyClient.me.id]
        : room.snapshot?.view;
      if (view) applyPartyView(isHost ? view : partyClient.predictView(view));
    } else if (
      ['finished', 'closed', 'waiting'].includes(room.status) &&
      partyRun
    ) {
      releaseControl();
      partyLocalPaused = true;
      partyRun = '';
      partyPacket = null;
      state = JSON.parse(invoke(JSON.stringify({ action: 'menu' })));
    }
    for (const receipt of room.receipts || []) {
      if (rewarded.has(receipt.run_id)) continue;
      if (state.profile?.profile_id !== receipt.profile_id) continue;
      state = JSON.parse(pyPartyReward(JSON.stringify(receipt)));
      if (state.screen !== 'save_error' && !state.message) {
        rewarded.add(receipt.run_id);
        void partyClient.acknowledge(receipt.run_id);
      }
    }
  }
  function applyPartyView(view: any) {
    const events = (view.events || []).filter(
      (event: any) => event.sequence > partyEventSequence,
    );
    if (events.length)
      partyEventSequence = Math.max(...events.map((e: any) => e.sequence));
    state = {
      ...state,
      screen: 'battle',
      battle: {
        ...view,
        events,
        phase: partyLocalPaused ? 'paused' : view.phase,
        host_paused:
          view.phase === 'paused' ||
          (partyClient.room?.hostId === partyClient.me?.id && partyLocalPaused),
      },
    };
    applyEvents();
  }
  async function partyAction(action: string, payload: any = {}) {
    if (action === 'configure') {
      await partyClient.action('ready', { ready: false });
      if (!partyClient.error) {
        partyPreparing = true;
        send('prepare');
      }
      return;
    }
    if (action === 'leave') {
      partyLeaving = true;
      releaseControl();
      partyRun = '';
      partyPacket = null;
      partyPreparing = false;
      await partyClient.action('leave');
      partyLeaving = false;
      if (!partyClient.room)
        state = JSON.parse(invoke(JSON.stringify({ action: 'menu' })));
      publish();
      return;
    }
    await partyClient.action(action, payload);
  }
  function partyFrame(dt: number) {
    const room = partyClient.room;
    if (!room || !partyRun) return;
    const mine = partyClient.me.id;
    const frame = partyLocalPaused
      ? { suspended: true }
      : { ...input.frame(dt, sensitivity), aspect: camera.aspect };
    if (room.hostId === mine) {
      const frames: any = { [mine]: frame };
      for (const participant of room.roster) {
        if (participant.id === mine) continue;
        const member = room.members.find((m: any) => m.id === participant.id);
        if (!member) {
          frames[participant.id] = { suspended: true, departed: true };
          continue;
        }
        if (!member.online) {
          frames[member.id] = { suspended: true };
          continue;
        }
        const fresh = partyInputs.get(member.id) !== member.inputSeq;
        partyInputs.set(member.id, member.inputSeq);
        frames[member.id] = {
          ...(fresh
            ? member.input
            : { ...member.input, commands: [], look_delta: [0, 0] }),
          ackInput: member.inputSeq,
        };
      }
      if (!partyLocalPaused)
        partyPacket = JSON.parse(pyPartyTick(JSON.stringify({ dt, frames })));
      if (partyPacket) {
        const packet = partyLocalPaused
          ? {
              ...partyPacket,
              phase: 'paused',
              views: Object.fromEntries(
                Object.entries(partyPacket.views).map(([k, v]: any) => [
                  k,
                  { ...v, phase: 'paused' },
                ]),
              ),
            }
          : partyPacket;
        partyClient.setSnapshot(packet);
        applyPartyView(packet.views[mine]);
      }
    } else {
      partyClient.setInput(frame);
      if (!partyLocalPaused && state.battle && 'look_delta' in frame) {
        state.battle = {
          ...state.battle,
          yaw: state.battle.yaw + frame.look_delta[0],
          pitch: Math.max(
            -85,
            Math.min(85, state.battle.pitch + frame.look_delta[1]),
          ),
        };
      }
    }
  }
  function command(kind: string, value?: number) {
    if (active()) input.enqueue(kind, value ?? null);
  }
  function setMode(value: ControlMode) {
    if (!validMode(value)) return;
    pause('paused');
    mode = value;
    savePreferences();
    publish();
  }
  function setSensitivity(value: number) {
    if (!Number.isFinite(value)) return;
    sensitivity = Math.max(0.2, Math.min(3, value));
    savePreferences();
    publish();
  }
  const listeners: (() => void)[] = [];
  function listen(target: any, event: string, fn: any, opts?: any) {
    target.addEventListener(event, fn, opts);
    listeners.push(() => target.removeEventListener(event, fn, opts));
  }
  listen(window, 'keydown', (e: KeyboardEvent) => {
    if (!active() || isEditable(e.target)) return;
    if (e.code === 'Escape') {
      e.preventDefault();
      pause();
      return;
    }
    if (
      [
        'Space',
        'ArrowUp',
        'ArrowDown',
        'ArrowLeft',
        'ArrowRight',
        'KeyF',
        'KeyQ',
      ].includes(e.code)
    )
      e.preventDefault();
    input.keyDown(e.code, e.repeat);
  });
  listen(window, 'keyup', (e: KeyboardEvent) => input.keyUp(e.code));
  listen(renderer.domElement, 'contextmenu', (e: Event) => e.preventDefault());
  listen(renderer.domElement, 'mousedown', (e: MouseEvent) => {
    if (!active() || mode === 'touch') return;
    if (mode === 'mouse' && document.pointerLockElement !== renderer.domElement)
      return;
    if (e.button === 0) input.fireDown('mouse');
    if (e.button === 2) command('toggle_aim');
  });
  listen(window, 'mouseup', (e: MouseEvent) => {
    if (e.button === 0) input.fireUp('mouse');
  });
  // 相同滑鼠 pointerId 的右鍵放開，不可解除仍按住的左鍵。
  listen(window, 'pointerup', (e: PointerEvent) => {
    if (e.pointerType === 'touch' || e.button === 0)
      input.releasePointer(e.pointerId);
  });
  listen(window, 'pointercancel', (e: PointerEvent) =>
    input.releasePointer(e.pointerId),
  );
  listen(window, 'mousemove', (e: MouseEvent) => {
    if (
      active() &&
      mode === 'mouse' &&
      document.pointerLockElement === renderer.domElement
    ) {
      input.look[0] += e.movementX * 0.12 * sensitivity;
      input.look[1] += e.movementY * 0.12 * sensitivity;
    }
  });
  listen(document, 'pointerlockchange', () => {
    if (document.pointerLockElement === renderer.domElement) {
      if (requesting) {
        requesting = false;
        resumeSimulation();
      }
    } else if (active() && mode === 'mouse') pause('released');
  });
  listen(document, 'pointerlockerror', () => {
    if (requesting) {
      requestNumber++;
      requesting = false;
      pauseReason = 'capture_failed';
      publish();
    }
  });
  listen(window, 'blur', () => pause('focus'));
  listen(document, 'visibilitychange', () => {
    if (document.hidden) pause('focus');
  });
  function resize() {
    renderer.setSize(host.clientWidth, host.clientHeight);
    camera.aspect = host.clientWidth / host.clientHeight;
    camera.updateProjectionMatrix();
  }
  listen(window, 'resize', resize);
  function draw(dt: number) {
    const b = state.battle,
      seen = new Set<string>();
    if (b && state.screen === 'battle') {
      camera.position.set(
        b.player.position[0],
        b.player.position[1] + 1.6,
        -b.player.position[2],
      );
      camera.rotation.order = 'YXZ';
      camera.rotation.set(
        (-b.pitch * Math.PI) / 180,
        (-b.yaw * Math.PI) / 180,
        0,
      );
      camera.fov =
        (2 *
          Math.atan(Math.tan((b.fov * Math.PI) / 360) / camera.aspect) *
          180) /
        Math.PI;
      camera.updateProjectionMatrix();
      gun.visible = true;
      updateGun();
      recoil = Math.max(0, recoil - dt * 0.4);
      gun.position.z = -0.65 + recoil;
      for (const kind of [
        'aircraft',
        'enemies',
        'turrets',
        'missiles',
        'rockets',
      ])
        for (const e of b[kind]) {
          if (e.hp === 0 || e.status === 'destroyed') continue;
          seen.add(e.id);
          let node = nodes.get(e.id);
          if (!node) {
            node =
              kind === 'aircraft'
                ? aircraft(e.kind)
                : kind === 'enemies'
                  ? enemy(e.kind)
                  : kind === 'turrets'
                    ? armory.turret(e.turret_type_id)
                    : projectile();
            if (kind === 'missiles' || kind === 'rockets') {
              const trail = new ProjectileTrail();
              trails.set(e.id, trail);
              scene.add(trail.line);
            }
            scene.add(node);
            nodes.set(e.id, node);
          }
          const targetPosition = new THREE.Vector3(
            e.position[0],
            e.position[1],
            -e.position[2],
          );
          if (
            b.cooperative &&
            partyClient.room?.hostId !== partyClient.me?.id &&
            node.position.distanceTo(targetPosition) < 30
          )
            node.position.lerp(targetPosition, Math.min(1, dt * 18));
          else node.position.copy(targetPosition);
          if (kind === 'missiles' || kind === 'rockets') {
            orientProjectile(node, e.forward);
            trails.get(e.id)?.update(e.position, e.age);
          }
          if (kind === 'turrets' && e.target_position) {
            const head = node.getObjectByName('turret-head');
            if (head)
              orientProjectile(
                head,
                e.target_position.map(
                  (v: number, i: number) => v - e.origin[i],
                ),
              );
          }
          if (kind === 'aircraft') {
            node.rotation.order = 'YXZ';
            node.rotation.y = (-e.yaw * Math.PI) / 180;
            node.rotation.x = (-e.pitch * Math.PI) / 180;
          }
          if (kind === 'enemies') {
            const chute = node.getObjectByName('chute');
            if (chute) chute.visible = e.phase !== 'ground';
          }
        }
      for (const teammate of b.players || []) {
        if (teammate.id === b.self_id || teammate.hp <= 0) continue;
        const key = 'ally-' + teammate.id;
        seen.add(key);
        let node = nodes.get(key);
        if (!node) {
          node = new THREE.Group();
          part(node, [0, 0.8, 0], [0.65, 1.1, 0.42], '#52d9cd');
          part(node, [0, 1.65, 0], [0.48, 0.48, 0.48], '#ffe0b0', 'sphere');
          part(node, [-0.18, 0.22, 0], [0.22, 0.45, 0.25], '#1a4c65');
          part(node, [0.18, 0.22, 0], [0.22, 0.45, 0.25], '#1a4c65');
          scene.add(node);
          nodes.set(key, node);
        }
        node.position.lerp(
          new THREE.Vector3(
            teammate.position[0],
            teammate.position[1],
            -teammate.position[2],
          ),
          Math.min(1, dt * 15),
        );
        node.rotation.y = (-teammate.yaw * Math.PI) / 180;
      }
    } else {
      gun.visible = false;
      camera.fov = 55;
      camera.position.set(46, 28, 78);
      camera.lookAt(-5, 8, 20);
      camera.updateProjectionMatrix();
    }
    for (const [id, node] of nodes)
      if (!seen.has(id)) {
        scene.remove(node);
        nodes.delete(id);
        const trail = trails.get(id);
        if (trail) {
          scene.remove(trail.line);
          trail.dispose();
          trails.delete(id);
        }
      }
    for (let i = effects.length - 1; i >= 0; i--) {
      const fx = effects[i];
      fx.ttl -= active() ? dt : 0;
      if (state.screen !== 'battle') fx.ttl = 0;
      if (fx.ttl <= 0) {
        scene.remove(fx.node);
        (fx.node as any).geometry?.dispose();
        (fx.node as any).material?.dispose();
        effects.splice(i, 1);
      }
    }
    renderer.render(scene, camera);
    aimingHud.update(
      state.screen === 'battle' ? b : null,
      camera,
      host.clientWidth,
      host.clientHeight,
    );
  }
  function frame(now: number) {
    if (disposed) return;
    const dt = Math.min((now - last) / 1000, 0.06);
    last = now;
    if (partyRun) {
      try {
        partyFrame(dt);
        if (now - notifyAt > 100) {
          publish();
          notifyAt = now;
        }
      } catch (e: any) {
        pause();
        partyClient.error = '多人戰場已暫停：' + e.message;
        publish();
      }
    } else if (active()) {
      const payload = {
        dt,
        ...input.frame(dt, sensitivity),
        aspect: camera.aspect,
      };
      try {
        state = JSON.parse(invoke(JSON.stringify({ action: 'tick', payload })));
        applyEvents();
        if (!active()) releaseControl();
        if (now - notifyAt > 100 || state.screen !== 'battle') {
          publish();
          notifyAt = now;
        }
      } catch (e: any) {
        pause();
        state.message = '遊戲已暫停：' + e.message;
        publish();
      }
    }
    draw(dt);
    raf = requestAnimationFrame(frame);
  }
  raf = requestAnimationFrame(frame);
  const unregister = registerGameTools(() => state, send);
  publish();
  return {
    catalog,
    partyAction,
    send,
    command,
    begin,
    pause,
    setMode,
    setSensitivity,
    getState: () => state,
    touchStart: (id: number, role: 'move' | 'look', x: number, y: number) => {
      if (mode === 'touch' && active()) input.touchDown(id, role, x, y);
    },
    touchMove: (id: number, x: number, y: number) =>
      input.touchMove(id, x, y, sensitivity),
    releasePointer: (id: number) => input.releasePointer(id),
    fireDown: (id: number) => {
      if (active()) input.fireDown('pointer:' + id);
    },
    setMuted: (v: boolean) => {
      muted = v;
      if (muted) for (const a of audio.values()) a.pause();
      savePreferences();
      publish();
    },
    dispose() {
      partyClient.dispose();
      pyPartyStart.destroy();
      pyPartyTick.destroy();
      pyPartyReward.destroy();
      releaseControl();
      unregister();
      disposed = true;
      cancelAnimationFrame(raf);
      for (const off of listeners) off();
      for (const a of audio.values()) a.pause();
      for (const g of Object.values(geometries) as any[]) g.dispose();
      for (const m of materials.values()) m.dispose();
      armory.dispose();
      for (const trail of trails.values()) trail.dispose();
      for (const fx of effects) {
        (fx.node as any).geometry?.dispose();
        (fx.node as any).material?.dispose();
      }
      renderer.dispose();
      aimingHud.dispose();
      renderer.domElement.remove();
      invoke.destroy();
      read.destroy();
    },
  };
}
