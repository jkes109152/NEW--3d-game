import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

type Vec = [number, number, number];
export type Appearance = {
  selected_color?: string;
  selected_pattern?: string;
  selected_attachments?: Record<string, string | null>;
};
export type ModelKind = 'weapons' | 'armors' | 'turrets' | 'player';
export const WEAPON_COLORS: Record<string, string> = {
  W01: '#8dcbe6',
  W02: '#be9ee5',
  W03: '#f0bc87',
  W04: '#a0d8ae',
  W05: '#ece0b0',
  W06: '#80cebb',
  W07: '#cd9ac6',
  W08: '#d8c8ad',
  W09: '#c99269',
  W10: '#f1adbd',
  W11: '#82cce2',
  W12: '#ebc6e1',
  W13: '#e5ca7f',
  W14: '#ad8d7e',
  W15: '#d2af88',
  W16: '#efe099',
  W17: '#a8cee6',
  W18: '#b4b0ed',
  W19: '#e7a17d',
  W20: '#9bd7be',
};

// The shop and first-person view use this same model factory and source recipes.
// Geometry is aligned before scaling: every recipe's depth is on local Z.
export class ArmoryModels {
  geometries: Record<string, THREE.BufferGeometry>;
  materials = new Map<string, THREE.MeshStandardMaterial>();
  textures = new Map<string, THREE.Texture>();
  constructor() {
    const wedge = new THREE.BufferGeometry();
    wedge.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(
        [
          -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, -0.5, -0.5, 0.5, 0.5, -0.5, -0.5,
          0.5, -0.5, 0.5, 0.5, 0.5, -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, -0.5,
          0.5, 0.5, -0.5, -0.5, -0.5, -0.5, 0.5, 0.5, -0.5, -0.5, 0.5, -0.5,
          -0.5, -0.5, -0.5, -0.5, -0.5, 0.5, 0.5, -0.5, 0.5, -0.5, -0.5, -0.5,
          0.5, -0.5, 0.5, 0.5, -0.5, -0.5, -0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.5,
          -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, -0.5, 0.5,
        ],
        3,
      ),
    );
    wedge.computeVertexNormals();
    this.geometries = {
      round: new RoundedBoxGeometry(1, 1, 1, 2, 0.1),
      sphere: new THREE.SphereGeometry(0.5, 16, 12),
      cylinder: new THREE.CylinderGeometry(0.5, 0.5, 1, 16).rotateX(
        -Math.PI / 2,
      ),
      cone: new THREE.ConeGeometry(0.5, 1, 16).rotateX(-Math.PI / 2),
      ring: new THREE.TorusGeometry(0.36, 0.14, 8, 20),
      wedge,
    };
  }
  async loadPatterns() {
    const loader = new THREE.TextureLoader();
    await Promise.all(
      ['dots', 'stripes', 'stars'].map(async (id) => {
        const t = await loader.loadAsync('/textures/' + id + '.png');
        t.colorSpace = THREE.SRGBColorSpace;
        t.wrapS = t.wrapT = THREE.RepeatWrapping;
        t.repeat.set(2, 2);
        this.textures.set(id, t);
      }),
    );
  }
  part(
    parent: THREE.Object3D,
    pos: Vec,
    scale: Vec,
    color: string,
    shape = 'round',
    pattern = 'plain',
  ) {
    const key = color + ':' + pattern;
    if (!this.materials.has(key))
      this.materials.set(
        key,
        new THREE.MeshStandardMaterial({
          color,
          roughness: 0.52,
          metalness: 0.12,
          map: this.textures.get(pattern) || null,
        }),
      );
    const mesh = new THREE.Mesh(
      this.geometries[shape] || this.geometries.round,
      this.materials.get(key),
    );
    mesh.position.set(pos[0], pos[1], -pos[2]);
    mesh.scale.set(...scale);
    parent.add(mesh);
    return mesh;
  }
  weapon(id: string, catalog: any, appearance: Appearance = {}) {
    const g = new THREE.Group();
    g.name = id;
    const color =
      appearance.selected_color && appearance.selected_color !== 'original'
        ? catalog.palette[appearance.selected_color]
        : WEAPON_COLORS[id];
    const pattern = appearance.selected_pattern || 'plain';
    const body = (p: Vec, s: Vec, shape = 'round') =>
      this.part(g, p, s, color, shape, pattern);
    const dark = (p: Vec, s: Vec, shape = 'round') =>
      this.part(g, p, s, '#33485f', shape);
    body([0, 0, 0], [0.4, 0.35, 0.8]);
    dark([0, -0.32, -0.13], [0.22, 0.6, 0.25]);
    for (const [name, pos, scale, shape] of catalog.recipes[id]) {
      const shapeOverride =
        ['W01', 'W14', 'W19', 'W20'].includes(id) && name.includes('管')
          ? 'cylinder'
          : shape;
      const mesh = body(pos, scale, shapeOverride);
      mesh.name = name;
    }
    const def = catalog.weapons[id];
    if (!['pistol', 'anti_air', 'rocket'].includes(def.category)) {
      dark([0, 0.09, 0.95], [0.13, 0.13, 1.45], 'cylinder');
      if (!['W06', 'W10', 'W12', 'W13', 'W14'].includes(id))
        body([0, 0, -0.7], [0.29, 0.4, 0.72]);
    }
    if (id === 'W01') dark([0, 0.12, 1.59], [0.38, 0.38, 0.035], 'cylinder');
    if (id === 'W02')
      for (const x of [-0.3, 0, 0.3])
        for (const y of [-0.08, 0.22])
          dark([x, y, 1.31], [0.22, 0.22, 0.035], 'cylinder');
    if (id === 'W18') dark([-0.2, -0.36, 0.9], [0.1, 0.9, 0.15]);
    if (id === 'W19') dark([0, 0.12, -0.68], [0.5, 0.5, 0.08], 'ring');
    if (id === 'W20') dark([0, 0.1, 1.67], [0.27, 0.27, 0.035], 'cylinder');
    if (['pistol', 'smg', 'rifle'].includes(def.category))
      this.part(g, [0, 0.29, -0.25], [0.12, 0.075, 0.12], '#fff0b7');
    const attachments = Object.values(appearance.selected_attachments || {});
    if (attachments.includes('zoom_scope')) {
      dark([0, 0.47, 0.1], [0.2, 0.16, 0.42]);
      dark([0, 0.66, 0.1], [0.29, 0.29, 0.86], 'cylinder');
      this.part(g, [0, 0.66, 0.54], [0.21, 0.21, 0.025], '#89e7dc', 'cylinder');
    }
    if (attachments.includes('guidance_scope')) {
      dark([0.36, 0.6, 0], [0.14, 0.48, 0.2]);
      this.part(g, [0.36, 0.85, 0.02], [0.5, 0.35, 0.12], '#acf1dc', 'sphere');
    }
    if (attachments.includes('heavy_barrel')) {
      const front = Math.max(
        ...catalog.recipes[id].map((r: any) => r[1][2] + r[2][2] / 2),
      );
      dark([0, 0.12, front - 0.16], [0.57, 0.57, 0.52], 'cylinder');
      this.part(
        g,
        [0, 0.12, front + 0.11],
        [0.4, 0.4, 0.028],
        '#203449',
        'cylinder',
      );
    }
    if (attachments.includes('extended_magazine'))
      body([0.04, -0.75, 0.04], [0.3, 0.6, 0.38]);
    if (attachments.includes('quick_reload'))
      this.part(g, [0, -0.55, 0.02], [0.3, 0.16, 0.32], '#b1f1db');
    if (attachments.includes('cooling_guidance'))
      for (const x of [-0.47, 0.47])
        this.part(g, [x, 0.18, 0.36], [0.12, 0.55, 0.82], '#b1f1db');
    if (attachments.includes('light_loading_rack'))
      dark([0, -0.3, 0.75], [0.66, 0.12, 0.75]);
    return g;
  }
  defender(id: string, catalog: any) {
    const g = new THREE.Group();
    g.name = id;
    this.part(g, [0, 0.95, 0], [0.55, 0.8, 0.4], '#92aec5');
    this.part(g, [0, 1.6, 0], [0.48, 0.48, 0.48], '#f4d9ad', 'sphere');
    for (const x of [-0.18, 0.18])
      this.part(g, [x, 0.29, 0], [0.22, 0.58, 0.26], '#52677f');
    for (const x of [-0.4, 0.4])
      this.part(g, [x, 0.96, 0], [0.19, 0.62, 0.26], '#92aec5');
    const colors: Record<string, string> = {
      A01: '#f0e3fa',
      A02: '#b6c8fa',
      A03: '#c0e9ae',
      A04: '#8be1cf',
      A05: '#efd198',
      A06: '#89c9ee',
    };
    if (catalog.armor_parts[id]) {
      const [name, pos, scale] = catalog.armor_parts[id];
      const mesh = this.part(
        g,
        pos,
        scale,
        colors[id],
        id === 'A06' ? 'ring' : 'round',
      );
      mesh.name = name;
      if (['A02', 'A04', 'A06'].includes(id))
        this.part(
          g,
          [-pos[0], pos[1], pos[2]],
          scale,
          colors[id],
          id === 'A06' ? 'ring' : 'round',
        );
    }
    return g;
  }
  turret(id: string) {
    const g = new THREE.Group();
    g.name = id;
    this.part(g, [0, 0.3, 0], [2, 0.6, 2], '#455f79');
    this.part(g, [0, 0.78, 0], [0.65, 0.65, 0.65], '#a6b8d5');
    const top = new THREE.Group();
    top.name = 'turret-head';
    g.add(top);
    if (id === 'T01') {
      this.part(top, [0, 1.18, 0], [1, 0.55, 0.85], '#99dac2');
      for (const x of [-0.23, 0.23])
        this.part(
          top,
          [x, 1.18, 0.85],
          [0.16, 0.16, 1.65],
          '#405975',
          'cylinder',
        );
      this.part(top, [0.67, 1.07, -0.1], [0.38, 0.55, 0.6], '#efd39b');
    } else if (id === 'T02') {
      this.part(top, [0, 1.35, 0.4], [0.23, 0.23, 2.8], '#bdace4', 'cylinder');
      this.part(top, [0, 1.7, -0.1], [0.3, 0.3, 0.8], '#8196ba', 'cylinder');
      this.part(top, [0, 1.35, 1.83], [0.4, 0.36, 0.32], '#405975');
    } else {
      for (const x of [-0.55, 0.55]) {
        this.part(top, [x, 1.36, 0.35], [0.74, 0.7, 1.5], '#96cde9');
        for (const y of [1.2, 1.52])
          this.part(
            top,
            [x, y, 1.12],
            [0.26, 0.26, 0.05],
            '#314e68',
            'cylinder',
          );
      }
      this.part(top, [0, 2, 0], [0.16, 0.7, 0.16], '#728fb0');
      this.part(top, [0, 2.27, 0], [1.1, 0.43, 0.25], '#f3dca2', 'sphere');
    }
    top.position.y = 1.2;
    for (const mesh of top.children) mesh.position.y -= 1.2;
    return g;
  }
  model(kind: ModelKind, id: string, catalog: any, appearance?: Appearance) {
    return kind === 'weapons'
      ? this.weapon(id, catalog, appearance)
      : kind === 'turrets'
        ? this.turret(id)
        : this.defender(id, catalog);
  }
  dispose() {
    Object.values(this.geometries).forEach((g) => g.dispose());
    this.materials.forEach((m) => m.dispose());
    this.textures.forEach((t) => t.dispose());
  }
}

// One renderer for the entire shop. Cards receive snapshots, not WebGL contexts.
export function createArmoryPreview(catalog: any) {
  const bank = new ArmoryModels();
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(600, 320);
  renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight('#fff8eb', '#4d6683', 2.7));
  const sun = new THREE.DirectionalLight('#ffffff', 3.2);
  sun.position.set(2, 5, 4);
  scene.add(sun);
  const camera = new THREE.OrthographicCamera(-1.875, 1.875, 1, -1, 0.01, 100);
  const cache = new Map<string, string>();
  const ready = bank.loadPatterns();
  let disposed = false;
  return {
    async render(kind: ModelKind, id: string, appearance?: Appearance) {
      await ready;
      if (disposed) return '';
      const key = JSON.stringify([kind, id, appearance]);
      if (cache.has(key)) return cache.get(key)!;
      const model = bank.model(kind, id, catalog, appearance);
      scene.add(model);
      model.updateMatrixWorld(true);
      const center = new THREE.Box3()
        .setFromObject(model)
        .getCenter(new THREE.Vector3());
      // Armor backpacks remain visible from this three-quarter side view.
      camera.position
        .copy(center)
        .add(new THREE.Vector3(5, 2.6, id === 'A01' ? 3.5 : -3.5));
      camera.lookAt(center);
      camera.updateMatrixWorld(true);
      const bounds = new THREE.Box3().setFromObject(model),
        corners: THREE.Vector3[] = [];
      for (const x of [bounds.min.x, bounds.max.x])
        for (const y of [bounds.min.y, bounds.max.y])
          for (const z of [bounds.min.z, bounds.max.z])
            corners.push(
              new THREE.Vector3(x, y, z).applyMatrix4(
                camera.matrixWorldInverse,
              ),
            );
      const maxX = Math.max(...corners.map((v) => Math.abs(v.x))),
        maxY = Math.max(...corners.map((v) => Math.abs(v.y)));
      const half = Math.max(maxY, maxX / (600 / 320)) * 1.17;
      camera.left = (-half * 600) / 320;
      camera.right = (half * 600) / 320;
      camera.top = half;
      camera.bottom = -half;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
      const url = renderer.domElement.toDataURL('image/png');
      scene.remove(model);
      if (cache.size >= 64) cache.delete(cache.keys().next().value!);
      cache.set(key, url);
      return url;
    },
    async dispose() {
      disposed = true;
      await ready.catch(() => {});
      bank.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      cache.clear();
    },
  };
}
