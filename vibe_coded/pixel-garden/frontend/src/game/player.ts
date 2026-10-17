import Phaser from 'phaser';
import { movementVector } from './interaction';

export class PlayerController {
  readonly sprite: Phaser.Physics.Arcade.Sprite;
  private keys: Record<string, Phaser.Input.Keyboard.Key>;
  private direction = 'down';
  private reduced = matchMedia('(prefers-reduced-motion: reduce)');
  constructor(private scene: Phaser.Scene, x: number, y: number) {
    this.sprite = scene.physics.add.sprite(x, y - 7, 'rowan', 0).setDepth(y);
    this.sprite.setBodySize(8, 6).setOffset(4, 17).setCollideWorldBounds(true);
    const keyboard = scene.input.keyboard!;
    this.keys = keyboard.addKeys('W,A,S,D,UP,DOWN,LEFT,RIGHT,E', false) as typeof this.keys;
    ['down', 'left', 'right', 'up'].forEach((direction, i) => {
      if (!scene.anims.exists(`walk-${direction}`)) scene.anims.create({ key: `walk-${direction}`, frames: scene.anims.generateFrameNumbers('rowan', { frames: [i * 3, i * 3 + 1, i * 3, i * 3 + 2] }), frameRate: 8, repeat: -1 });
    });
  }
  clear(): void {
    this.scene.input.keyboard?.resetKeys();
    this.sprite.setVelocity(0, 0).stop();
  }
  update(active: boolean): boolean {
    if (!active) { this.clear(); return false; }
    const k = this.keys;
    const [vx, vy] = movementVector(k.A.isDown || k.LEFT.isDown, k.D.isDown || k.RIGHT.isDown, k.W.isDown || k.UP.isDown, k.S.isDown || k.DOWN.isDown);
    this.sprite.setVelocity(vx, vy).setDepth(this.sprite.y + 7);
    if (vx || vy) {
      this.direction = vy > 0 ? 'down' : vy < 0 ? 'up' : vx < 0 ? 'left' : 'right';
      if (!this.reduced.matches) this.sprite.play(`walk-${this.direction}`, true);
      else this.idle();
    } else this.idle();
    return Phaser.Input.Keyboard.JustDown(k.E);
  }
  private idle(): void { this.sprite.stop().setFrame(['down', 'left', 'right', 'up'].indexOf(this.direction) * 3); }
}
