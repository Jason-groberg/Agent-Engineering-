# Pixel Garden

## Product and scope
Build a local, desktop-first, single-screen retro plant gallery. A pixel adventurer walks among six exhibits and occasionally makes short AI-generated remarks. Keep puzzles, code execution, public hosting, larger maps, and two-way chat out of this release.

## Architecture
- `frontend/`: strict TypeScript, Vite, Phaser, semantic HTML, plain CSS. Separate scenes, movement, interaction, and dialogue scheduling.
- `backend/`: FastAPI and OpenAI Responses API. Bind to localhost. Serve the built frontend from the same origin; proxy `/api` during development.
- `content/`: shared JSON exhibit definitions, world layout, and fallback remarks. Content is the source of truth for both runtimes.
- Game-to-interface communication uses typed events. Every exhibit must also be accessible through the HTML gallery and native dialog.

## Rules
- Preserve unrelated repository changes. Keep this application independent of existing Python scripts.
- Keep API keys and model calls on the server. Never use frontend environment variables for secrets, log secrets/prompts, or commit `.env` files.
- Render model output as text, validate input and output, bound generation by cooldown, timeout, and per-run limits. Missing AI must never prevent exploration.
- Use small focused modules, strict TypeScript, typed request boundaries, and readable names. Avoid new dependencies without a concrete need.
- Use a 480x320 world, 16-pixel tiles, nearest-neighbor graphics, original local integer-grid SVGs, moss/stone/earth/parchment colors, and readable interface text. Record third-party asset attribution if added.
- Pause and clear input when focus is lost or a dialog opens. Honor reduced motion and Quiet mode. No keyboard traps.
- Do not deploy or widen scope as part of routine implementation.

## Development and checks
See README.md for Windows setup. From this folder, `./scripts/run.ps1 dev` starts Vite and `./scripts/run.ps1 api` starts the backend using the app-local Python environment. The package manager is pnpm 11.25.0; preserve its lockfile.
Before completion, run `./scripts/run.ps1 check`, `./scripts/run.ps1 test`, and `./scripts/run.ps1 build`. Equivalent package scripts are `pnpm check`, `pnpm test`, and `pnpm build`, plus `.venv/Scripts/python.exe -m pytest backend/tests`. Browser-check movement, collisions, all six interactions, focus restoration, responsive gallery, and Quiet mode. Mock AI in automated tests; disclose any unverified live API behavior.

## Adding an exhibit
Add an original SVG to `frontend/public/art`, then add a unique entry to `content/exhibits.json` with ID, art kind, title, description, asset, alt text, and tile position. Keep the position clear of walls and other exhibits, with a reachable adjacent interaction tile. Run content validation/tests. Do not change player movement to add content.
