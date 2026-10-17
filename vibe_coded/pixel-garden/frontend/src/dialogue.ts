import { remarks } from './content';
import type { Remark, RemarkEvent, RemarkRequest } from './types';

export function fallback(event: RemarkEvent): Remark {
  const choices = remarks[event];
  return { text: choices[Math.floor(Math.random() * choices.length)], source: 'fallback' };
}
export function validRemark(value: unknown): value is Remark {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<Remark>;
  return typeof item.text === 'string' && item.text.trim().length > 0 && item.text.length <= 160 && ['ai', 'cache', 'fallback'].includes(item.source ?? '');
}
export async function requestRemark(request: RemarkRequest, signal: AbortSignal): Promise<Remark> {
  const response = await fetch('/api/remark', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request), signal });
  if (!response.ok) throw new Error('Remark unavailable');
  const data: unknown = await response.json();
  if (!validRemark(data)) throw new Error('Invalid remark');
  return data;
}

export class DialogueScheduler {
  private lastRequest = -Infinity;
  private pending = false;
  private suppressed = true;
  private generation = 0;
  private controller?: AbortController;
  constructor(private display: (remark: Remark) => void, private request = requestRemark, private now = () => performance.now()) {}
  setSuppressed(value: boolean): void {
    this.suppressed = value;
    if (value) { this.generation++; this.controller?.abort(); }
  }
  async trigger(event: RemarkEvent, exhibitId?: string): Promise<void> {
    if (this.suppressed || this.pending || this.now() - this.lastRequest < 45_000) return;
    this.lastRequest = this.now(); this.pending = true;
    const generation = ++this.generation;
    const controller = new AbortController(); this.controller = controller;
    const timeout = setTimeout(() => controller.abort(), 9000);
    try {
      let result: Remark;
      try { result = await this.request({ event, ...(exhibitId ? { exhibit_id: exhibitId } : {}) }, controller.signal); }
      catch { result = fallback(event); }
      if (!this.suppressed && generation === this.generation) this.display(result);
    } finally { clearTimeout(timeout); this.pending = false; }
  }
}
