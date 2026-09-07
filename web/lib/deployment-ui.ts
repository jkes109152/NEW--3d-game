export const TURRET_KINDS = ['T01', 'T02', 'T03'] as const;
export function turretStock(profile: any, deployments: any[], kind: string) {
  const owned = profile.owned_turrets.filter((t: any) => t.turret_id === kind);
  const placed = new Set(deployments.map((t: any) => t.instance_id));
  return {
    total: owned.length,
    available: owned.filter((t: any) => !placed.has(t.instance_id)),
  };
}
export function mapViewport(
  view: { x: number; y: number; zoom: number },
  aspect: number,
) {
  const width = Math.max(120, 320 * aspect) / view.zoom;
  const height = width / aspect;
  return { width, height, left: view.x - width / 2, top: view.y + height / 2 };
}
export function mapPoint(
  client: [number, number],
  rect: { left: number; top: number; width: number; height: number },
  view: ReturnType<typeof mapViewport>,
) {
  return [
    view.left + ((client[0] - rect.left) / rect.width) * view.width,
    view.top - ((client[1] - rect.top) / rect.height) * view.height,
  ];
}
