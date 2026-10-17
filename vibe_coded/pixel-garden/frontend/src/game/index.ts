import Phaser from 'phaser';
import { exhibits, garden, validateContent } from '../content';
import { EventBus, type Exhibit } from '../types';
import { PlayerController } from './player';
import { nearestExhibit } from './interaction';
import { drawWorld } from './world';

export function createGarden(parent: HTMLElement, bus: EventBus): Phaser.Game {
  class LoadingScene extends Phaser.Scene {
    constructor() { super('loading'); }
    preload(): void {
      validateContent(exhibits);
      this.load.on('loaderror', () => bus.emit('error', 'Some garden artwork could not load. You can still browse the collection below.'));
      for (const exhibit of exhibits) this.load.svg(exhibit.id, exhibit.asset);
      this.load.svg('rowan', '/art/rowan.svg');
    }
    create(): void {
      const texture = this.textures.get('rowan');
      for (let i = 0; i < 12; i++) texture.add(i, 0, i * 16, 0, 16, 24);
      this.scene.start('garden');
    }
  }
  class GardenScene extends Phaser.Scene {
    private player!: PlayerController;
    private paused = false;
    private nearby: Exhibit | null = null;
    private visited = new Set<string>();
    private prompt!: Phaser.GameObjects.Text;
    constructor() { super('garden'); }
    create(): void {
      drawWorld(this);
      this.physics.world.setBounds(16, 32, 448, 272);
      const obstacles = this.physics.add.staticGroup();
      for (const o of garden.obstacles) {
        const zone = this.add.zone(o.x + o.width / 2, o.y + o.height / 2, o.width, o.height);
        obstacles.add(zone);
      }
      for (const exhibit of exhibits) {
        const x = exhibit.tile.x * 16 + 8, y = exhibit.tile.y * 16 + 8;
        this.add.rectangle(x, y + 6, 22, 10, 0x26392e).setDepth(y - 2);
        this.add.rectangle(x, y + 2, 20, 10, 0x89917a).setDepth(y - 1);
        this.add.rectangle(x, y - 2, 20, 3, 0xb0b296).setDepth(y - 1);
        this.add.image(x, y + 1, exhibit.id).setDisplaySize(32, 32).setOrigin(0.5, 1).setDepth(y);
        obstacles.add(this.add.zone(x, y + 2, 18, 12));
      }
      this.player = new PlayerController(this, garden.spawn.x, garden.spawn.y);
      this.physics.add.collider(this.player.sprite, obstacles);
      this.prompt = this.add.text(0, 0, 'E · inspect', { fontFamily: 'monospace', fontSize: '8px', color: '#f0e3bb', backgroundColor: '#23372e', padding: { x: 4, y: 3 } }).setOrigin(0.5, 1).setDepth(1000).setVisible(false);
      const unpause = bus.on('pause', value => { this.paused = value; this.player.clear(); });
      const blur = () => this.player.clear();
      const preventScroll = (event: KeyboardEvent) => {
        if (parent.contains(document.activeElement) && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) event.preventDefault();
      };
      window.addEventListener('blur', blur);
      document.addEventListener('visibilitychange', blur);
      parent.addEventListener('keydown', preventScroll);
      this.events.once('shutdown', () => {
        unpause(); window.removeEventListener('blur', blur); document.removeEventListener('visibilitychange', blur); parent.removeEventListener('keydown', preventScroll);
      });
      bus.emit('ready', undefined);
    }
    update(): void {
      if (!this.player) return;
      const active = !this.paused && !document.hidden && document.hasFocus() && parent.contains(document.activeElement);
      const interact = this.player.update(active);
      const sprite = this.player.sprite;
      const nearest = nearestExhibit(sprite.x, sprite.y + 7, exhibits);
      if (this.nearby?.id !== nearest?.id) { this.nearby = nearest; bus.emit('nearby', nearest); }
      this.prompt.setVisible(Boolean(nearest) && active);
      if (nearest) {
        this.prompt.setPosition(nearest.tile.x * 16 + 8, nearest.tile.y * 16 - 24);
        if (active && !this.visited.has(nearest.id)) { this.visited.add(nearest.id); bus.emit('discover', nearest); }
        if (interact) bus.emit('inspect', nearest);
      }
    }
  }
  return new Phaser.Game({ type: Phaser.AUTO, parent, width: garden.width, height: garden.height,
    backgroundColor: '#344d3d', pixelArt: true, roundPixels: true,
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    physics: { default: 'arcade', arcade: { gravity: { x: 0, y: 0 }, debug: false } },
    scene: [LoadingScene, GardenScene], banner: false,
  });
}
