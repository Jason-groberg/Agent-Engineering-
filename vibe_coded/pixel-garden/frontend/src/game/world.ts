import Phaser from 'phaser';
import { garden } from '../content';

export function drawWorld(scene: Phaser.Scene): void {
  const g = scene.add.graphics().setDepth(-100);
  const fill = (color: number, x: number, y: number, w: number, h: number) => g.fillStyle(color).fillRect(x, y, w, h);
  fill(0x344d3d, 0, 0, 480, 320);
  // Deterministic hand-laid ground: no shifting decorations between visits.
  for (let y = 32; y < 304; y += 8) for (let x = 16; x < 464; x += 8) {
    const seed = (x * 73 + y * 29) % 101;
    if (seed < 22) fill(seed < 11 ? 0x3c5742 : 0x415d44, x, y, 5, 3);
    if (seed > 95) { fill(0x6c8051, x, y, 1, 3); fill(0x6c8051, x + 2, y + 1, 1, 2); }
  }
  // A wide stone loop links all six beds.
  const onPath = (x: number, y: number) => (y >= 144 && y < 184) || (x >= 216 && x < 256 && y >= 64 && y < 280)
    || ((x >= 88 && x < 120 || x >= 360 && x < 392) && y >= 96 && y < 256);
  for (let y = 40; y < 296; y += 8) for (let x = 24; x < 456; x += 8) if (onPath(x, y)) {
    const color = [0x8c8870, 0x99927a, 0x827f69][(x / 8 + y / 8 * 7) % 3];
    fill(0x505b45, x, y, 8, 8); fill(color, x + 1, y + 1, 7, 7);
    if ((x + y) % 32 === 0) fill(0xb0a88a, x + 2, y + 1, 4, 1);
  }
  // Raised beds frame the exhibits, while their centers remain walkable around plinths.
  for (const [x, y] of [[72, 72], [200, 56], [344, 72], [72, 184], [200, 200], [344, 184]]) {
    fill(0x283d31, x, y, 64, 48); fill(0x667250, x, y, 64, 3);
    fill(0x46523a, x + 3, y + 3, 58, 42);
    for (let i = 0; i < 7; i++) fill(0x596246, x + 6 + i * 8, y + 38, 3, 2);
  }
  for (const o of garden.obstacles) {
    fill(0x283831, o.x, o.y, o.width, o.height);
    for (let y = o.y; y < o.y + o.height; y += 8) for (let x = o.x; x < o.x + o.width; x += 16) {
      fill(0x66705d, x + 1, y + 1, 14, 6); fill(0x849079, x + 1, y + 1, 14, 1);
    }
  }
  // Ivy and small wildflowers soften the courtyard's masonry.
  for (let x = 24; x < 464; x += 40) {
    fill(0x3b5b3f, x, 21, 4, 17); fill(0x59764d, x - 3, 28, 10, 4);
    fill(0x7f9457, x + 1, 22, 4, 3);
  }
  for (const [x, y] of [[38, 70], [435, 104], [40, 260], [420, 268], [178, 48], [307, 284]]) {
    fill(0x779158, x, y + 3, 2, 6); fill(0xc6ac76, x - 2, y, 6, 3); fill(0xe5c990, x, y - 2, 2, 6);
  }
  // Entrance arch and a small resting bench are decorative, not invisible obstacles.
  fill(0x354a38, 212, 292, 48, 12); fill(0xc0ad82, 224, 294, 24, 10);
  fill(0x2d4134, 300, 56, 41, 16); fill(0x927451, 300, 54, 40, 5); fill(0xb39664, 300, 54, 40, 2);
}
