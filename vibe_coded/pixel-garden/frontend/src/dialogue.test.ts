import { describe, expect, it, vi } from 'vitest';
import { DialogueScheduler, validRemark } from './dialogue';
import type { Remark } from './types';

const line: Remark = { text: 'A small kingdom of leaves.', source: 'ai' };
describe('dialogue scheduling', () => {
  it('suppresses quiet, hidden, unfocused and dialog states through the shared gate', async () => {
    const request = vi.fn().mockResolvedValue(line), display = vi.fn();
    const scheduler = new DialogueScheduler(display, request);
    await scheduler.trigger('welcome'); expect(request).not.toHaveBeenCalled();
    scheduler.setSuppressed(false); await scheduler.trigger('welcome');
    scheduler.setSuppressed(true); await scheduler.trigger('idle');
    expect(request).toHaveBeenCalledTimes(1);
  });
  it('enforces 45 seconds between calls', async () => {
    let now = 0; const request = vi.fn().mockResolvedValue(line);
    const scheduler = new DialogueScheduler(vi.fn(), request, () => now);
    scheduler.setSuppressed(false);
    await scheduler.trigger('welcome'); now = 44_999; await scheduler.trigger('idle');
    expect(request).toHaveBeenCalledTimes(1);
    now = 45_000; await scheduler.trigger('idle'); expect(request).toHaveBeenCalledTimes(2);
  });
  it('allows only one pending request and discards stale results even after resuming', async () => {
    let resolve!: (value: Remark) => void, now = 0;
    const request = vi.fn(() => new Promise<Remark>(done => { resolve = done; }));
    const display = vi.fn(), scheduler = new DialogueScheduler(display, request, () => now);
    scheduler.setSuppressed(false); const pending = scheduler.trigger('welcome');
    now = 60_000; await scheduler.trigger('idle'); expect(request).toHaveBeenCalledTimes(1);
    scheduler.setSuppressed(true); scheduler.setSuppressed(false); resolve(line); await pending;
    expect(display).not.toHaveBeenCalled();
  });
  it('supplies browser fallback when the backend is unavailable', async () => {
    const display = vi.fn(); const scheduler = new DialogueScheduler(display, vi.fn().mockRejectedValue(new Error('offline')));
    scheduler.setSuppressed(false); await scheduler.trigger('welcome');
    expect(display.mock.calls[0][0].source).toBe('fallback');
  });
  it('validates the response boundary', () => {
    expect(validRemark(line)).toBe(true);
    expect(validRemark({ text: 'x'.repeat(161), source: 'ai' })).toBe(false);
    expect(validRemark({ text: '', source: 'ai' })).toBe(false);
    expect(validRemark({ text: 'hello', source: 'unknown' })).toBe(false);
  });
  it('aborts a hung browser request and shows a fallback', async () => {
    vi.useFakeTimers();
    try {
      const display = vi.fn();
      const scheduler = new DialogueScheduler(display, (_request, signal) => new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new Error('aborted')));
      }));
      scheduler.setSuppressed(false);
      const pending = scheduler.trigger('welcome');
      await vi.advanceTimersByTimeAsync(9000);
      await pending;
      expect(display.mock.calls[0][0].source).toBe('fallback');
    } finally { vi.useRealTimers(); }
  });
});
