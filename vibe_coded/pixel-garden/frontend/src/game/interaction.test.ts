import { describe, expect, it } from 'vitest';
import { exhibits, garden, validateContent } from '../content';
import { nearestExhibit, movementVector } from './interaction';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

describe('garden content and movement', () => {
  it('makes every original exhibit reachable and supplies its local asset', () => {
    expect(() => validateContent(exhibits)).not.toThrow();
    for (const exhibit of exhibits) expect(existsSync(fileURLToPath(new URL(`../../public${exhibit.asset}`, import.meta.url)))).toBe(true);
  });
  it('rejects duplicate IDs, overlaps, walls, and unreachable exhibits', () => {
    expect(() => validateContent([...exhibits, exhibits[0]])).toThrow();
    const items = structuredClone(exhibits); items[0].tile = { x: 0, y: 0 };
    expect(() => validateContent(items)).toThrow();
    const world = structuredClone(garden);
    const { x, y } = exhibits[0].tile;
    world.obstacles.push(...[[x-1,y],[x+1,y],[x,y-1],[x,y+1]].map(([x,y]) => ({ x: x * 16, y: y * 16, width: 16, height: 16 })));
    expect(() => validateContent(exhibits, world)).toThrow('Unreachable');
  });
  it('normalizes diagonal motion and cancels opposite keys', () => {
    expect(Math.hypot(...movementVector(false, true, false, true))).toBeCloseTo(72);
    expect(movementVector(true, true, true, true)).toEqual([0, 0]);
    expect(movementVector(false, false, true, false)).toEqual([0, -72]);
  });
  it('chooses the closest in-range exhibit and ignores distant items', () => {
    expect(nearestExhibit(104, 120, exhibits)?.id).toBe('fern');
    expect(nearestExhibit(240, 164, exhibits)).toBeNull();
    expect(nearestExhibit(0, 0, exhibits)).toBeNull();
  });
});
