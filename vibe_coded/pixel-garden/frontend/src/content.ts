import rawExhibits from '../../content/exhibits.json';
import garden from '../../content/garden.json';
import remarks from '../../content/remarks.json';
import type { Exhibit } from './types';

export const exhibits = rawExhibits as Exhibit[];
export { garden, remarks };

export function validateContent(items: Exhibit[], world = garden): void {
  const { tileSize: size, width, height } = world;
  const cols = width / size, rows = height / size;
  const key = (x: number, y: number) => `${x},${y}`;
  const blocked = new Set<string>();
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
    if (world.obstacles.some(o => x * size < o.x + o.width && (x + 1) * size > o.x && y * size < o.y + o.height && (y + 1) * size > o.y)) blocked.add(key(x, y));
  }
  const ids = new Set<string>();
  for (const item of items) {
    const { x, y } = item.tile;
    if (ids.has(item.id) || !/^[a-z][a-z0-9-]*$/.test(item.id)) throw new Error(`Invalid or duplicate exhibit ID: ${item.id}`);
    if (item.kind !== 'art' || !item.title || !item.description || !item.alt || !/^\/art\/[a-z0-9-]+\.svg$/.test(item.asset)) throw new Error(`Invalid exhibit: ${item.id}`);
    if (!Number.isInteger(x) || !Number.isInteger(y) || x < 0 || y < 0 || x >= cols || y >= rows || blocked.has(key(x, y))) throw new Error(`Invalid placement: ${item.id}`);
    ids.add(item.id); blocked.add(key(x, y));
  }
  const spawn = [Math.floor(world.spawn.x / size), Math.floor(world.spawn.y / size)];
  if (blocked.has(key(spawn[0], spawn[1]))) throw new Error('Blocked spawn');
  const queue = [spawn];
  const reachable = new Set([key(spawn[0], spawn[1])]);
  for (let i = 0; i < queue.length; i++) {
    const [x, y] = queue[i];
    for (const [nx, ny] of [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]]) {
      const k = key(nx, ny);
      if (nx >= 0 && ny >= 0 && nx < cols && ny < rows && !blocked.has(k) && !reachable.has(k)) { reachable.add(k); queue.push([nx, ny]); }
    }
  }
  for (const { id, tile: { x, y } } of items) {
    if (![[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]].some(([nx, ny]) => reachable.has(key(nx, ny)))) throw new Error(`Unreachable exhibit: ${id}`);
  }
}
