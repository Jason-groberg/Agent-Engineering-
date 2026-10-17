# Codex CLI web development harness

Run the module from `Chat_Files`, or `python codex_harness.py` from `Codex_Harness`.
The wrapper invokes the installed **native Codex CLI**;
it does not create Responses API requests. `Simple_Harness` remains unchanged.

Prerequisites: Python 3.10+, Codex CLI on PATH with `codex login` completed,
and the existing `openai` / `python-dotenv` dependencies used by `tool_chat.py`.
The OpenAI SDK is used only to adapt usage records to the existing tracker.
Browser verification uses Python Playwright, Chromium, and axe-core, installed
privately inside this directory. Node/npm are not required. No plugins or MCP
servers are installed. Codex's hosted web search is enabled for planning/UI/developer.
The installed CLI checked during development was `0.162.1`.
The original native CLI check executed a local assert, inspected a PNG with
`view_image`, and produced usable native usage data. Browser integration tests
exercise real form/navigation interactions and detect accessibility defects.
The final native developer check also passed web search, a sandboxed request to
the local Playwright/axe runner, report reading, and desktop/mobile `view_image`
inspection. Planning handoffs and the three-pass repair loop are covered by tests.

Install the browser tools once (or restore them after a fresh checkout):

```powershell
python -m Codex_Harness.setup_browser_tools
```

Versions are pinned to Playwright 1.63.0 and axe-core 4.14.0. Python packages go
in `.browser_tools`, browser binaries in `.browsers`; both are ignored by Git.
The axe download is checked against the npm registry's SHA-512 integrity value.
Browser tools execute through the local Python wrapper with your normal user
permissions. Codex agents retain their native sandbox; installing browser tools
does not require sandbox ACL changes.

```powershell
python -m Codex_Harness.codex_harness "Build a responsive portfolio" --model YOUR_CODEX_MODEL
python -m Codex_Harness.codex_harness "Plan a portfolio; do not implement it" --model YOUR_CODEX_MODEL --role planning
```

From inside `Codex_Harness`, start with a saved prompt:

```powershell
python codex_harness.py --prompt "Resume_website/START_PROJECT.md" --model YOUR_CODEX_MODEL --project Resume_website
```

`--prompt` reads the file as UTF-8 and passes its contents as the task. Prompt paths
are relative to your current directory; absolute paths also work. Supply either
task text or `--prompt`, not both. Missing, unreadable, invalid UTF-8, and blank
prompt files stop before agents start. `--project` remains relative to the harness
directory. The module command also accepts `--prompt`.

Use a coding model available to your Codex login. The wrapper skips your personal
Codex configuration, so the model is explicit. It reuses your saved CLI authentication;
an OpenAI API key is not required when using an existing ChatGPT login.

## Workflow and boundaries

Planning intake -> plan -> UI -> developer -> review. The intake asks up to three
important unanswered questions in your terminal, then produces the plan from your
answers. A complete brief can skip unnecessary questions. If you leave an answer
blank or input is unavailable, implementation stops with the questions saved.
Each role starts a fresh, ephemeral Codex
run, receives preceding structured reports, and inspects the same project files.
The reviewer has an independent context, with the preceding reports supplied as evidence.

| Role | Sandbox | Responsibility |
| --- | --- | --- |
| planning | read-only | Scope, questions, browser journeys, official documentation search |
| ui | workspace-write | UI specification, local artwork, licensed assets, map design, image inspection |
| developer | workspace-write | Implementation, Playwright/axe checks, screenshots, documentation search |
| review | read-only | Independent code, browser/axe output, asset, and screenshot review |

The default project is `Codex_Harness/web_project`. `--project` selects another
subdirectory of `Codex_Harness`. The harness root and reserved directories cannot
be selected. Source, assets, and verification artifacts go inside the selected
project. Test output and screenshots belong in `.harness-verification` there.

The wrapper explicitly disables connector/plugin loading, hooks, extra skill
discovery and dependency installation, subagents, memories, tool suggestions,
built-in image generation, and browser/computer-control integrations. It clears
configured MCP servers, skips user configuration and project
config layers, and supplies scoped instructions instead of inherited AGENTS files.
Native shell/file tools and `view_image` remain available. Live web search is
enabled for planning, UI, and development; results are treated as untrusted data.
Codex requests browser checks through the existing shell, not an MCP tool. The
local wrapper executes the fixed browser helper outside the agent sandbox and
returns its real results. Requests cannot execute arbitrary host shell commands
or select a project outside the current developer run.
Admin-enforced configuration still applies; the wrapper cannot override it.

On Windows the wrapper selects the unelevated native sandbox. It never falls back
to unrestricted execution when commands fail. Approval policy is `never`: commands
that need broader permissions are denied and the role must report the blocker.
Sandboxing limits writes; read-only is not a guarantee of project-only read access.
The prompts restrict reads to relevant project files and the supplied helpers.
UI and developer phases enable sandboxed network access: UI can retrieve free
licensed artwork, and the developer starts the local website server. Browser processes run on the local
PC with fresh contexts, not your signed-in browser profile. Developer checks use
the supplied browser tools and existing project dependencies. A required project
library such as Phaser must be version-pinned and keep its license. Installing it
still depends on the available runtime and sandbox permissions; it is not a harness tool.

## Verification and results

The developer creates `browser_checks.json` for the planned user journeys, starts
the local app, and invokes the supplied request command through Codex's shell.
The request includes a per-run token; the local wrapper runs `browser_checks.py`
on your PC and returns results to the waiting agent. This avoids Windows sandbox
named-pipe restrictions without removing the agent sandbox. Requests time out after
190 seconds; browser execution is limited to 180 seconds and stopped when the
developer run ends. The runner
executes those journeys at desktop (1280x800) and mobile (390x844) sizes, checks
browser errors and failed asset responses, captures initial/after screenshots,
and audits both states with axe's WCAG A/AA rules through WCAG 2.2 AA.
Both developer and reviewer inspect screenshots with `view_image`. Automated axe
checks cover only part of accessibility; keyboard and visual assessment still matter.

The runner accepts local HTTP(S) sites only and blocks navigation to other hosts.
Browser contexts are fresh and do not use your signed-in browser profile. Credentials
are not allowed in target URLs. Use test data in journey specifications.

Example specification (created by the developer inside the project):

```json
{
  "cases": [{
    "name": "contact-navigation",
    "path": "/",
    "steps": [
      {"action": "click", "selector": "a[href='#contact']"},
      {"action": "expect_visible", "selector": "#contact"}
    ]
  }]
}
```

Supported actions are `click`, `fill`, `expect_visible`, `expect_text`, and
`expect_url`. Each case requires an interaction and an expected outcome. Names must
be unique and contain only letters, numbers, underscores, or hyphens.

For manual use, start the website's local server, then run:

```powershell
python -m Codex_Harness.browser_checks --project web_project --url http://127.0.0.1:3000
```

`--project` is relative to `Codex_Harness`, or an absolute path within it. The runner
saves screenshots and full axe results in `.harness-verification/browser-report.json`.
Exit code 1 means verification failed. A build alone cannot replace browser checks.

Reports use `report.schema.json`. Each check has a kind, result, and evidence.
The developer and review phases require passed `browser`, `accessibility`, and
`page` checks. Existing unit tests/builds also run when relevant. Blockers and missing
verification stop with exit code 2.
CLI errors raise an error and stop subsequent roles.

The reviewer lists defects instead of editing code. In the full workflow, findings
from a UI or developer `needs_changes` report are passed to the next role instead
of ending the run: UI hands off to developer, then developer hands off to review.
Failed checks remain visible and cannot count as completed verification. A `blocked`
report still stops the workflow. Findings
assigned to `developer` go back to developer -> review. Any finding assigned to `ui`
routes through UI -> developer -> review, so component/layout/asset changes get a UI
pass before implementation. Planning is not repeated during these bug-fix passes.

After three review passes, remaining findings are printed and saved, and the terminal
asks whether to continue for another three passes. Only `y` or `yes` authorizes more
work. Declining, blank input, or unavailable input stops without further modifications.
`--max-reviews` changes the number of review passes per batch. A `--role` invocation
runs only that role and never automatically starts other roles.

Records are saved under `Codex_Harness/runs/<timestamp-id>`: each role's prompt,
native JSONL events, stderr log, JSON report, the answered `brief.txt`, and the
combined `reports.json`. Repeated roles have numbered files such as `review-3.json`,
so earlier reports and execution records are preserved.
The reports are model assessments; inspect native command events and screenshot
files when auditing their evidence. The wrapper does not independently prove every
reported observation. CLI session rollout persistence is disabled with `--ephemeral`;
Codex may still maintain its normal authentication/cache/runtime metadata.

## Artwork and usage

PixelLab and remote paid artwork generation are disabled in this harness. No artwork
API key is required. The legacy `assets.py` entry point now refuses generation, so
older project scripts cannot use that helper to make paid requests. `Simple_Harness`
is unchanged. Existing PNGs remain usable and are not deleted or regenerated.

The UI role authors reproducible artwork with Canvas, SVG, or Pillow when available,
or uses free assets with verified licenses and recorded source URLs. Planning and
UI define the map; the developer implements it. Phaser belongs in the generated
game project, not in a new agent or MCP server. Preserve an existing renderer unless
an engine migration is requested. Keep accessible HTML outside the game canvas.

Useful options: [Phaser](https://github.com/phaserjs/phaser) for game runtime;
[Tiled](https://www.mapeditor.org/) for map editing and JSON export;
[Piskel](https://www.piskelapp.com/) or
[Pixelorama](https://github.com/Orama-Interactive/Pixelorama) for sprite editing;
[Pillow](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html) for local
procedural PNGs; and [Kenney Tiny Town](https://kenney.nl/assets/tiny-town) for CC0 tiles.
Tiled, Piskel, and Pixelorama remain optional editors; they are not installed or
automated by the harness. Phaser is supplied through the helper below.

Phaser 4.2.1 is supplied through `phaser.py`. Setup downloads the official npm
archive, checks its SHA-512 integrity and package version, and caches only the
browser runtime and MIT license in `.game_tools/phaser-4.2.1` (ignored by Git).
From `Codex_Harness`, restore the cache after a fresh checkout with:

```powershell
python phaser.py
```

The developer receives this project-scoped shell tool:

```powershell
python phaser.py --project Resume_website
```

That command copies the cached runtime and license to `vendor/phaser-4.2.1/` in
the selected project and returns both paths. It needs no network, Node, or npm;
identical copies are reused, and different existing files are not overwritten.
Include `vendor/phaser-4.2.1/phaser.min.js` locally in HTML. This makes the engine
available; converting an existing website still requires an implementation request.
UI web search is enabled for finding pixel assets on original creators' pages,
checking licenses, and recording frame/tile geometry.

The wrapper calls the same existing tracker functions: `UsageTracker()`,
`track(response, elapsed, task)`, `print_summary()`, and `save_to_file()`.
Native `turn.completed` token totals are adapted into an OpenAI response-shaped
record without sending an API request. These are **per-turn totals**, rather than
every internal inference request. Missing reasoning-token detail is recorded as
zero; total output tokens are retained. Tracker cost figures are API-rate estimates,
not necessarily actual ChatGPT-plan billing.
The shared tracker controls its own output location and is not modified here.

## Your first website

Start with a short brief covering purpose, audience, pages/sections, main actions,
available content, visual style, and constraints. A detailed technical spec is
optional. Put any local reference images in the project and mention their paths.

```powershell
$siteBrief = @'
Build a portfolio for a freelance photographer.
Audience: prospective wedding and portrait clients.
Sections: introduction, gallery, about, and contact.
Main action: email me through a mailto link; no backend or login.
Style: warm neutral colors, large photography, restrained typography.
Use clearly labeled placeholder photos and copy for now.
Make it work on phones and support keyboard navigation.
Use the existing stack if there is one; otherwise use plain HTML/CSS/JavaScript.
'@
python -m Codex_Harness.codex_harness $siteBrief --model YOUR_CODEX_MODEL --role planning
```

Read the planning report in the printed run directory. The planner states reasonable
assumptions and asks only the important unresolved questions before producing the
plan. You answer in the terminal; no implementation starts during `--role planning`.
To preserve those answers, load the saved `brief.txt` from the printed run directory,
add any corrections, then run the full workflow:

```powershell
$siteBrief = Get-Content "Codex_Harness/runs/YOUR_RUN/brief.txt" -Raw
python -m Codex_Harness.codex_harness $siteBrief --model YOUR_CODEX_MODEL
```

The full workflow performs planning again, using the answered brief, and automatically
routes review findings through the repair loop described above. For work stopped at
a review limit, you can authorize another batch at the prompt. To resume after exiting,
provide the requested changes as a new full-workflow task on the same `--project`.

## Follow-up changes

Every run saves the initial answered brief, latest answered brief, and latest role
reports in `sessions/<project-hash>.json`, outside the website's served directory.
The next run for that project receives this context automatically and reads the
existing code. The newest task takes precedence; roles plan and implement only
the requested delta. Full runs retain the UI/developer/review repair loop and the
three-pass user decision. Each role still starts a fresh Codex session; this is
project context reuse, not a resumed CLI conversation.

From inside `Codex_Harness`, for example:

```powershell
python codex_harness.py "Add a pond beside the garden; preserve the rest of the map" --model YOUR_CODEX_MODEL --project Resume_website
python codex_harness.py --prompt "Resume_website/CHANGES.md" --model YOUR_CODEX_MODEL --project Resume_website
```

No new iteration flag is required. Different projects receive separate context.
Session files are ignored by Git; writes are atomic. Run sequentially for the same
project, because the latest completed save replaces its context. Single-role runs
reuse context but do not automatically start other roles. Older runs made before
this feature are not automatically imported; include important prior answers in
the first follow-up prompt or supply their saved `brief.txt` through `--prompt`.
Changing artwork policy does not migrate the current website to Phaser or redraw it.

## Checks and sources

```powershell
python -m unittest Codex_Harness.test_codex_harness -v
python -m unittest Codex_Harness.test_browser_checks -v
python -m unittest Codex_Harness.test_phaser -v
```

Harness tests use a local fake CLI subprocess and mocked tracker imports. Browser
tests start a temporary local website, run Chromium and axe, and verify both passing
and deliberately broken pages. They do not inspect the tracker or call paid services.
Install the tools first so the real browser tests run instead of being skipped.

Sources: [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[Codex web search](https://learn.chatgpt.com/docs/web-search),
[Python Playwright](https://playwright.dev/python/docs/intro),
[axe API](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md).
