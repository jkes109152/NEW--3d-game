import * as THREE from 'three';

const NOSE = new THREE.Vector3(0, 0, -1);
export function worldVector(v: number[]) {
  return new THREE.Vector3(v[0], v[1], -v[2]);
}
export function orientProjectile(node: THREE.Object3D, forward: number[]) {
  const direction = worldVector(forward);
  if (
    direction.lengthSq() > 1e-12 &&
    direction.toArray().every(Number.isFinite)
  )
    node.quaternion.setFromUnitVectors(NOSE, direction.normalize());
}
export function tracerEndpoints(
  event: any,
  catalog: any,
  battle: any,
): number[][] {
  if (!event.position) return [];
  if (event.kind === 'weapon_fire') {
    if (catalog.weapons[event.weapon_id]?.delivery !== 'hitscan') return [];
    return event.endpoints || (event.target ? [event.target] : []);
  }
  if (event.kind === 'turret_fire') {
    const type = battle.turrets.find(
      (t: any) => t.id === event.source_id,
    )?.turret_type_id;
    if (catalog.turrets[type]?.target_kind !== 'enemy') return [];
    return event.target ? [event.target] : [];
  }
  return [];
}

// A short history of actual world positions. It is never parented to the
// projectile or camera, and its clock is simulation age so pause freezes it.
export class ProjectileTrail {
  samples: { point: THREE.Vector3; age: number }[] = [];
  geometry = new THREE.BufferGeometry();
  material = new THREE.LineBasicMaterial({
    color: '#ffe7b2',
    transparent: true,
    opacity: 0.7,
  });
  line: THREE.Line;
  positions = new Float32Array(24 * 3);
  constructor() {
    this.geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(this.positions, 3).setUsage(
        THREE.DynamicDrawUsage,
      ),
    );
    this.geometry.setDrawRange(0, 0);
    this.line = new THREE.Line(this.geometry, this.material);
    this.line.frustumCulled = false;
  }
  update(position: number[], age: number) {
    const point = worldVector(position),
      last = this.samples.at(-1);
    if (last && age < last.age) this.samples = [];
    if (!last || point.distanceToSquared(last.point) > 1e-12)
      this.samples.push({ point, age });
    this.samples = this.samples.filter((s) => age - s.age <= 0.18).slice(-24);
    this.samples.forEach((s, i) => s.point.toArray(this.positions, i * 3));
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.setDrawRange(0, this.samples.length);
  }
  dispose() {
    this.geometry.dispose();
    this.material.dispose();
  }
}
