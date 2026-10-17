# Web development harness

Run from `Chat_Files` with Python and the same `openai` and `python-dotenv`
dependencies used by `tool_chat.py`. No new dependencies are needed.
The harness source, tests, and this README are in `Chat_Files/Simple_Harness`.

This is a Responses API harness with four sequential roles, rather than a wrapper
around the Codex CLI. Supply the API coding model you want to use; no model is
hardcoded. Codex CLI login does not authenticate Responses API requests.

Set `OPENAI_API_KEY` and, for asset generation, `PIXELLAB_API_KEY` in the environment
or `Chat_Files/.env`. Never commit that file. Only this explicit `.env` is loaded.

```powershell
python -m Simple_Harness.dev_harness "Build a responsive portfolio with a pixel-art mascot" --model YOUR_CODING_MODEL
python -m Simple_Harness.dev_harness "Review the portfolio for bugs and accessibility" --model YOUR_CODING_MODEL --role review
```

The default project is `Chat_Files/web_project`. `--project` selects another
subdirectory inside `Chat_Files`; the `Chat_Files` root itself is not a project.
New files are created there; the developer can replace existing project text files.

The workflow is planning -> UI -> developer -> review. All four roles share the
task and preceding responses/tool results. Role instructions and tool permissions
live in `dev_harness.py`. Planning and review can list and read files, the UI role
can additionally generate assets, and the developer can write text files.
An incomplete response or exhausted tool loop stops the workflow. Review findings
are printed for the user; the harness does not automatically repair them.

File tools reject paths outside the project, including resolved symlink escapes,
`.env` files, credential directories, the user's excluded directories, and dependency
trees. Listings show one directory at a time; text reads are limited to 100 KB.
There is no shell, browser, screenshot, or image-inspection tool. Run the developer's
suggested tests/build commands yourself and visually check the result.

## PixelLab

The UI role calls `generate_asset(description, path, width, height, no_background)`.
It makes one paid request to `POST https://api.pixellab.ai/v1/generate-image-pixflux`
with bearer authentication, `description`, `image_size`, and `no_background`.
It accepts raw or data-URL base64 PNG responses, saves a new project-relative PNG,
and returns the file path and PixelLab's reported `usage`. Existing assets are
never overwritten. Dimensions are conservatively limited to 32..400 per side.
The v1 docs describe blank backgrounds above 200x200 rather than full transparency.

HTTP errors and uncertain network outcomes are returned to the role without
automatic retries. The UI instructions request a CSS fallback instead of retrying.
Model behavior can still cause multiple asset calls; this version has no spending cap.

OpenAI usage uses the exact `tool_chat.py` calls: `UsageTracker()`,
`tracker.track(response, elapsed, user_input)` for every response,
`tracker.print_summary()`, and `tracker.save_to_file()`. Summary and save also run
when a workflow fails or is interrupted. PixelLab usage is separate and appears
in the asset tool result; it is not passed to the OpenAI usage tracker.
The tracker is reused unchanged; its output location is controlled by that module.

Sources: [PixelLab v1 docs](https://api.pixellab.ai/v1/docs),
[PixelLab OpenAPI schema](https://api.pixellab.ai/v1/openapi.json),
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling).

## Checks

```powershell
python -m unittest Simple_Harness.test_dev_harness -v
```

The tests use mocked Responses and PixelLab clients and never import or inspect
the existing tracker. They do not make paid API requests.
