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
MODULES_ROOT = os.path.join(REPO_ROOT, "src", "modules")
CLI = os.path.join(REPO_ROOT, "src", "main.py")

PORT = int(os.environ.get("ZYPHUS_WEB_PORT", "3000"))
CLI_TIMEOUT = int(os.environ.get("ZYPHUS_CLI_TIMEOUT", "300"))
IS_PREVIEW = os.environ.get("BASE44_PREVIEW_MODE") == "1"

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
            else:
                self._send_json(404, {"error": "Not found"})
        except subprocess.TimeoutExpired:
            self._send_json(504, {"error": "The CLI took too long to respond."})
        except Exception as exc:  # keep the dashboard honest instead of blank
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/execute":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            self._send_json(200, execute_payload(str(body.get("code", ""))))
        except subprocess.TimeoutExpired:
            self._send_json(504, {"success": False, "error": "Execution timed out."})
        except Exception as exc:
            self._send_json(400, {"success": False, "error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt, *args):
        sys.stderr.write("dashboard: " + fmt % args + "\n")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Zyphus dashboard on http://0.0.0.0:{PORT} (repo: {REPO_ROOT})", flush=True)
    server.serve_forever()
