#!/usr/bin/env python3
"""
Zyphus CLI Engine - browser dashboard.

A small, dependency-free front end that drives the existing `zyphus` CLI
(src/main.py) so the engine can be used from the preview. It adds no engine
logic of its own: every action shells out to the CLI and returns its output.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_ROOT = os.path.dirname(os.path.abspath(__file__))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.agent.loop import get_loop
    from src.agent import control
    AGENT_IMPORT_ERROR = ""
except Exception as _exc:  # the dashboard must still serve if the agent layer breaks
    get_loop = None
    control = None
    AGENT_IMPORT_ERROR = f"{type(_exc).__name__}: {_exc}"
MODULES_ROOT = os.path.join(REPO_ROOT, "src", "modules")
VOICE_DIR = os.path.join(REPO_ROOT, "devmind", "agent", "voice")
VOICE_FILE = re.compile(r"^voice-\d{8}-\d{6}\.wav$")
CLI = os.path.join(REPO_ROOT, "src", "main.py")

PORT = int(os.environ.get("ZYPHUS_WEB_PORT", "3000"))
CLI_TIMEOUT = int(os.environ.get("ZYPHUS_CLI_TIMEOUT", "300"))
IS_PREVIEW = os.environ.get("BASE44_PREVIEW_MODE") == "1"

# Browsers ask for /favicon.ico on every load; without a route the 404 surfaces
# as a failed request in the preview. Served inline so no binary asset is needed.
FAVICON = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#06080d"/>
<path d="M20 21h24L20 43h24" fill="none" stroke="#2dd4bf" stroke-width="7"
 stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

COMPONENT_LINE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*:\s*(OK|FAIL)\s*$", re.MULTILINE)


def run_cli(*args):
    """Run a CLI command in a subprocess and capture stdout + stderr."""
    proc = subprocess.run(
        [sys.executable, CLI, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def status_payload():
    """`zyphus status` rendered as JSON."""
    code, output = run_cli("status")

    overall = "UNKNOWN"
    match = re.search(r"Overall Health:\s*(HEALTHY|UNHEALTHY)", output)
    if match:
        overall = match.group(1)

    version = re.search(r"Version:\s*(\S+)", output)
    timestamp = re.search(r"Timestamp:\s*(\S+)", output)

    return {
        "exit_code": code,
        "overall": overall,
        "components": {name: flag == "OK" for name, flag in COMPONENT_LINE.findall(output)},
        "version": version.group(1) if version else None,
        "timestamp": timestamp.group(1) if timestamp else None,
        "log": output.strip(),
    }


def execute_payload(code):
    """`zyphus execute <nrx code>` rendered as JSON."""
    if not code.strip():
        return {"success": False, "log": "", "error": "No NRX code supplied."}
    try:
        exit_code, output = run_cli("execute", code)
    except subprocess.TimeoutExpired:
        return {"success": False, "log": "", "error": "Execution timed out."}
    return {
        "success": exit_code == 0 and "Execution Successful:" in output,
        "log": output.strip(),
    }


def modules_payload():
    """The JavaScript modules the engine's bridge can address."""
    modules = []
    if os.path.isdir(MODULES_ROOT):
        for name in sorted(os.listdir(MODULES_ROOT)):
            path = os.path.join(MODULES_ROOT, name)
            if os.path.isdir(path):
                modules.append({
                    "name": name,
                    "files": sorted(f for f in os.listdir(path) if f.endswith(".js")),
                })
    return {"modules": modules}


def agent_payload():
    """Loop state, queue counts, tool catalog, body, voice and recent calls (read-only)."""
    if get_loop is None:
        return {"available": False, "error": AGENT_IMPORT_ERROR}
    payload = get_loop().status()
    payload["available"] = True
    payload["control"] = {"configured": bool(control and control.configured())}
    return payload


def task_payload(body, header_token=None):
    """Token-gated remote control: queue the operator's instructions and run them now.

    The preview URL is public, so this is the only inbound endpoint that runs
    tools, and it answers only a caller holding ZYPHUS_CONTROL_TOKEN. With no
    token configured it refuses outright - the loop keeps running either way.
    """
    if get_loop is None:
        return 503, {"error": f"Agent layer not loaded: {AGENT_IMPORT_ERROR}"}
    if control is None or not control.configured():
        return 503, {"error": "Remote control is off: no ZYPHUS_CONTROL_TOKEN is configured."}
    if not control.authorized(header_token or body.get("token") or ""):
        return 401, {"error": "Invalid or missing control token."}

    instructions = str(body.get("instructions", "")).strip()
    if not instructions:
        return 400, {"error": "No instruction supplied."}
    result = get_loop().submit(instructions, title=body.get("title") or None)
    return 200, result


def health_payload():
    """Cheap liveness probe: the engine source must be importable."""
    probe = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import src.nrx_interpreter"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "status": "ok" if probe.returncode == 0 else "degraded",
        "engine_importable": probe.returncode == 0,
        "node_available": shutil.which("node") is not None,
        "preview_mode": IS_PREVIEW,
    }


def memory_payload():
    """List the agent's persistent key-value memory (read-only)."""
    import sqlite3
    mem_db = os.path.join(REPO_ROOT, "devmind", "agent", "memory.db")
    if not os.path.isfile(mem_db):
        return {"entries": []}
    try:
        conn = sqlite3.connect(mem_db, timeout=5)
        rows = conn.execute(
            "SELECT key, value, tag, created_at FROM memory ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        conn.close()
        return {"entries": [
            {"key": r[0], "value": r[1][:500], "tag": r[2], "created_at": r[3]}
            for r in rows
        ]}
    except Exception as exc:
        return {"entries": [], "error": str(exc)}


def fusion_payload():
    """Status of the model fusion engine."""
    try:
        from src.agent.fusion import FusionEngine
        return FusionEngine().status()
    except Exception as exc:
        return {"error": str(exc)}


def capabilities_payload():
    """What the agent can reach: model endpoints, custom APIs, connectors, retrieval index.

    Read-only, and it exposes only configuration - never a credential value, only
    whether the environment variable an entry names is present.
    """
    try:
        from src.agent import config, integrations, rag
    except Exception as exc:  # a broken module must not blank the tab
        return {"error": f"{type(exc).__name__}: {exc}"}
    active = config.active_model() or {}
    return {
        "models": integrations.models(),
        "active_model": active.get("name") or None,
        "apis": integrations.api_names(),
        "connectors": integrations.connector_names(),
        "rag": rag.stats(),
        "sources": rag.sources()[:60],
        "registry": config.CONFIG_PATH,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ZyphusDashboard"

    def _send(self, status, body, content_type, cache=False):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, payload):
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path in ("/favicon.ico", "/favicon.svg"):
            self._send(200, FAVICON, "image/svg+xml", cache=True)
            return

        if path in ("/", "/index.html"):
            with open(os.path.join(WEB_ROOT, "index.html"), "rb") as handle:
                self._send(200, handle.read(), "text/html; charset=utf-8")
            return

        try:
            if path == "/api/health":
                payload = health_payload()
                self._send_json(200 if payload["engine_importable"] else 503, payload)
            elif path == "/api/status":
                self._send_json(200, status_payload())
            elif path == "/api/modules":
                self._send_json(200, modules_payload())
            elif path == "/api/agent":
                self._send_json(200, agent_payload())
            elif path == "/api/agent/memory":
                self._send_json(200, memory_payload())
            elif path == "/api/fusion":
                self._send_json(200, fusion_payload())
            elif path == "/api/capabilities":
                self._send_json(200, capabilities_payload())
            elif path.startswith("/api/agent/voice/"):
                self._send_voice(path.rsplit("/", 1)[-1])
            else:
                self._send_json(404, {"error": "Not found"})
        except subprocess.TimeoutExpired:
            self._send_json(504, {"error": "The CLI took too long to respond."})
        except Exception as exc:  # keep the dashboard honest instead of blank
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def _send_voice(self, name):
        """Serve one of the agent's utterances to the browser player."""
        full = os.path.join(VOICE_DIR, name)
        if not VOICE_FILE.match(name) or not os.path.isfile(full):
            self._send_json(404, {"error": "No such utterance."})
            return
        with open(full, "rb") as handle:
            self._send(200, handle.read(), "audio/wav", cache=True)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path not in ("/api/execute", "/api/agent/task"):
            self._send_json(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/execute":
                self._send_json(200, execute_payload(str(body.get("code", ""))))
            else:
                status, payload = task_payload(body, self.headers.get("X-Zyphus-Token"))
                self._send_json(status, payload)
        except subprocess.TimeoutExpired:
            self._send_json(504, {"success": False, "error": "Execution timed out."})
        except Exception as exc:
            self._send_json(400, {"success": False, "error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt, *args):
        sys.stderr.write("dashboard: " + fmt % args + "\n")


if __name__ == "__main__":
    if get_loop is not None and os.environ.get("ZYPHUS_AGENT_AUTOSTART") == "1":
        loop = get_loop()
        loop.start_thread()
        print(f"agent loop started (state: {loop.store.path})", flush=True)
    elif AGENT_IMPORT_ERROR:
        print(f"agent layer not loaded: {AGENT_IMPORT_ERROR}", flush=True)

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Zyphus dashboard on http://0.0.0.0:{PORT} (repo: {REPO_ROOT})", flush=True)
    server.serve_forever()
