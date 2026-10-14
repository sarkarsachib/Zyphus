"""
Deciding what to do next.

Today the decision maker is rule-based: it follows an explicit instruction when
a task carries one, and when the queue is empty it proposes its own inspection
work. No model is required to run the loop, and nothing here pretends to reason.

The loop only needs `plan(task)` and `propose()`. To put a real model behind it
later, implement those two methods against your model client and pass the new
brain to `AgentLoop(brain=...)` - the tools, the store and the loop stay as they are.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agent.tools import REPO_ROOT

MODULE_POOL = [
    "src/nrx_interpreter.py",
    "src/custom_kernel.py",
    "src/custom_terminal.py",
    "src/js_module_bridge_fixed.py",
    "src/agent/tools.py",
    "src/agent/store.py",
    "src/agent/loop.py",
]


@dataclass
class ToolCall:
    tool: str
    arguments: Dict[str, Any] = field(default_factory=dict)


class RuleBasedBrain:
    """Turns a task into tool calls, and invents its own work when idle."""

    name = "rule-based"

    def __init__(self, notes_dir: str = "devmind/agent/notes"):
        self.notes_dir = notes_dir
        self._rotation = 0

    # --- following a task ----------------------------------------------------

    def plan(self, task: Dict[str, Any]) -> List[ToolCall]:
        instructions = (task.get("instructions") or "").strip()

        if instructions.startswith("@tool"):
            return self._plan_explicit_tool(instructions)
        if instructions.startswith("shell:"):
            return [ToolCall("run_shell", {"command": instructions[len("shell:"):].strip()})]
        if instructions.startswith("fetch:"):
            return [ToolCall("web_fetch", {"url": instructions[len("fetch:"):].strip()})]
        if instructions.startswith("self:"):
            return self._plan_self_directed(instructions)

        # No explicit instruction: look around the repository.
        return [
            ToolCall("list_dir", {"path": "."}),
            ToolCall("read_file", {"path": "README.md"}),
        ]

    def _plan_explicit_tool(self, instructions: str) -> List[ToolCall]:
        import json
        remainder = instructions[len("@tool"):].strip()
        name, _, raw_args = remainder.partition(" ")
        if not raw_args.strip():
            return [ToolCall(name.strip(), {})]
        try:
            arguments = json.loads(raw_args)
        except ValueError as exc:
            return [ToolCall("__invalid__", {"error": f"arguments are not JSON: {exc}"})]
        return [ToolCall(name.strip(), arguments)]

    # --- inventing its own work ---------------------------------------------

    def _plan_self_directed(self, instructions: str) -> List[ToolCall]:
        if instructions.startswith("self:inspect"):
            module = self._next_module()
            note = self._note_path("inspect".replace("inspect", "inspection"))
            return [
                ToolCall("read_file", {"path": module}),
                ToolCall("write_file", {
                    "path": note,
                    "content": f"# Inspection of {module}\n\nRead at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```python\n$last\n```\n",
                }),
            ]
        if instructions.startswith("self:selftest"):
            note = self._note_path("selftest")
            return [
                ToolCall("run_shell", {"command": "python src/main.py status", "timeout": 120}),
                ToolCall("write_file", {
                    "path": note,
                    "content": f"# Self-check\n\nRan at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
                }),
            ]
        # self:inventory and anything else under self:
        note = self._note_path("inventory")
        return [
            ToolCall("list_dir", {"path": "src"}),
            ToolCall("write_file", {
                "path": note,
                "content": f"# Source inventory\n\nTaken at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n```\n$last\n```\n",
            }),
        ]

    def propose(self) -> Optional[Dict[str, str]]:
        """One unit of self-directed work, rotating through what it can do."""
        self._rotation += 1
        if self._rotation % 3 == 0:
            return {"title": "Self-check the engine",
                    "instructions": "self:selftest"}
        if self._rotation % 3 == 1:
            return {"title": "Inspect its own source tree",
                    "instructions": "self:inventory"}
        return {"title": "Read one of its own modules",
                "instructions": "self:inspect"}

    def _next_module(self) -> str:
        module = MODULE_POOL[self._rotation % len(MODULE_POOL)]
        return module if os.path.exists(os.path.join(REPO_ROOT, module)) else "README.md"

    def _note_path(self, kind: str) -> str:
        return os.path.join(self.notes_dir, f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}.md")
