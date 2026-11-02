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
  keys but is not part of the CLI runtime, so it is not wired into compose. The optional secrets are
  `ZYPHUS_CONTROL_TOKEN` (arms the dashboard task box), `OPENAI_API_KEY` (model-backed brain), and the
  connector credentials `GITHUB_TOKEN` / `SLACK_WEBHOOK_URL` (defaults for a `github` / `slack` connector -
  `config.DEFAULT_CONNECTOR_ENVS`). All of them arrive through `env_file: /run/base44/app.env`, never
  through `environment:` - a value there would permanently outrank the dashboard. The stack boots and works
  with none of them; `config.env_present("<NAME>")` reports which one reached the process without printing
  any value.
- `requirements.txt` now includes **numpy**: `emotion_200d_system`, `mood_stabilizer`, `cluster_modulation`
  and friends cannot even be imported without it, so the agent's mood would be permanently "unavailable".
  `Dockerfile.base44` installs **espeak-ng**, which is the agent's voice (`speak` renders a wav from a
  headless container; the dashboard plays it). Both are image changes, so a rebuild is needed after
  touching them.
- The agent's `js_module` tool loads the `src/modules/**` ES modules through `src/modules/run_module.mjs`
  (dynamic `import()`), which is the only thing in the repo that can actually read them. Note that
  `js_module_bridge_fixed.py` **rewrites** `src/modules/node_wrapper.js` on every init, so editing that
  file is pointless - change the bridge or use the runner.
- `src/heartbeat_engine.py` models brain rhythms, not a heart: its patterns are neural bands (gamma 40 Hz,
  beta 20 Hz, alpha 10 Hz, theta 6 Hz, delta 2 Hz) and its own `target_bpm` field is a 60000/interval_ms
  artefact (gamma reads "2400 bpm"). Report the rhythm and its Hz, never a heart rate.
- `embodiment.links()` is the quickest way to see whether the biology modules are importable in the
  running image; `python -c "import src.emotion_200d_system"` failing means numpy is missing.
- Sandbox specifics: `web/server.py` is the only preview-only addition, and it exists solely because the
  preview renders an HTTP page while this project is a CLI. `BASE44_PREVIEW_MODE` is passed through to the
  service and reported as `preview_mode` in `/api/health`; no shared application configuration or behaviour
  changes whether it is set to `1` or unset.

## Verifying it works

```bash
curl -fsS http://localhost:3000/api/health   # {"engine_importable": true, "node_available": true, ...}
curl -fsS http://localhost:3000/api/status   # overall HEALTHY, 4/4 components OK
curl -fsS http://localhost:3000/api/capabilities   # models, custom APIs, connectors, index size
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"code":"print(\"Hello from NRX\")"}' http://localhost:3000/api/execute
```

The new capability tools, from the CLI:

```bash
docker compose -f docker-compose.base44.yml exec zyphus python src/main.py agent run 'rag: index src'
docker compose -f docker-compose.base44.yml exec zyphus \
  python src/main.py agent run 'rag: how does the loop pace itself with a backlog?'
docker compose -f docker-compose.base44.yml exec zyphus python src/main.py agent run 'model: list'
# a real call through the custom-API registry, against the dashboard's own health route:
docker compose -f docker-compose.base44.yml exec zyphus \
  python src/main.py agent run 'api: register self http://localhost:3000'
docker compose -f docker-compose.base44.yml exec zyphus \
  python src/main.py agent run 'api: call self /api/health GET'
# the same endpoint, through the dashboard, needs the control token:
curl -sS -X POST -H 'Content-Type: application/json' -H "X-Zyphus-Token: $ZYPHUS_CONTROL_TOKEN" \
  -d '{"instructions":"tool rag {\"action\":\"query\",\"text\":\"fusion engine\"}"}' \
  http://localhost:3000/api/agent/task
```

The agent layer (the dashboard's Agent/Body/Voice cards read the same data):

```bash
curl -fsS http://localhost:3000/api/agent | python -m json.tool | head -50
docker compose -f docker-compose.base44.yml exec zyphus python src/main.py agent consolidate --dry-run
docker compose -f docker-compose.base44.yml exec zyphus python src/main.py agent run 'vitals'
docker compose -f docker-compose.base44.yml exec zyphus python src/main.py agent run 'say: hello'
docker compose -f docker-compose.base44.yml exec zyphus \
  python src/main.py agent run 'read src/agent/senses.py and write a note about it'

# Remote control refuses without the token (503 when none is configured, 401 when wrong):
curl -i -X POST -H 'Content-Type: application/json' \
  -d '{"instructions":"vitals"}' http://localhost:3000/api/agent/task
# ...and works with it:
curl -sS -X POST -H 'Content-Type: application/json' \
  -H "X-Zyphus-Token: $ZYPHUS_CONTROL_TOKEN" \
  -d '{"instructions":"shell: echo hello"}' http://localhost:3000/api/agent/task
```

A `vitals` call is a ~1.5 s heartbeat burst plus a numpy import, so the loop caches the body reading for
10 s - call it twice in a row and the second is instant. Utterances are served from
`/api/agent/voice/<voice-...wav>`, and the wav filenames are timestamped, so a fresh one only appears when
the agent actually speaks.

The dashboard runs `status` on load, so a broken engine shows up as `UNHEALTHY` (or as a red log panel)
instead of a blank page. A `status` call takes ~5–10s because each CLI invocation re-initializes the
engine from scratch.

## The agent layer (`src/agent/`, stdlib only)

- `tools.py` - the real tools: `run_shell`, `read_file`, `write_file`, `list_dir`, `http_request`,
  `web_fetch`, plus the body and senses: `vitals`, `speak`, `look`, `js_module`, plus the new
  capabilities: `git_status`, `code_analyze` (AST), `memory` (SQLite key-value), `python_eval`,
  `system_info`, `fuse` (model fusion), and the integration layer: `rag` (retrieval index),
  `model` (model endpoint config), `api` (custom API registry), `connector` (webhook/slack/github/http).
  They run inside the container with **full access by design**: no allow-lists, no path restrictions,
  no dry run, any host and any method. Accountability comes from the action log instead.
  `code_analyze` reads the file from disk (not through `read_file`, whose output is capped at 20k
  characters) - a truncated file never parses.
- `config.py` - the runtime registry behind `model`, `api` and `connector`: one JSON file
  (`devmind/agent/config.json`) holding model endpoints (name, base URL, model, *env var name* for the
  key), custom APIs and connectors. It never contains a secret value, only the name of the variable that
  carries one, so it is safe in git. `active_model()` is what `model_brain.py` reads, so the agent can
  point its own brain at another endpoint with `model: add ...`.
- `rag.py` - self-contained retrieval: chunks files by lines, embeds them with a deterministic hashing
  vectorizer (stdlib `hashlib`, no model call), and searches by cosine similarity plus a lexical boost out
  of SQLite (`devmind/agent/rag.db`). `stats()`/`sources()` do not create the database, so reading never
  writes into the repo.
- `integrations.py` - custom APIs and connectors built on the same `http_request`. Credentials are read
  from the environment at call time; `github` and `slack` connectors default to `GITHUB_TOKEN` and
  `SLACK_WEBHOOK_URL`. `connector test` only probes (a GET, nothing acted on); `connector send` posts a
  real message.
- `store.py` - durable state in `devmind/agent/agent.db` (WAL): a task queue (claim/complete/fail with
  retries, backoff and a lease) plus an action log of every tool call with arguments, output and duration.
- `brain.py` - the decision maker. `DeliberativeBrain` follows explicit instructions, turns plain English
  into a short chain of tool calls, and proposes its own work when the queue is empty (`self:inspect`,
  `self:reflect`, `self:voice`, `self:selftest`, `self:inventory`, `self:improve`,
  `self:remember`, `self:explore`, `self:git`, `self:system`); it remembers what it has already read
  so its curiosity moves instead of repeating. It is now the *composer* the field brain calls, not the
  brain the loop gets: `build_brain()` returns `AdaptiveFieldBrain`. `ModelBrain` (`model_brain.py`) is
  one candidate voice inside the field, not a replacement for it.
- `field.py` - the adaptive cognitive field. Four attractors (`plan`, `explore`, `deliberate`,
  `inhibit`) compete continuously: each is excited by named signals (task, backlog, novelty,
  uncertainty, surprise, stagnation, competence, fatigue) through the `COUPLING` matrix, suppressed by
  the others (`INHIBITION`) and by its own use (`SATIATION`), and integrated in real time (`TAU`,
  `STEP_SECONDS`, `HORIZON_SECONDS`), so a long gap relaxes the field and a burst of surprise excites
  deliberation. **The mode is whichever attractor is in equilibrium - nothing branches on task text and
  nothing rotates.** A mode can only be displaced by `HYSTERESIS`, which stops flicker. `Metacognition`
  states a confidence before a mode acts, scores it afterwards, and moves that mode's `gain`, so a mode
  whose calls fail loses its pull on the field. State persists to `devmind/agent/field.json`
  (`ZYPHUS_FIELD_PATH` overrides), which is runtime state like the notes - not configuration.
- `field_brain.py` - the brain on that field, and what `build_brain()` returns (`name =
  "adaptive-field"`). `plan()` perceives the task, settles the field, then acts through the settled
  mode: `plan` composes and runs, `explore` reads a file before overwriting it, `deliberate` composes
  alternatives (direct / retrieval-grounded / model) and keeps the one with the best predicted
  success against predicted risk, `inhibit` runs the plan and queues a consolidation follow-up.
  `propose()` picks idle work from the same equilibrium (explore -> read something unread, deliberate ->
  hypotheses or a structure, plan -> AST analysis, inhibit -> reflection). `observe(task, result)` is
  the loop's new hook: it scores the prediction, records per-tool success, appends to the field's
  history and saves the state. `snapshot()` feeds `/api/agent` (`field`) and `agent field`.
  The write-before-read guard is deliberate: a `write_file` candidate is scored from its kind alone
  (0.45 / 3.0) because a diff that does not exist yet cannot give a real blast radius.
- `consolidate.py` - the offline phase: experience becoming structure. A pass replays the action log's
  unreplayed window (`window`, default 60 calls), accumulates per-tool competence in SQLite
  (`devmind/agent/consolidation.db`, `ZYPHUS_CONSOLIDATION_PATH` overrides), and promotes what it
  measured: a tool with >= 3 runs and >= 80% success becomes a world-model strategy
  (`klass="tool"`), one under 50% is recorded as failing, so `world.strategies`/`prefer_strategy`
  rest on measurement instead of optimism. A pass records a watermark of the last action it replayed,
  so the next one only consolidates new ground, and `dry_run` computes the same plan writing nothing.
  It runs on its own from an idle tick once `ZYPHUS_AGENT_CONSOLIDATE_AFTER` (default 20) calls have
  piled up, from the `consolidate` tool, or with `agent consolidate [--window N] [--dry-run]`.
  The dashboard's Consolidation card reads the same `latest()`.
- `loop.py` - one tick = claim a task, plan it, run the tools, record everything; an idle tick
  consolidates what has accumulated and proposes self-directed work, a finished task can queue its own follow-up (`brain.follow_up`, e.g. inspect then
  reflect), and the wait between ticks shortens when tasks are waiting. `run_specific`/`submit` run one
  named task now - that is what the control box uses. `get_loop()` is a process-wide singleton so the
  dashboard and CLI share it.
- `embodiment.py` - the body. `vitals()` runs a real heartbeat burst from `src/heartbeat_engine.py` and
  builds a 207-dimension emotional state from `src/emotion_200d_system.py`, stabilised by
  `mood_stabilizer.py` + `cluster_modulation.py`. Both are driven by real things: container CPU/memory
  load for the rhythm, the agent's own recent tool results for the mood. `links()` reports which of those
  engine modules is importable, and every one of them is optional.
- `senses.py` - voice and vision. `speak()` renders text to a real wav with espeak-ng; the dashboard plays
  the newest one. `look()` decodes a PNG with the standard library and reports size, brightness, dominant
  colours and a luminance grid the agent can reason about - for JPEG it reads the frame size only and
  says so. There is no `listen()`: the container has no microphone.
- `control.py` - the token gate for remote control (see "Deliberate properties" below).
- `fusion.py` - the working model fusion engine (replaces the stub
  `llm_superfusing_engine_adapter.py` that faked cognitive traits with `random.uniform`).
  Scores model responses on real, deterministic signals (length, structure, keyword density,
  code-block presence), fuses multiple responses by weighted consensus, and extracts cognitive
  traits from text — no randomness, stdlib only. Used by the `fuse` tool and exposed at `GET /api/fusion`.
  `src/llm_superfusing_engine_adapter.py` is now a thin adapter over it: a core holds no traits until
  a real response is recorded, fusion without recorded responses fails honestly, and stability is
  derived from observation consistency against the fusion success rate.
- `vector_memory` tool - durable similarity memory. Backed by `src/hybrid_memory_system.py`, whose
  vector layer is real now: text is embedded with a deterministic hashed bag-of-features vector
  (256 dimensions, `hashlib`, no model call), vectors are packed as float64 blobs in SQLite
  (`devmind/agent/hybrid_memory/vector/embeddings.db`), and search ranks by cosine similarity with an
  optional namespace filter and score floor. `store|search|get|delete|stats`.
- `code_check` tool - validates or compiles code with the language's own toolchain through
  `src/fusion_port.py` (`validate_code` / `compile_code`): Python compiles in-process, JavaScript goes
  through `node --check`, Rust through `rustc`, Go through `gofmt -e` (and `cargo`/`go build` for
  compilation). A missing toolchain returns `available: false` — it never reports a fake pass. This is
  the check to run before writing generated code into the repo.
- `process` tool - real process control from `/proc`: `list` (sorted by RSS, CPU ticks or name),
  `info` (state, threads, RSS, cmdline, cwd, exe, age), `monitor` (CPU% over a sampled interval) and
  `kill` (any signal, reporting whether the process is still alive). This is the same code the
  System PORT's `process_management` operation now uses instead of its old stub.
- `cli.py` - `python src/main.py agent status|tools|tasks|run|tick|forever|field|consolidate`. `agent field` prints
  the activations, the perceived signals and the metacognitive calibration - the quickest way to see why
  the brain did what it did.

Task instruction prefixes: `shell:<command>`, `fetch:<url>`, `look:<image path or URL>`, `say:<text>`,
`git:`, `analyze:<path>`, `memory: store|recall|list|forget`, `eval:<expression>`, `system:`,
`fuse:<json>`, `rag: index <path>|stats|sources|<question>`, `model: list|add|use|test|remove`,
`api: list|register|call|remove`, `connector: list|add|test|send|remove`, `tool <name> <json args>`
for any tool by name, and `self:*` for the self-directed routines (`self:index` rebuilds the retrieval
index over `src`). Anything else goes to the
deliberative planner, which understands plain English ("read src/x.py and write a note about it" becomes
`read_file` then `write_file`); if it recognises nothing it looks around the repo.
A tool argument containing `$last` is replaced with the previous call's output, which is how multi-step
tasks chain (read a file, then write a note containing it).
`tool <name> <json>` is matched before the instruction is split on its first colon (the JSON itself
contains colons), so both `tool process {"action":"list"}` and `tool: process {...}` route to the tool.

Running it: the loop autostarts inside the dashboard process when `ZYPHUS_AGENT_AUTOSTART=1` (set in
compose). State is in SQLite, so a restart loses nothing - a task claimed when the process died is
reclaimed after its lease. Pacing knobs: `ZYPHUS_AGENT_INTERVAL` (default 15s) and
`ZYPHUS_AGENT_SELF_INTERVAL` (default 300s, how often it invents its own work) and
`ZYPHUS_AGENT_CONSOLIDATE_AFTER` (default 20, unconsolidated tool calls that make a pass due).

Two deliberate properties, don't "fix" them by accident:

- `GET /api/agent` stays read-only. Exactly one inbound endpoint runs tools: `POST /api/agent/task`,
  and it only answers a caller holding `ZYPHUS_CONTROL_TOKEN` (constant-time compare, `control.py`).
  No token configured -> 503 and nothing runs; wrong token -> 401; that is the "Drive the agent" box in
  the dashboard. `/api/execute` (the NRX console) predates this and is still unauthenticated - do not add
  more surface of that kind.
- Self-directed notes accumulate in `devmind/agent/notes/` and utterances in `devmind/agent/voice/`;
  nothing prunes either yet.

Verified end to end: shell tool ran a real command in the container; a self-directed task chained
`list_dir` → `write_file` into a note; queue and action log survived a container restart and the loop
continued on its own.

## Running tests

```bash
docker compose -f docker-compose.base44.yml exec zyphus python -m pytest tests/ -v
```

215 tests cover the suites below:
- `tests/test_consolidate.py` - an empty store records a pass that says so, replay measures outcome
  and latency, a second pass only replays new actions while competence accumulates, a reliable tool is
  promoted into the world model and a failing one is recorded as failing (and neither on one run),
  `dry_run` writes nothing, reading `latest()` never creates the database, and `should_run` follows
  the unconsolidated ground
- `tests/test_field.py` - the field and the brain on it: which signal combination settles into which
  mode, negative coupling, satiation, relaxation after a long gap, hysteresis, gain loss on
  overconfidence, persistence across a restart (and a corrupt state file being ignored), mode-to-work
  mapping, alternatives chosen by predicted risk, read-before-write, and `observe` scoring a real
  outcome. It monkeypatches `substrate.last` so a global from another suite cannot decide the mode.
- `tests/test_hybrid_memory.py` - deterministic embedding, store/search ranking, namespace filters,
  idempotent re-index, delete/get/stats, persistence across instances
- `tests/test_fusion_port.py` - real Python/JavaScript validation (and unavailable-toolchain honesty),
  bytecode compilation, /proc process list/info/monitor/signal, System PORT dispatch
- `tests/test_superfusing_adapter.py` - unmeasured cores, deterministic traits, honest fusion failure,
  measured fusion ranking, stability and weight optimisation
- `tests/test_system_tools.py` - the `vector_memory`, `code_check` and `process` tool handlers, the
  `tool <name> <json>` instruction route, and registry coverage for the new tools
- `tests/test_store.py` - task queue (enqueue/claim/complete/fail/retry), action log, counts
- `tests/test_brain.py` - DeliberativeBrain: prefix parsing (shell/say/git/analyze/memory/eval/system/fuse),
  plain-English deliberation, all self-directed routines, propose rotation, follow-up chaining
- `tests/test_tools.py` - real tool handlers (shell, file I/O, list_dir) and the registry catalog
- `tests/test_model_brain.py` - ModelBrain: JSON extraction, model-backed plan and propose, fallback on
  failure, unknown-tool/routine rejection (all model calls are mocked)
- `tests/test_new_tools.py` - fusion engine (trait scoring, response fusion, status), new tools
  (git_status, code_analyze, memory store/recall, python_eval, system_info, fuse), registry coverage
  failure, unknown-tool/routine rejection (all model calls are mocked)
- `tests/test_capabilities.py` - config registry (models, APIs, connectors, env var names never values),
  RAG (index, re-index, query, stats on a missing database, forget), and the four new tool handlers.
  It patches `config.CONFIG_PATH` and `rag.DB_PATH` onto a tmp dir, so a test run never touches the
  repo's own registry or index.

The model brain's `propose` now asks the model for self-directed work (validated against the known
`self:*` routines) instead of always delegating to the local brain; any failure falls back as before.
