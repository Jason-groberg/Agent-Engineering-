import type { Exhibit } from '../types';
export function nearestExhibit(x: number, y: number, items: Exhibit[], radius = 28): Exhibit | null {
  let closest: Exhibit | null = null, distance = radius;
  for (const item of items) {
    const d = Math.hypot(x - (item.tile.x * 16 + 8), y - (item.tile.y * 16 + 8));
    if (d < distance) { closest = item; distance = d; }
  }
  return closest;
}
export function movementVector(left: boolean, right: boolean, up: boolean, down: boolean, speed = 72): [number, number] {
  const x = Number(right) - Number(left), y = Number(down) - Number(up);
  const length = Math.hypot(x, y) || 1;
  return [x / length * speed, y / length * speed];
}
