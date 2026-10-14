# Working in this repo

## What this app is

- The engine is a **CLI**, not a server: `src/main.py` is a Click group with `init`, `status` and
  `execute "<nrx code>"`. The declared entry point is `main:cli`. Nothing in the repo listens on a port.
- `web/server.py` is a small, dependency-free dashboard (stdlib `http.server`) that **drives that CLI**
  in a subprocess so the engine is usable from the browser preview on port 3000. It holds no engine
  logic — put features in the CLI, not in the dashboard.
- `nishkraman/awaken.py` is a standalone "awakening" script that is not part of the CLI.

## Run it

```bash
docker compose -f docker-compose.base44.yml up -d --build
# CLI parity with the dashboard:
docker compose -f docker-compose.base44.yml exec zyphus python src/main.py status
docker compose -f docker-compose.base44.yml exec zyphus python src/main.py execute 'print("hi")'
```

Source is bind-mounted, so code edits need no rebuild. A change to `requirements.txt` or
`Dockerfile.base44` does: re-run `up -d --build`.

## Gotchas learned the hard way

- `src/main.py` used to `from src.models.user import db`, which needs `flask_sqlalchemy` — that is not in
  `requirements.txt`, so **every** CLI command crashed on import. Flask had already been removed from the
  project (see the comment there), the import was dead, and it was deleted. `src/models/user.py` still
  imports `flask_sqlalchemy`; don't import it unless you add the dependency.
- Heavy libraries (`torch`, `numpy`, `pandas`, `sklearn`, `scipy`, `matplotlib`, `seaborn`, `networkx`,
  `bs4`, `requests`) appear in modules that are **not reachable** from `src/main.py`
  (`perpetual_self_train_loop`, `universal_cognition_mapper`, `universal_model_extractor`,
  `persistent_memory_cores`, …). `requirements.txt` deliberately omits them — do not install them for the CLI.
- Node.js is required by `src/js_module_bridge_fixed.py` and is installed in the image. Its `test_module()`
  only checks that node exists, so `js_modules_bridge: OK` means "node found", **not** "modules executed".
- The modules under `src/modules/**` are ESM (`export class …`) while `src/modules/node_wrapper.js` uses
  `require()`, so the bridge's CommonJS load path cannot load them. Nothing in the CLI path exercises this today.
- `setup.py` still hardcodes `find_packages(where='/home/ubuntu/Zyphus/Zyphus/src')`, so `pip install .` /
  `pip install -e .` fails. Run from source instead — that is what the container command does.
- The engine persists state **inside the repo** (`devmind/memory/**`, `nishkraman/logs/**`, root `*.db`).
  It is bind-mounted and writable. `PYTHONDONTWRITEBYTECODE=1` stops `__pycache__` churn in git.
- No credentials are needed to run the stack. `src/dynamic_code_generator.py` reads `OPENAI`/`ANTHROPIC`
  keys but is not part of the CLI runtime, so it is not wired into compose.
- Sandbox specifics: `web/server.py` is the only preview-only addition, and it exists solely because the
  preview renders an HTTP page while this project is a CLI. `BASE44_PREVIEW_MODE` is passed through to the
  service and reported as `preview_mode` in `/api/health`; no shared application configuration or behaviour
  changes whether it is set to `1` or unset.

## Verifying it works

```bash
curl -fsS http://localhost:3000/api/health   # {"engine_importable": true, "node_available": true, ...}
curl -fsS http://localhost:3000/api/status   # overall HEALTHY, 4/4 components OK
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"code":"print(\"Hello from NRX\")"}' http://localhost:3000/api/execute
```

The dashboard runs `status` on load, so a broken engine shows up as `UNHEALTHY` (or as a red log panel)
instead of a blank page. A `status` call takes ~5–10s because each CLI invocation re-initializes the
engine from scratch.

## The agent layer (`src/agent/`, stdlib only)

- `tools.py` - the real tools: `run_shell`, `read_file`, `write_file`, `list_dir`, `http_request`,
  `web_fetch`. They run inside the container with **full access by design**: no allow-lists, no path
  restrictions, no dry run. Accountability comes from the action log instead, not from limits.
- `store.py` - durable state in `devmind/agent/agent.db` (WAL): a task queue (claim/complete/fail with
  retries, backoff and a lease) plus an action log of every tool call with arguments, output and duration.
- `brain.py` - the decision maker, currently `RuleBasedBrain`. It follows explicit instructions and, when
  the queue is empty, proposes its own inspection work. **This is the seam for a real model**: implement
  `plan(task)` and `propose()` and pass the new brain to `AgentLoop(brain=...)`.
- `loop.py` - one tick = claim a task, plan it, run the tools, record everything; an idle tick proposes
  self-directed work. `get_loop()` is a process-wide singleton so the dashboard and CLI share it.
- `cli.py` - `python src/main.py agent status|tools|tasks|run|tick|forever`.

Task instruction prefixes: `shell:<command>`, `fetch:<url>`, `@tool <name> {json arguments}`, `self:*`
for the self-directed routines. Anything else makes it look around the repo (`list_dir` + `README.md`).
A tool argument containing `$last` is replaced with the previous call's output, which is how multi-step
tasks chain (read a file, then write a note containing it).

Running it: the loop autostarts inside the dashboard process when `ZYPHUS_AGENT_AUTOSTART=1` (set in
compose). State is in SQLite, so a restart loses nothing - a task claimed when the process died is
reclaimed after its lease. Pacing knobs: `ZYPHUS_AGENT_INTERVAL` (default 15s) and
`ZYPHUS_AGENT_SELF_INTERVAL` (default 300s, how often it invents its own work).

Two deliberate properties, don't "fix" them by accident:

- The dashboard exposes the loop **read-only** (`GET /api/agent`). There is no inbound endpoint that
  runs tools, because the preview URL is publicly reachable - an unauthenticated exec endpoint would let
  anyone with the link drive the container. Add remote control only behind a token.
- Self-directed notes accumulate in `devmind/agent/notes/`; nothing prunes them yet.

Verified end to end: shell tool ran a real command in the container; a self-directed task chained
`list_dir` → `write_file` into a note; queue and action log survived a container restart and the loop
continued on its own.
