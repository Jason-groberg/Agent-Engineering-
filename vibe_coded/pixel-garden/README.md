# Pixel Garden

A small retro courtyard, six original botanical pixel studies, and Rowan: adventurer, amateur botanist. Walk with **WASD / arrow keys**, press **E** beside a plant, or open any exhibit from the field guide. **Tab** leaves the garden, **Escape** closes an exhibit, and **Quiet mode** stops remarks and new AI requests.

## Run on Windows

Open PowerShell in `Apps/pixel-garden`. Requires Node.js 24 (or another Vite-compatible release) and Python 3.11+. The scripts support the bundled Node/pnpm runtime in Codex as well as ordinary installations.

```powershell
# First-time dependency setup (isolated Python environment and locked JS packages)
.\scripts\run.ps1 install

# Build once, then serve the gallery and API together
.\scripts\run.ps1 build
.\scripts\run.ps1 api
```

Open **http://127.0.0.1:8000**. Stop the server with Ctrl+C. Run `build` again after changing the frontend or shared content. Restart the backend after changing content or server configuration.

For frontend development, keep `run.ps1 api` running and open a second terminal:

```powershell
.\scripts\run.ps1 dev
```

Open the printed Vite URL (normally **http://127.0.0.1:5173**). `/api` requests are proxied to port 8000. Both servers bind only to localhost. All assets and fonts are local; only AI generation needs internet access.

If PowerShell policy prevents running scripts, use these equivalent commands:

```powershell
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

The package manager is pinned to pnpm 11.25.0. On a normal Node/npm installation, `npx --yes pnpm@11.25.0 install --frozen-lockfile` installs frontend dependencies. Python dependencies are locked in `requirements.lock`; `requirements.txt` records the direct dependency ranges.

## AI configuration

The complete gallery works without credentials, using written fallback remarks. To enable live remarks, copy `.env.example` to `.env` inside this app and set `OPENAI_API_KEY`, or provide it through the backend process environment. No credentials belong in frontend code, `VITE_*` variables, or Git. The application loads only its own `.env`, not the repository-wide file.

| Setting | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | unset | Server-side OpenAI credential |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Responses API model |
| `REMARK_MAX_GENERATIONS` | `60` | Maximum generation attempts per server run; `0` disables them |

Rowan offers a welcome after entering, occasional first-discovery remarks, and a line every 60–90 seconds while the page is active. Client and server enforce a 45-second minimum between requests/generations. There is no queue, chat history, or tool use. Requests time out after eight seconds without retries; valid responses are cached by event/exhibit for ten minutes. Failures and exhausted limits use written fallback lines. Cache hits do not consume the generation budget.

Generation is suppressed while a dialog is open, the tab is hidden, the window is unfocused, or Quiet mode is enabled. In-flight browser requests are aborted and stale results discarded. Quiet mode is the only persistent browser preference; discoveries reset when the page reloads. Server limits and cache reset when the process restarts, so these controls are for a local prototype, not a public service.

## Project map

| Area | Responsibility |
| --- | --- |
| `AGENTS.md` | Scope, conventions, required checks, and content-authoring rules |
| `frontend/src/game/` | Loading/garden scenes, player input, nearby exhibits, world drawing |
| `frontend/src/main.ts` | Accessible field guide, native dialog, focus, and interface events |
| `frontend/src/dialogue.ts` | Request boundary, suppression, cooldown, stale-response handling |
| `frontend/src/theme.css` | Shared colors and typography |
| `frontend/public/art/` | Original local SVG plants, sprite sheet, and attribution |
| `content/` | Shared exhibit definitions, layout, and written remarks |
| `backend/` | FastAPI, content validation, bounded AI generation |
| `scripts/` | Windows task launcher and original sprite generator |

The Phaser 4.2.1 scene uses a 480×320 canvas, 16-pixel tiles, zero-gravity Arcade Physics, and nearest-neighbor artwork. Its large engine bundle is loaded separately from the HTML interface; Vite's bundle-size advisory is expected. The gallery list is fully usable without the game and moves above it on small screens. Reduced-motion mode disables the character's walking animation.

## Add or change an exhibit

1. Add an original integer-grid SVG to `frontend/public/art` and record attribution if needed.
2. Add an entry to `content/exhibits.json` with a unique `id`, `kind: "art"`, title, description, `/art/name.svg` asset, meaningful alt text, and integer tile coordinates.
3. Keep its tile clear of walls, the spawn, and other exhibits. At least one neighboring tile must be reachable. Content validation checks reachability and local asset existence.
4. Run checks and rebuild/restart. The field guide and backend context update from the same data; movement code does not change.

Garden bounds, spawn, and solid rectangles live in `content/garden.json`. The first courtyard's decorative paths and planting beds are drawn in the world renderer. Expand those visuals deliberately when changing the layout. Regenerate Rowan's 12-frame SVG with `python scripts/make_character.py` if the sprite source changes.

## API

- `GET /api/health` → `{ "status": "ok", "dialogue": "configured" | "fallback" }`. Configured means a key is present, not that provider access is verified.
- `POST /api/remark` accepts `{ "event": "welcome" | "discover" | "idle", "exhibit_id"?: "fern" }`. Discovery requires an ID. Unknown events, IDs, extra fields, and incorrect types receive HTTP 422 before contacting the model.
- Success or graceful fallback returns `{ "text": "…", "source": "ai" | "cache" | "fallback" }`.

The backend looks up trusted exhibit descriptions, requests a short family-friendly line with `store: false`, validates nonempty output up to 160 characters, and returns plain text. Logs contain outcome, latency, and token counts; never API keys or prompts.

## Verification

```powershell
.\scripts\run.ps1 check
.\scripts\run.ps1 test
.\scripts\run.ps1 build
```

Equivalent package scripts are `pnpm check`, `pnpm test`, and `pnpm build`; backend tests run with `.venv\Scripts\python.exe -m pytest backend/tests -q`.

Automated coverage includes all six reachable exhibits and assets; invalid placements; normalized movement and nearest-exhibit selection; dialogue cooldown, suppression, stale responses and offline fallback; API validation; model output validation; missing credentials; timeout; caching; concurrency; and the generation budget.

Implementation verification: 10 frontend and 24 backend tests passed; strict type checking and production build passed. A single live OpenAI request with the repository's existing credential succeeded, returning a valid 127-character remark; the credential was neither copied into this app nor printed. Browser visual verification was blocked by the browser tool's localhost URL policy, so the following manual checks remain:

- Enter the garden and walk in all directions, including diagonally. Confirm walls/plinths block movement and every plant is reachable.
- Inspect all six plants with E and from the list. Close using both buttons and Escape; confirm focus returns correctly.
- Change tabs or focus while walking; confirm movement stops and no key remains stuck.
- Enable Quiet mode and verify it survives reload; verify no new remark requests while quiet, hidden, or viewing art.
- Inspect the desktop layout and a narrow mobile viewport; confirm the field guide comes first on mobile and no horizontal overflow occurs.
- Enable reduced motion and confirm the walking animation stops while movement remains available.

No public hosting, accounts, puzzles, executable coding exercises, or two-way chat are included in this release.
