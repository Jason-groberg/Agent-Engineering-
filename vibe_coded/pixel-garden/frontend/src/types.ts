export interface Exhibit {
  id: string; kind: 'art'; title: string; description: string; asset: string; alt: string;
  tile: { x: number; y: number };
}
export type RemarkEvent = 'welcome' | 'discover' | 'idle';
export interface RemarkRequest { event: RemarkEvent; exhibit_id?: string }
export interface Remark { text: string; source: 'ai' | 'cache' | 'fallback' }
export interface GardenEvents {
  ready: undefined;
  nearby: Exhibit | null;
  inspect: Exhibit;
  discover: Exhibit;
  pause: boolean;
  error: string;
}
export class EventBus {
  private events = new EventTarget();
  emit<K extends keyof GardenEvents>(name: K, value: GardenEvents[K]): void {
    this.events.dispatchEvent(new CustomEvent(name, { detail: value }));
  }
  on<K extends keyof GardenEvents>(name: K, handler: (value: GardenEvents[K]) => void): () => void {
    const listener = (event: Event) => handler((event as CustomEvent<GardenEvents[K]>).detail);
    this.events.addEventListener(name, listener);
    return () => this.events.removeEventListener(name, listener);
  }
}
