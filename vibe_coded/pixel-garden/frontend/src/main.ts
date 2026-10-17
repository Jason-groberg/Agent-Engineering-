import './styles.css';
import { exhibits } from './content';
import { DialogueScheduler } from './dialogue';
import { EventBus, type Exhibit } from './types';

function element<T extends HTMLElement>(id: string): T {
  const item = document.getElementById(id);
  if (!item) throw new Error(`Missing interface element: ${id}`);
  return item as T;
}
const bus = new EventBus();
const game = element('game');
const dialog = element<HTMLDialogElement>('art-dialog');
const quietButton = element<HTMLButtonElement>('quiet');
const speech = element('speech');
const seen = new Set<string>();
let quiet = false, entered = false, ready = false;
try { quiet = localStorage.getItem('pixel-garden-quiet') === 'true'; } catch { /* Private browsing remains usable. */ }
let previousFocus: HTMLElement | null = null;
const scheduler = new DialogueScheduler(remark => { speech.textContent = remark.text; });
function syncSuppression(): void { scheduler.setSuppressed(quiet || !entered || dialog.open || document.hidden || !document.hasFocus()); }
function renderQuiet(): void {
  quietButton.setAttribute('aria-pressed', String(quiet));
  quietButton.innerHTML = `Quiet mode <span aria-hidden="true">${quiet ? '●' : '○'}</span>`;
  speech.textContent = quiet ? 'Quiet mode is on. A little peace among the leaves.' : 'The plants seem friendly. I’m less certain about the cactus.';
  syncSuppression();
}
function markFound(exhibit: Exhibit): void {
  seen.add(exhibit.id);
  document.querySelector(`[data-exhibit="${exhibit.id}"]`)?.classList.add('found');
  element('progress').textContent = `${seen.size} / ${exhibits.length} found`;
}
function openExhibit(exhibit: Exhibit): void {
  if (dialog.open) return;
  previousFocus = document.activeElement as HTMLElement;
  bus.emit('pause', true);
  element('art-title').textContent = exhibit.title;
  element('art-description').textContent = exhibit.description;
  element('art-number').textContent = `FIELD NOTE ${String(exhibits.indexOf(exhibit) + 1).padStart(2, '0')} / 06`;
  const image = element<HTMLImageElement>('art-image'); image.src = exhibit.asset; image.alt = exhibit.alt;
  markFound(exhibit);
  dialog.showModal(); syncSuppression();
}
for (const [index, exhibit] of exhibits.entries()) {
  const li = document.createElement('li');
  const button = document.createElement('button');
  button.dataset.exhibit = exhibit.id;
  const art = document.createElement('img'); art.src = exhibit.asset; art.alt = ''; art.width = 48; art.height = 48;
  const copy = document.createElement('span');
  const name = document.createElement('strong'); name.textContent = exhibit.title;
  const label = document.createElement('small'); label.textContent = `NO. ${String(index + 1).padStart(2, '0')} · ${exhibit.id.toUpperCase()}`;
  copy.append(name, label);
  const arrow = document.createElement('span'); arrow.className = 'exhibit-arrow'; arrow.textContent = '↗'; arrow.setAttribute('aria-hidden', 'true');
  button.append(art, copy, arrow); button.addEventListener('click', () => openExhibit(exhibit));
  li.append(button); element('exhibits').append(li);
}
dialog.addEventListener('close', () => { bus.emit('pause', false); syncSuppression(); previousFocus?.focus({ preventScroll: true }); });
element('close-dialog').addEventListener('click', () => dialog.close());
element('back-to-garden').addEventListener('click', () => dialog.close());
quietButton.addEventListener('click', () => {
  quiet = !quiet;
  try { localStorage.setItem('pixel-garden-quiet', String(quiet)); } catch { /* Optional preference only. */ }
  renderQuiet();
});
function enterGarden(): void {
  if (!ready) return;
  const first = !entered; entered = true;
  element('entry').hidden = true;
  game.focus({ preventScroll: true }); syncSuppression();
  if (first) void scheduler.trigger('welcome');
}
element('enter').addEventListener('click', enterGarden);
game.addEventListener('pointerdown', enterGarden);
game.addEventListener('focus', enterGarden);
bus.on('inspect', openExhibit);
bus.on('discover', exhibit => { markFound(exhibit); void scheduler.trigger('discover', exhibit.id); });
bus.on('nearby', exhibit => { element('nearby').textContent = exhibit ? `${exhibit.id[0].toUpperCase() + exhibit.id.slice(1)} nearby · press E` : 'Find something that catches your eye.'; });
bus.on('ready', () => { ready = true; element<HTMLButtonElement>('enter').disabled = false; });
function showError(message: string): void { element('game-error').textContent = message; element('game-error').hidden = false; element('entry').hidden = true; }
bus.on('error', showError);
document.addEventListener('visibilitychange', syncSuppression);
window.addEventListener('blur', syncSuppression);
window.addEventListener('focus', syncSuppression);
renderQuiet();
let nextIdle = performance.now() + 60_000 + Math.random() * 30_000;
const idleTimer = setInterval(() => {
  if (performance.now() >= nextIdle) { void scheduler.trigger('idle'); nextIdle = performance.now() + 60_000 + Math.random() * 30_000; }
}, 1000);
element<HTMLButtonElement>('enter').disabled = true;
let instance: import('phaser').Game | undefined;
try { const gardenModule = await import('./game'); instance = gardenModule.createGarden(game, bus); }
catch { showError('The walkable garden could not start. All six exhibits are available in the field guide.'); }
if (import.meta.hot) import.meta.hot.dispose(() => { scheduler.setSuppressed(true); clearInterval(idleTimer); instance?.destroy(true); });
