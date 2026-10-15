"""
Real tools the agent can call.

These run inside the engine's own container with full access on purpose: no
allow-lists, no path restrictions, no dry-run mode. A shell there is a shell.
What keeps it accountable is the action log - every call the loop makes is
persisted with its arguments, output and duration, so what the agent did is
always inspectable after the fact.
"""

import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAX_OUTPUT = 20000


def _truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [truncated, {len(text) - limit} more characters]"


def _resolve(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


@dataclass
class ToolResult:
    ok: bool
    output: str = ""
    error: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "output": self.output, "error": self.error, "meta": self.meta}


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, str]
    handler: Callable[..., ToolResult]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return sorted(self._tools)

    def catalog(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in sorted(self._tools.values(), key=lambda t: t.name)
        ]

    def run(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(False, error=f"unknown tool: {name}")
        try:
            return tool.handler(**(arguments or {}))
        except TypeError as exc:
            return ToolResult(False, error=f"bad arguments for {name}: {exc}")
        except Exception as exc:
            return ToolResult(False, error=f"{type(exc).__name__}: {exc}")


# --- handlers ----------------------------------------------------------------


def run_shell(command: str, timeout: float = 120, cwd: Optional[str] = None) -> ToolResult:
    workdir = _resolve(cwd) if cwd else REPO_ROOT
    try:
        proc = subprocess.run(command, shell=True, cwd=workdir, capture_output=True,
                              text=True, timeout=float(timeout))
    except subprocess.TimeoutExpired:
        return ToolResult(False, error=f"command timed out after {timeout}s")
    except Exception as exc:
        return ToolResult(False, error=f"{type(exc).__name__}: {exc}")
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return ToolResult(
        proc.returncode == 0,
        output=_truncate(output),
        error="" if proc.returncode == 0 else f"exit code {proc.returncode}",
        meta={"returncode": proc.returncode, "cwd": workdir},
    )


def read_file(path: str, max_bytes: int = 200000) -> ToolResult:
    full = _resolve(path)
    if not os.path.isfile(full):
        return ToolResult(False, error=f"not a file: {full}")
    size = os.path.getsize(full)
    with open(full, "rb") as handle:
        raw = handle.read(int(max_bytes))
    text = raw.decode("utf-8", errors="replace")
    if size > len(raw):
        text += f"\n… [truncated, file is {size} bytes]"
    return ToolResult(True, output=_truncate(text), meta={"path": full, "bytes": size})


def write_file(path: str, content: str) -> ToolResult:
    full = _resolve(path)
    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(content)
    return ToolResult(True, output=f"wrote {len(content)} characters to {full}",
                      meta={"path": full, "bytes": len(content.encode("utf-8"))})


def list_dir(path: str = ".") -> ToolResult:
    full = _resolve(path)
    if not os.path.isdir(full):
        return ToolResult(False, error=f"not a directory: {full}")
    lines = []
    for name in sorted(os.listdir(full)):
        entry = os.path.join(full, name)
        if os.path.isdir(entry):
            lines.append(f"dir  {name}/")
        else:
            lines.append(f"file {name}  ({os.path.getsize(entry)} B)")
    return ToolResult(True, output=_truncate("\n".join(lines)) or "(empty directory)",
                      meta={"path": full, "entries": len(lines)})


def http_request(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
                 body: Optional[str] = None, timeout: float = 30) -> ToolResult:
    data = body.encode("utf-8") if body else None
    request = urllib.request.Request(url, data=data, method=method.upper(),
                                     headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=float(timeout)) as response:
            payload = response.read(MAX_OUTPUT + 1).decode("utf-8", errors="replace")
            return ToolResult(True, output=_truncate(payload),
                              meta={"status": response.status, "url": response.url})
    except urllib.error.HTTPError as exc:
        payload = exc.read(MAX_OUTPUT + 1).decode("utf-8", errors="replace")
        return ToolResult(False, output=_truncate(payload), error=f"HTTP {exc.code}",
                          meta={"status": exc.code, "url": url})
    except Exception as exc:
        return ToolResult(False, error=f"{type(exc).__name__}: {exc}", meta={"url": url})


class _TextExtractor(HTMLParser):
    """Pull visible text out of a page, skipping script and style blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            chunk = " ".join(data.split())
            if chunk:
                self.parts.append(chunk)


def web_fetch(url: str, timeout: float = 30) -> ToolResult:
    """Fetch a page and return its readable text (no HTML, no scripts)."""
    fetched = http_request(url, timeout=timeout)
    if not fetched.ok and "HTTP" not in fetched.error:
        return fetched
    parser = _TextExtractor()
    parser.feed(fetched.output)
    text = "\n".join(parser.parts)
    return ToolResult(fetched.ok, output=_truncate(text) or "(no readable text)",
                      error=fetched.error, meta=fetched.meta)


def js_module(name: str = "") -> ToolResult:
    """Load one of the engine's own ESM modules with node and report its shape."""
    modules_root = os.path.join(REPO_ROOT, "src", "modules")
    runner = os.path.join(modules_root, "run_module.mjs")
    if not os.path.isfile(runner):
        return ToolResult(False, error=f"module runner missing: {runner}")

    if not name:
        found = []
        for root, _dirs, files in os.walk(modules_root):
            for entry in sorted(files):
                if entry.endswith(".js"):
                    found.append(os.path.relpath(os.path.join(root, entry), modules_root))
        return ToolResult(True, output="\n".join(found) or "(no modules found)",
                          meta={"modules": found})

    target = None
    for root, _dirs, files in os.walk(modules_root):
        for entry in sorted(files):
            if entry == name or entry == f"{name}.js" or entry.startswith(name):
                target = os.path.join(root, entry)
                break
        if target:
            break
    if target is None:
        return ToolResult(False, error=f"no module matching {name!r} under src/modules")

    try:
        proc = subprocess.run(["node", runner, target], cwd=REPO_ROOT, capture_output=True,
                              text=True, timeout=60)
    except Exception as exc:
        return ToolResult(False, error=f"{type(exc).__name__}: {exc}")
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return ToolResult(proc.returncode == 0, output=_truncate(output),
                      error="" if proc.returncode == 0 else f"node exited {proc.returncode}",
                      meta={"module": os.path.relpath(target, REPO_ROOT)})


def tool_vitals() -> ToolResult:
    """The body reading, as one spoken-style sentence plus the full data."""
    from src.agent import embodiment

    reading = embodiment.vitals()
    return ToolResult(True, output=embodiment.summary(reading), meta=reading)


# --- git ---------------------------------------------------------------------

def git_status() -> ToolResult:
    """Git branch, status summary and last 5 commits."""
    branch = run_shell("git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'no-git'")
    log = run_shell("git log --oneline -5 2>/dev/null || true")
    status = run_shell("git status --short 2>/dev/null | head -30")
    out = f"branch: {branch.output}\n\ncommits:\n{log.output}\n\nstatus:\n{status.output or '(clean)'}"
    return ToolResult(True, output=_truncate(out))


# --- code analysis (stdlib ast) ----------------------------------------------

def code_analyze(path: str) -> ToolResult:
    """AST-based analysis of a Python file: functions, classes, imports, complexity."""
    import ast as _ast

    full = _resolve(path)
    if not os.path.isfile(full):
        return ToolResult(False, error=f"not a file: {full}")
    source = read_file(path).output
    try:
        tree = _ast.parse(source)
    except SyntaxError as exc:
        return ToolResult(False, error=f"cannot parse: {exc}")

    funcs, classes, imports = [], [], []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            funcs.append(f"  def {node.name}({', '.join(args)})  [line {node.lineno}]")
        elif isinstance(node, _ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, _ast.FunctionDef)]
            classes.append(f"  class {node.name}  [line {node.lineno}, {len(methods)} methods]")
        elif isinstance(node, (_ast.Import, _ast.ImportFrom)):
            if isinstance(node, _ast.ImportFrom):
                imports.append(f"  from {node.module or '.'} import ...")
            else:
                for alias in node.names:
                    imports.append(f"  import {alias.name}")

    # McCabe-ish complexity: count branching nodes
    branches = sum(1 for n in _ast.walk(tree)
                   if isinstance(n, (_ast.If, _ast.For, _ast.While, _ast.ExceptHandler,
                                     _ast.BoolOp)))
    lines = source.count("\n") + 1

    out = (f"file: {path}  ({lines} lines, complexity {branches})\n\n"
           f"imports ({len(imports)}):\n" + "\n".join(imports) + "\n\n"
           f"classes ({len(classes)}):\n" + "\n".join(classes) + "\n\n"
           f"functions ({len(funcs)}):\n" + "\n".join(funcs))
    return ToolResult(True, output=_truncate(out),
                      meta={"lines": lines, "branches": branches,
                            "functions": len(funcs), "classes": len(classes)})


# --- memory (key-value SQLite) -----------------------------------------------

MEMORY_DB = os.path.join(REPO_ROOT, "devmind", "agent", "memory.db")


def _memory_db():
    import sqlite3
    os.makedirs(os.path.dirname(MEMORY_DB), exist_ok=True)
    conn = sqlite3.connect(MEMORY_DB, timeout=10)
    conn.execute("CREATE TABLE IF NOT EXISTS memory "
                 "(key TEXT PRIMARY KEY, value TEXT, tag TEXT, created_at TEXT)")
    conn.commit()
    return conn


def memory(action: str = "list", key: str = "", value: str = "", tag: str = "") -> ToolResult:
    """Persistent key-value memory: store, recall, list, or forget."""
    import time as _time
    conn = _memory_db()
    action = (action or "list").strip().lower()

    if action in ("store", "set", "save"):
        if not key:
            return ToolResult(False, error="store requires a key")
        conn.execute("INSERT OR REPLACE INTO memory (key, value, tag, created_at) VALUES (?,?,?,?)",
                     (key, value, tag, _time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return ToolResult(True, output=f"remembered: {key}")

    if action in ("recall", "get", "read"):
        if not key:
            return ToolResult(False, error="recall requires a key")
        row = conn.execute("SELECT value, tag, created_at FROM memory WHERE key=?", (key,)).fetchone()
        if not row:
            return ToolResult(False, error=f"no memory for key: {key}")
        return ToolResult(True, output=row[0], meta={"key": key, "tag": row[1], "created_at": row[2]})

    if action in ("forget", "delete", "del"):
        if not key:
            return ToolResult(False, error="forget requires a key")
        conn.execute("DELETE FROM memory WHERE key=?", (key,))
        conn.commit()
        return ToolResult(True, output=f"forgot: {key}")

    # default: list
    rows = conn.execute("SELECT key, tag, created_at FROM memory ORDER BY created_at DESC LIMIT 50").fetchall()
    if not rows:
        return ToolResult(True, output="(memory is empty)")
    out = "\n".join(f"  {r[0]:30s}  [{r[1] or '-'}]  {r[2]}" for r in rows)
    return ToolResult(True, output=f"memory ({len(rows)} entries):\n{out}",
                      meta={"count": len(rows)})


# --- python eval (safe expression) -------------------------------------------

def python_eval(expression: str) -> ToolResult:
    """Evaluate a Python expression and return the result."""
    expression = (expression or "").strip()
    if not expression:
        return ToolResult(False, error="no expression")
    try:
        result = eval(expression, {"__builtins__": __builtins__}, {})
        return ToolResult(True, output=_truncate(str(result)),
                          meta={"type": type(result).__name__})
    except Exception as exc:
        return ToolResult(False, error=f"{type(exc).__name__}: {exc}")


# --- system info -------------------------------------------------------------

def system_info() -> ToolResult:
    """OS, CPU, memory and disk information for the container."""
    import platform
    info = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    try:
        load = os.getloadavg()
        info["load_avg"] = f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
    except (OSError, AttributeError):
        pass
    # memory from /proc/meminfo (Linux)
    try:
        with open("/proc/meminfo") as f:
            memlines = {}
            for line in f:
                k, _, v = line.partition(":")
                memlines[k.strip()] = v.strip()
        info["memory_total"] = memlines.get("MemTotal", "?")
        info["memory_free"] = memlines.get("MemFree", "?")
        info["memory_available"] = memlines.get("MemAvailable", "?")
    except Exception:
        pass
    # disk
    try:
        st = os.statvfs("/")
        gb = 1024 ** 3
        info["disk_total_gb"] = round(st.f_blocks * st.f_frsize / gb, 1)
        info["disk_free_gb"] = round(st.f_bavail * st.f_frsize / gb, 1)
    except Exception:
        pass
    out = "\n".join(f"  {k}: {v}" for k, v in info.items())
    return ToolResult(True, output=f"system info:\n{out}", meta=info)


# --- model fusion ------------------------------------------------------------

def fuse_tool(responses: str = "") -> ToolResult:
    """Fuse multiple model responses. Pass a JSON array of {source, response} objects."""
    from src.agent.fusion import FusionEngine

    if not responses:
        engine = FusionEngine()
        return ToolResult(True, output="fusion engine ready. Pass a JSON array of "
                                        '{"source": "...", "response": "..."} objects.',
                          meta=engine.status())

    try:
        data = json.loads(responses)
    except ValueError as exc:
        return ToolResult(False, error=f"invalid JSON: {exc}")

    if not isinstance(data, list):
        return ToolResult(False, error="expected a JSON array of response objects")

    engine = FusionEngine()
    result = engine.fuse(data)
    if "error" in result:
        return ToolResult(False, error=result["error"])
    out = (f"winner: {result['winner']} (weight {result['winner_weight']})\n"
           f"algorithm: {result['algorithm']}\n"
           f"blended traits: {json.dumps(result['blended_traits'])}\n\n"
           f"fused output:\n{result['fused'][:2000]}")
    return ToolResult(True, output=_truncate(out),
                      meta={"cores": len(result["cores"]), "fusions": engine.fusions})


def build_registry() -> ToolRegistry:
    from src.agent import senses

    registry = ToolRegistry()
    registry.register(Tool(
        "run_shell", "Run a shell command inside the engine's container.",
        {"command": "str", "timeout": "float seconds (optional, default 120)",
         "cwd": "str path (optional, defaults to the repo root)"}, run_shell))
    registry.register(Tool(
        "read_file", "Read a text file.",
        {"path": "str", "max_bytes": "int (optional, default 200000)"}, read_file))
    registry.register(Tool(
        "write_file", "Create or overwrite a file (parent directories are created).",
        {"path": "str", "content": "str"}, write_file))
    registry.register(Tool(
        "list_dir", "List a directory with entry types and sizes.",
        {"path": "str (optional, defaults to the repo root)"}, list_dir))
    registry.register(Tool(
        "http_request", "Make an HTTP request and return the response body.",
        {"url": "str", "method": "str (optional)", "headers": "object (optional)",
         "body": "str (optional)", "timeout": "float seconds (optional)"}, http_request))
    registry.register(Tool(
        "web_fetch", "Fetch a web page and return its readable text.",
        {"url": "str", "timeout": "float seconds (optional)"}, web_fetch))
    registry.register(Tool(
        "vitals", "Read the agent's body: a real heartbeat burst (rhythm, bpm, energy, stress) "
                  "plus its emotional state.", {}, tool_vitals))
    registry.register(Tool(
        "speak", "Say text out loud - renders a wav with the speech engine in the image; "
                 "the dashboard plays the newest one.",
        {"text": "str", "speed": "int words per minute (optional, default 165)",
         "voice": "str voice name (optional)"}, senses.speak))
    registry.register(Tool(
        "look", "See an image (a path in the container or an http(s) URL): format, size, "
                "brightness, dominant colours and a luminance grid.",
        {"source": "str path or URL"}, senses.look))
    registry.register(Tool(
        "js_module", "List the engine's JavaScript modules, or load one with node and report "
                     "the classes it exports and their methods.",
        {"name": "str module name (optional - omit to list them)"}, js_module))
    registry.register(Tool(
        "git_status", "Show the current git branch, recent commits and working-tree status.",
        {}, git_status))
    registry.register(Tool(
        "code_analyze", "AST-analyze a Python file: functions, classes, imports, complexity.",
        {"path": "str path to a .py file"}, code_analyze))
    registry.register(Tool(
        "memory", "Persistent key-value memory: store, recall, list, or forget entries.",
        {"action": "str: store|recall|list|forget (optional, default list)",
         "key": "str (required for store/recall/forget)",
         "value": "str (required for store)",
         "tag": "str optional label"}, memory))
    registry.register(Tool(
        "python_eval", "Evaluate a Python expression and return the result.",
        {"expression": "str Python expression"}, python_eval))
    registry.register(Tool(
        "system_info", "OS, CPU, memory and disk information for the container.",
        {}, system_info))
    registry.register(Tool(
        "fuse", "Fuse multiple model responses into one. Pass a JSON array of "
                '{"source": "...", "response": "..."} objects, or omit for status.',
        {"responses": "str JSON array (optional)"}, fuse_tool))
    return registry
