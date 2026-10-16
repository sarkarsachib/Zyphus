"""
Deciding what to do next.

`DeliberativeBrain` is the local decision maker: it follows an explicit
instruction when a task carries one, turns plain English into a short chain of
real tool calls, and when the queue is empty it proposes its own work - reading
its own source, reflecting on its notes, checking the engine, or reporting its
body out loud. It keeps a memory of what it has already looked at, so its
curiosity moves instead of repeating itself, and it can chain a follow-up task
after a finished one.

`build_brain()` returns this brain by default, and a model-backed brain
(`src/agent/model_brain.py`) when an API key for one is present - the same loop,
the same tools, a stronger planner. The loop only needs `plan(task)`,
`propose(context)` and the optional `follow_up(task, outcome)`.
"""

import json
import os
import re
import shlex
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agent.tools import REPO_ROOT

MODULE_POOL = [
    "src/agent/brain.py",
    "src/agent/loop.py",
    "src/agent/tools.py",
    "src/agent/store.py",
    "src/agent/senses.py",
    "src/agent/embodiment.py",
    "src/nrx_interpreter.py",
    "src/custom_kernel.py",
    "src/custom_terminal.py",
    "src/heartbeat_engine.py",
    "src/js_module_bridge_fixed.py",
]

FILE_HINT = re.compile(r"[\w./-]+\.(?:py|js|mjs|md|json|html|txt|ya?ml|png|jpe?g|wav|db)\b")
PATH_HINT = re.compile(r"(?<![\w./-])[\w.-]+/[\w./-]+")
MODULE_HINT = re.compile(r"\b(hyper-core|godmode-executor|hive-brain|neural-editor|smart-terminal|"
                         r"quantum-task-engine|digital-soul-fabric|self-aware-kernel|ai-genesis|"
                         r"global-integrator|future-engine|omniconscious-core|intelligent-database|"
                         r"universal-law-engine|reality-overseer|recursive-agent-factory|safety-core|"
                         r"causal-rewrite-engine|dimensional-awareness|uncreate|quantum-observer)\b")


@dataclass
class ToolCall:
    tool: str
    arguments: Dict[str, Any] = field(default_factory=dict)


class DeliberativeBrain:
    """Turns a task into a plan of real tool calls, and invents its own work."""

    name = "deliberative"

    def __init__(self, notes_dir: str = "devmind/agent/notes"):
        self.notes_dir = notes_dir
        self._rotation = 0
        self._looked_at: set = set()

    # --- following a task ----------------------------------------------------

    def plan(self, task: Dict[str, Any]) -> List[ToolCall]:
        instructions = (task.get("instructions") or "").strip()
        prefix, _, rest = instructions.partition(":")
        prefix = prefix.strip().lower()
        rest = rest.strip()

        if prefix == "tool":
            return self._explicit_tool(instructions)
        if prefix == "shell":
            return [ToolCall("run_shell", {"command": rest})]
        if prefix in ("fetch", "read_url"):
            return [ToolCall("web_fetch", {"url": rest})]
        if prefix == "look":
            return [ToolCall("look", {"source": rest})]
        if prefix == "say":
            return [ToolCall("speak", {"text": rest})]
        if prefix in ("git", "git_status"):
            return [ToolCall("git_status", {})]
        if prefix in ("analyze", "ast"):
            return [ToolCall("code_analyze", {"path": rest})]
        if prefix in ("remember", "memory"):
            return self._memory_instruction(rest)
        if prefix in ("eval", "python", "py"):
            return [ToolCall("python_eval", {"expression": rest})]
        if prefix in ("sysinfo", "system"):
            return [ToolCall("system_info", {})]
        if prefix in ("fuse", "fusion"):
            return [ToolCall("fuse", {"responses": rest})]
        if prefix in ("rag", "index", "retrieve"):
            return self._rag_instruction(rest)
        if prefix in ("model", "models", "llm"):
            return self._model_instruction(rest)
        if prefix in ("api", "apis", "endpoint"):
            return self._api_instruction(rest)
        if prefix in ("connector", "connectors", "connect", "hook"):
            return self._connector_instruction(rest)
        if prefix == "self":
            return self._self_directed(rest)
        return self._deliberate(instructions)

    def _memory_instruction(self, rest: str) -> List[ToolCall]:
        """Parse 'memory: store key=value' or 'memory: recall key' or 'memory: list'."""
        rest = (rest or "").strip()
        if not rest or rest == "list":
            return [ToolCall("memory", {"action": "list"})]
        low = rest.lower()
        if low.startswith("store ") or low.startswith("set "):
            body = rest.split(" ", 1)[1]
            key, _, val = body.partition("=")
            return [ToolCall("memory", {"action": "store", "key": key.strip(), "value": val.strip()})]
        if low.startswith("recall ") or low.startswith("get "):
            return [ToolCall("memory", {"action": "recall", "key": rest.split(" ", 1)[1].strip()})]
        if low.startswith("forget ") or low.startswith("delete "):
            return [ToolCall("memory", {"action": "forget", "key": rest.split(" ", 1)[1].strip()})]
        return [ToolCall("memory", {"action": "list"})]

    def _rag_instruction(self, rest: str) -> List[ToolCall]:
        """Parse 'rag: index src', 'rag: stats', 'rag: sources', 'rag: <question>'."""
        rest = (rest or "").strip()
        low = rest.lower()
        if not rest or low in ("stats", "status"):
            return [ToolCall("rag", {"action": "stats"})]
        if low in ("sources", "list", "files"):
            return [ToolCall("rag", {"action": "sources"})]
        if low.startswith("forget ") or low.startswith("clear ") or low.startswith("delete "):
            return [ToolCall("rag", {"action": "forget", "source": rest.split(" ", 1)[1].strip()})]
        if low.startswith("index") or low.startswith("ingest"):
            target = rest.split(" ", 1)[1].strip() if " " in rest else "."
            tag = ""
            if " into " in target:
                target, _, tag = target.partition(" into ")
            return [ToolCall("rag", {"action": "index", "path": target.strip() or ".",
                                     "source": tag.strip()})]
        if low.startswith("query ") or low.startswith("search ") or low.startswith("find "):
            return [ToolCall("rag", {"action": "query", "text": rest.split(" ", 1)[1].strip()})]
        return [ToolCall("rag", {"action": "query", "text": rest})]

    def _model_instruction(self, rest: str) -> List[ToolCall]:
        """Parse 'model: list', 'model: add <name> <base_url> <model> [key_env]', 'model: use <name>'."""
        rest = (rest or "").strip()
        verb, _, arg = rest.partition(" ")
        verb, arg = verb.lower(), arg.strip()
        if verb == "add" or verb == "set" or verb == "configure":
            parts = arg.split()
            if not parts:
                return [ToolCall("model", {"action": "list"})]
            return [ToolCall("model", {
                "action": "add",
                "name": parts[0],
                "base_url": parts[1] if len(parts) > 1 else "",
                "model": parts[2] if len(parts) > 2 else "",
                "api_key_env": parts[3] if len(parts) > 3 else "OPENAI_API_KEY",
            })]
        if verb in ("use", "activate", "switch", "select"):
            return [ToolCall("model", {"action": "use", "name": arg})]
        if verb in ("test", "probe", "check"):
            return [ToolCall("model", {"action": "test", "name": arg})]
        if verb in ("remove", "delete"):
            return [ToolCall("model", {"action": "remove", "name": arg})]
        return [ToolCall("model", {"action": "list"})]

    def _api_instruction(self, rest: str) -> List[ToolCall]:
        """Parse 'api: list', 'api: register <name> <base_url> [key_env]', 'api: call <name> <path> [method]'."""
        rest = (rest or "").strip()
        verb, _, arg = rest.partition(" ")
        verb, arg = verb.lower(), arg.strip()
        if verb in ("register", "add", "set"):
            parts = arg.split()
            if not parts:
                return [ToolCall("api", {"action": "list"})]
            return [ToolCall("api", {"action": "register", "name": parts[0],
                                     "base_url": parts[1] if len(parts) > 1 else "",
                                     "auth_env": parts[2] if len(parts) > 2 else ""})]
        if verb in ("remove", "delete"):
            return [ToolCall("api", {"action": "remove", "name": arg})]
        if verb in ("call", "request", "invoke"):
            parts = arg.split()
            if not parts:
                return [ToolCall("api", {"action": "list"})]
            return [ToolCall("api", {"action": "call", "name": parts[0],
                                     "path": parts[1] if len(parts) > 1 else "",
                                     "method": parts[2].upper() if len(parts) > 2 else "GET"})]
        return [ToolCall("api", {"action": "list"})]

    def _connector_instruction(self, rest: str) -> List[ToolCall]:
        """Parse 'connector: add <name> <kind> <url>', 'connector: test <name>', 'connector: send <name> <text>'."""
        rest = (rest or "").strip()
        verb, _, arg = rest.partition(" ")
        verb, arg = verb.lower(), arg.strip()
        if verb in ("add", "register", "set"):
            parts = arg.split()
            if not parts:
                return [ToolCall("connector", {"action": "list"})]
            return [ToolCall("connector", {"action": "add", "name": parts[0],
                                           "kind": parts[1] if len(parts) > 1 else "webhook",
                                           "url": parts[2] if len(parts) > 2 else ""})]
        if verb in ("remove", "delete"):
            return [ToolCall("connector", {"action": "remove", "name": arg})]
        if verb in ("test", "probe", "check"):
            return [ToolCall("connector", {"action": "test", "name": arg})]
        if verb in ("send", "post", "notify"):
            name, _, message = arg.partition(" ")
            return [ToolCall("connector", {"action": "send", "name": name,
                                           "message": message.strip()})]
        return [ToolCall("connector", {"action": "list"})]

    def _explicit_tool(self, instructions: str) -> List[ToolCall]:
        remainder = instructions[len("tool"):].lstrip(": ").strip()
        name, _, raw_args = remainder.partition(" ")
        if not raw_args.strip():
            return [ToolCall(name.strip(), {})]
        try:
            return [ToolCall(name.strip(), json.loads(raw_args))]
        except ValueError as exc:
            return [ToolCall("__invalid__", {"error": f"arguments are not JSON: {exc}"})]

    # --- plain instructions --------------------------------------------------

    def _deliberate(self, text: str) -> List[ToolCall]:
        low = text.lower()
        path = self._first_path(text)
        module = self._first_module(text)
        note_wanted = any(word in low for word in ("note", "write", "save", "record", "document"))
        steps: List[ToolCall]

        if any(word in low for word in ("rag", "retrieval index", "semantic search", "index the",
                                        "search the index", "retrieve from")):
            steps = self._rag_instruction(text)
        elif any(word in low for word in ("connector", "webhook", "slack", "custom api",
                                          "registered api", "api registry")):
            steps = [ToolCall("api" if "api" in low else "connector", {"action": "list"})]
        elif any(word in low for word in ("which model", "model config", "switch model",
                                          "model endpoint", "what model")):
            steps = [ToolCall("model", {"action": "list"})]
        elif any(word in low for word in ("search", "grep", "find in", "look for", "where is")):
            steps = [ToolCall("run_shell", {"command": self._grep_command(text)})]
        elif any(word in low for word in ("git status", "git log", "git branch", "recent commit",
                                          "what changed")):
            steps = [ToolCall("git_status", {})]
        elif any(word in low for word in ("analyze", "ast", "code structure", "complexity")) and path:
            steps = [ToolCall("code_analyze", {"path": path})]
        elif any(word in low for word in ("remember", "store in memory", "recall from memory")):
            steps = [ToolCall("memory", {"action": "list"})]
        elif any(word in low for word in ("system info", "cpu", "memory usage", "disk space",
                                          "how much ram")):
            steps = [ToolCall("system_info", {})]
        elif any(word in low for word in ("fuse", "fusion", "combine models", "model fusion")):
            steps = [ToolCall("fuse", {"responses": ""})]
        elif any(word in low for word in ("vitals", "pulse", "heartbeat", "your body", "how do you feel",
                                          "mood", "emotion")):
            steps = [ToolCall("vitals", {})]
        elif module or any(word in low for word in ("javascript", "js module", "modules you")):
            steps = [ToolCall("js_module", {"name": module or ""})] if module \
                else [ToolCall("js_module", {})]
        elif path and any(word in low for word in ("look at", "see", "image", "picture", "view ")):
            steps = [ToolCall("look", {"source": path})]
        elif any(word in low for word in ("say ", "speak", "out loud", "voice")):
            steps = [ToolCall("speak", {"text": self._utterance(text)})]
        elif any(word in low for word in ("status", "health", "self-check", "self check")):
            steps = [ToolCall("run_shell", {"command": "python src/main.py status", "timeout": 180})]
        elif path and any(word in low for word in ("read", "open", "show", "cat", "inspect", "review")):
            steps = [ToolCall("read_file", {"path": path})]
        elif any(word in low for word in ("list", "inventory", "what files", "tree", "ls ")):
            steps = [ToolCall("list_dir", {"path": path or "."})]
        elif any(word in low for word in ("run ", "execute", "shell", "command")):
            steps = [ToolCall("run_shell", {"command": self._command(text), "timeout": 180})]
        elif note_wanted:
            steps = self._note_plan(text)
        else:
            # Nothing specific to go on: look around the repository.
            steps = [ToolCall("list_dir", {"path": "."}), ToolCall("read_file", {"path": "README.md"})]

        if note_wanted and steps[-1].tool not in ("write_file", "speak"):
            steps.append(ToolCall("write_file", {
                "path": self._note_path("task"),
                "content": self._note_header(text) + "$last\n```\n",
            }))
        return steps

    def _note_plan(self, text: str) -> List[ToolCall]:
        return [ToolCall("write_file", {
            "path": self._note_path("task"),
            "content": f"# {text[:80]}\n\nWritten at {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
        })]

    def _grep_command(self, text: str) -> str:
        quoted = re.findall(r"[\"']([^\"']{2,60})[\"']", text)
        if quoted:
            term = quoted[0]
        else:
            low = text.lower()
            cut = max(low.rfind(word) + len(word) for word in ("search for", "search", "grep for",
                                                               "grep", "find in", "look for", "where is"))
            term = text[cut:].strip() or text
        return f"grep -rn -i -e {shlex.quote(term[:80])} --include='*.py' --include='*.js' --include='*.md' . | head -40"

    def _command(self, text: str) -> str:
        """The command inside an instruction like 'run: ls -la' or 'execute ls -la'."""
        command = text.strip()
        while True:
            stripped = re.sub(r"^\s*(?:please\s+)?(?:run|execute|exec|shell|command)\s*[: ]\s*",
                              "", command, count=1, flags=re.IGNORECASE)
            if stripped == command:
                break
            command = stripped
        return command.strip().strip("\"'") or text

    def _utterance(self, text: str) -> str:
        quoted = re.findall(r"[\"']([^\"']{2,200})[\"']", text)
        if quoted:
            return quoted[0]
        low = text.lower()
        for marker in ("say", "speak", "out loud"):
            if marker in low:
                return text[low.index(marker) + len(marker):].strip(" :\"'") or text
        return text

    @staticmethod
    def _first_path(text: str) -> Optional[str]:
        for match in FILE_HINT.findall(text):
            if match.lower() not in ("note",):
                return match
        for match in PATH_HINT.findall(text):
            candidate = match.strip(".,;")
            if os.path.exists(os.path.join(REPO_ROOT, candidate)):
                return candidate
        return None

    @staticmethod
    def _first_module(text: str) -> Optional[str]:
        match = MODULE_HINT.search(text.lower())
        return match.group(1) if match else None

    # --- inventing its own work ---------------------------------------------

    def _self_directed(self, rest: str) -> List[ToolCall]:
        routine = (rest or "inspect").split(":")[0].strip() or "inspect"

        if routine == "reflect":
            return [
                ToolCall("run_shell", {"command":
                          "ls -1t devmind/agent/notes 2>/dev/null | head -8; echo '---'; "
                          "wc -l devmind/agent/notes/*.md 2>/dev/null | tail -3"}),
                ToolCall("write_file", {
                    "path": self._note_path("reflection"),
                    "content": ("# Reflection\n\nWritten at "
                                f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n\nWhat I have been doing:\n\n```\n$last\n```\n"),
                }),
            ]
        if routine == "vitals":
            return [
                ToolCall("vitals", {}),
                ToolCall("write_file", {
                    "path": self._note_path("vitals"),
                    "content": f"# Body reading\n\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n$last\n",
                }),
            ]
        if routine == "voice":
            return [
                ToolCall("vitals", {}),
                ToolCall("speak", {"text": "Body report. $last"}),
            ]
        if routine == "selftest":
            return [
                ToolCall("run_shell", {"command": "python src/main.py status", "timeout": 180}),
                ToolCall("write_file", {
                    "path": self._note_path("selftest"),
                    "content": f"# Self-check\n\nRan at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        if routine == "inventory":
            return [
                ToolCall("list_dir", {"path": "src"}),
                ToolCall("write_file", {
                    "path": self._note_path("inventory"),
                    "content": f"# Source inventory\n\nTaken at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        if routine == "improve":
            module = self._next_module()
            self._looked_at.add(module)
            return [
                ToolCall("code_analyze", {"path": module}),
                ToolCall("write_file", {
                    "path": self._note_path("improvement"),
                    "content": f"# Code analysis: {module}\n\nAnalyzed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        if routine == "remember":
            return [
                ToolCall("memory", {"action": "list"}),
                ToolCall("write_file", {
                    "path": self._note_path("memory"),
                    "content": f"# Memory dump\n\nAt {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        if routine == "explore":
            return [
                ToolCall("run_shell", {"command":
                          "find src -name '*.py' -not -path '*/__pycache__/*' | shuf | head -1 | "
                          "xargs -I{} sh -c 'echo \"=== {} ===\"; head -20 {}'"}),
                ToolCall("write_file", {
                    "path": self._note_path("exploration"),
                    "content": f"# Random exploration\n\nAt {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        if routine == "git":
            return [
                ToolCall("git_status", {}),
                ToolCall("write_file", {
                    "path": self._note_path("git"),
                    "content": f"# Git state\n\nAt {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        if routine == "system":
            return [
                ToolCall("system_info", {}),
                ToolCall("write_file", {
                    "path": self._note_path("system"),
                    "content": f"# System info\n\nAt {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        if routine == "index":
            return [
                ToolCall("rag", {"action": "index", "path": "src"}),
                ToolCall("write_file", {
                    "path": self._note_path("index"),
                    "content": f"# Retrieval index\n\nRebuilt at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]

        module = self._next_module()
        self._looked_at.add(module)
        return [
            ToolCall("read_file", {"path": module}),
            ToolCall("write_file", {
                "path": self._note_path("inspection"),
                "content": f"# Inspection of {module}\n\nRead at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```python\n$last\n```\n",
            }),
        ]

    ROUTINES = {
        "self:inspect": "Read one of its own modules",
        "self:reflect": "Reflect on its own recent work",
        "self:voice": "Report its body state out loud",
        "self:selftest": "Self-check the engine",
        "self:inventory": "Inventory its own source tree",
        "self:improve": "Analyze a module with the AST code analyzer",
        "self:remember": "Dump persistent memory and note it",
        "self:explore": "Explore a random file in the source tree",
        "self:git": "Check git status and recent commits",
        "self:system": "Report system info (CPU, memory, disk)",
        "self:index": "Rebuild its retrieval index over its own source",
    }

    def propose(self, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """One unit of self-directed work, chosen from what the agent knows."""
        context = context or {}
        recent = context.get("recent_actions") or []
        failures = sum(1 for action in recent if not action.get("ok"))

        order = ["self:inspect", "self:improve", "self:reflect", "self:explore",
                "self:voice", "self:selftest", "self:inventory", "self:remember",
                "self:git", "self:system", "self:index"]
        if failures:
            order.insert(0, "self:selftest")  # something broke: check itself first
        elif not recent:
            order.insert(0, "self:inventory")  # nothing done yet: see what is here

        self._rotation += 1
        routine = order[self._rotation % len(order)]
        return {"title": self.ROUTINES[routine], "instructions": routine}

    def follow_up(self, task: Dict[str, Any], outcome: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """What to queue after a finished task, so work chains on its own."""
        instructions = (task.get("instructions") or "")
        if outcome.get("action") == "failed":
            return {"title": "Re-check after a failed task", "instructions": "self:selftest"}
        if instructions.startswith("self:inspect"):
            return {"title": "Reflect on what it just read", "instructions": "self:reflect"}
        return None

    # --- helpers -------------------------------------------------------------

    def _next_module(self) -> str:
        pool = [module for module in MODULE_POOL if module not in self._looked_at] or MODULE_POOL
        module = pool[self._rotation % len(pool)]
        return module if os.path.exists(os.path.join(REPO_ROOT, module)) else pool[0]

    def _note_path(self, kind: str) -> str:
        return os.path.join(self.notes_dir, f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}.md")

    @staticmethod
    def _note_header(title: str) -> str:
        return f"# {title[:80]}\n\nTaken at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n"


def build_brain():
    """The strongest brain available: a real model when one is configured."""
    from src.agent.model_brain import ModelBrain

    fallback = DeliberativeBrain()
    model = ModelBrain(fallback=fallback)
    return model if model.available() else fallback
