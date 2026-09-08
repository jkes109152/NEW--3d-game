import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { ArmoryModels } from './armory-models';
import { AntiAirHud } from './aiming-hud';
import { pvpGroundHud } from './pvp-hud.ts';
import type { PvpActor, PvpView } from './pvp-types.ts';
const vec = (p: number[]) => new THREE.Vector3(p[0], p[1], -p[2]);
export class PvpScene {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(65, 1, 0.08, 1000);
  private nodes = new Map<string, THREE.Group>();
  private materials = new Map<string, THREE.MeshStandardMaterial>();
  private geometry = new RoundedBoxGeometry(1, 1, 1, 2, 0.1);
  private sphere = new THREE.SphereGeometry(0.5, 12, 8);
  private armory = new ArmoryModels();
  private gun: THREE.Group;
  private hud: AntiAirHud;
  private ray = new THREE.Raycaster();
  private barriers: THREE.Object3D[] = [];
  private lastTick = -1;
  private previous: PvpView | null = null;
  private current: PvpView | null = null;
  private receivedAt = 0;
  private disposed = false;
  constructor(
    private renderer: THREE.WebGLRenderer,
    private host: HTMLElement,
    catalog: any,
  ) {
    this.scene.background = new THREE.Color('#aedbed');
    this.scene.fog = new THREE.Fog('#aedbed', 180, 430);
    this.scene.add(new THREE.HemisphereLight('#fff5da', '#417d6f', 2.2));
    const sun = new THREE.DirectionalLight('#fff4d4', 2.8);
    sun.position.set(60, 90, 40);
    this.scene.add(sun);
    this.scene.add(this.camera);
    this.part(this.scene, [0, -0.55, 0], [210, 1, 210], '#9fceb7');
    const grid = new THREE.GridHelper(200, 20, '#5b9687', '#80b5a2');
    grid.position.y = 0.015;
    this.scene.add(grid);
    for (const [c, s] of [
      [
        [-45, 6, -25],
        [10, 12, 18],
      ],
      [
        [45, 6, 25],
        [10, 12, 18],
      ],
      [
        [-25, 4, 45],
        [16, 8, 10],
      ],
      [
        [25, 4, -45],
        [16, 8, 10],
      ],
    ]) {
      const box = this.part(this.scene, c, s, '#daaccd');
      this.barriers.push(box);
      this.part(
        this.scene,
        [c[0], c[1] + s[1] / 2 - 0.15, c[2]],
        [s[0], 0.3, s[2]],
        '#ffe09c',
      );
    }
    for (const x of [-100, 100])
      this.part(this.scene, [x, 0.08, 0], [0.35, 0.15, 200], '#ffd176');
    for (const z of [-100, 100])
      this.part(this.scene, [0, 0.08, z], [200, 0.15, 0.35], '#ffd176');
    this.gun = this.armory.weapon('W01', catalog);
    this.gun.rotation.y = Math.PI;
    this.gun.scale.setScalar(0.45);
    this.gun.position.set(0.47, -0.38, -0.9);
    this.camera.add(this.gun);
    this.hud = new AntiAirHud(host);
  }
  private part(
    parent: THREE.Object3D,
    p: number[],
    size: number[],
    color: string,
    sphere = false,
  ) {
    if (!this.materials.has(color))
      this.materials.set(
        color,
        new THREE.MeshStandardMaterial({ color, roughness: 0.65 }),
      );
    const mesh = new THREE.Mesh(
      sphere ? this.sphere : this.geometry,
      this.materials.get(color),
    );
    mesh.position.copy(vec(p));
    mesh.scale.set(...(size as [number, number, number]));
    parent.add(mesh);
    return mesh;
  }
  private aircraft() {
    const g = new THREE.Group();
    this.part(g, [0, 0, 0], [1.1, 1, 5], '#ea94ae');
    this.part(g, [0, 0, 0], [7, 0.22, 1.5], '#ea94ae');
    this.part(g, [0, 0.5, -1.8], [2.7, 0.22, 0.8], '#ffe2a0');
    this.part(g, [0, 0.75, -1.7], [0.18, 1.5, 0.8], '#ea94ae');
    this.part(g, [0, 0.45, 1], [0.8, 0.6, 1.4], '#31596f', true);
    return g;
  }
  private ground() {
    const g = new THREE.Group();
    this.part(g, [0, 1, 0], [0.7, 1, 0.4], '#75bddc');
    this.part(g, [0, 1.75, 0], [0.55, 0.55, 0.55], '#ffe2b6', true);
    for (const x of [-0.2, 0.2])
      this.part(g, [x, 0.3, 0], [0.25, 0.6, 0.3], '#486486');
    this.part(g, [0.45, 1.25, 0.25], [0.35, 0.35, 1.1], '#8dcbe6');
    return g;
  }
  render(
    view: PvpView,
    predicted: PvpActor | null,
    cameraMode: 'chase' | 'cockpit',
    spectator: string | null,
    dt: number,
  ) {
    if (this.disposed) return;
    const now = performance.now();
    if (view.tick !== this.lastTick) {
      this.previous = this.current;
      this.current = view;
      this.lastTick = view.tick;
      this.receivedAt = now;
    }
    const mine = view.actors.find((a) => a.id === view.selfId);
    const focus =
      view.actors.find((a) => a.id === (mine?.alive ? mine.id : spectator)) ||
      mine;
    const seen = new Set<string>();
    for (const a of view.actors) {
      if (!a.alive) continue;
      const key = 'actor:' + a.id;
      seen.add(key);
      let node = this.nodes.get(key);
      if (!node) {
        node = a.team === 'air' ? this.aircraft() : this.ground();
        this.nodes.set(key, node);
        this.scene.add(node);
      }
      const target = predicted?.id === a.id ? predicted : a;
      let pos = vec(target.position);
      const older = this.previous?.actors.find((p) => p.id === a.id);
      if (!predicted || predicted.id !== a.id) {
        if (older && this.previous && view.elapsed > this.previous.elapsed) {
          const gap = (view.elapsed - this.previous.elapsed) * 1000;
          const t = Math.min(
            1.2,
            Math.max(0, (now - this.receivedAt) / Math.max(1, gap)),
          );
          const extrap = Math.min(
            0.2,
            Math.max(0, (now - this.receivedAt - gap) / 1000),
          );
          pos =
            t <= 1
              ? vec(older.position).lerp(pos, t)
              : pos.add(
                  vec(a.position)
                    .sub(vec(older.position))
                    .multiplyScalar(extrap / Math.max(gap / 1000, 0.001)),
                );
        }
      }
      if (node.position.distanceTo(pos) > 10 || node.userData.fresh !== true)
        node.position.copy(pos);
      else node.position.lerp(pos, Math.min(1, dt / 0.1));
      node.userData.fresh = true;
      node.rotation.order = 'YXZ';
      node.rotation.set(
        (-target.pitch * Math.PI) / 180,
        (-target.yaw * Math.PI) / 180,
        (-target.roll * Math.PI) / 180,
      );
      node.visible = !(
        focus?.id === a.id &&
        (a.team === 'ground' || cameraMode === 'cockpit')
      );
    }
    for (const m of view.missiles) {
      const key = 'missile:' + m.id;
      seen.add(key);
      let node = this.nodes.get(key);
      if (!node) {
        node = new THREE.Group();
        this.part(node, [0, 0, 0], [0.16, 0.16, 1.3], '#fff1b6');
        this.part(node, [0, 0, -0.8], [0.1, 0.1, 0.6], '#ffb653');
        this.nodes.set(key, node);
        this.scene.add(node);
      }
      node.position.copy(vec(m.position));
      node.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 0, -1),
        vec(m.forward).normalize(),
      );
    }
    for (const [key, node] of this.nodes)
      if (!seen.has(key)) {
        this.scene.remove(node);
        this.nodes.delete(key);
      }
    if (focus) {
      const pose = predicted?.id === focus.id ? predicted : focus;
      const node = this.nodes.get('actor:' + focus.id);
      const center = node?.position.clone() || vec(pose.position);
      this.camera.rotation.order = 'YXZ';
      this.camera.rotation.set(
        (-pose.pitch * Math.PI) / 180,
        (-pose.yaw * Math.PI) / 180,
        (-pose.roll * Math.PI) / 180,
      );
      if (focus.team === 'ground')
        this.camera.position.copy(center.add(new THREE.Vector3(0, 1.6, 0)));
      else {
        const offset = new THREE.Vector3(
          0,
          cameraMode === 'chase' ? 4 : 0.8,
          cameraMode === 'chase' ? 12 : -1,
        ).applyQuaternion(this.camera.quaternion);
        if (cameraMode === 'chase') {
          this.ray.set(center, offset.clone().normalize());
          this.ray.far = offset.length();
          this.scene.updateMatrixWorld(true);
          const hit = this.ray.intersectObjects(this.barriers, false)[0];
          if (hit) offset.setLength(Math.max(0.1, hit.distance - 0.3));
        }
        this.camera.position.copy(center.clone().add(offset));
        if (cameraMode === 'chase') {
          const up = new THREE.Vector3(0, 1, 0).applyQuaternion(
            this.camera.quaternion,
          );
          const forward = new THREE.Vector3(0, 0, -20).applyQuaternion(
            this.camera.quaternion,
          );
          this.camera.up.copy(up);
          this.camera.lookAt(center.add(forward));
        }
      }
    }
    this.gun.visible = !!mine?.alive && mine.team === 'ground';
    this.camera.aspect = this.host.clientWidth / this.host.clientHeight;
    this.camera.fov = 65;
    this.camera.updateProjectionMatrix();
    this.renderer.render(this.scene, this.camera);
    this.hud.update(
      pvpGroundHud(view),
      this.camera,
      this.host.clientWidth,
      this.host.clientHeight,
    );
  }
  dispose() {
    this.disposed = true;
    this.hud.dispose();
    this.armory.dispose();
    this.geometry.dispose();
    this.sphere.dispose();
    for (const m of this.materials.values()) m.dispose();
    this.scene.traverse((n) => {
      if (n instanceof THREE.LineSegments) {
        n.geometry.dispose();
        const mats = Array.isArray(n.material) ? n.material : [n.material];
        mats.forEach((m) => m.dispose());
      }
    });
    this.nodes.clear();
    this.scene.clear();
  }
}
