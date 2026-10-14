"""
The autonomy loop.

One tick = claim a task, turn it into tool calls, run them, record everything.
When the queue is empty it does not stop: it proposes its own inspection work,
paced so the box is not thrashed. All state lives in the store, so restarting
the process loses nothing - claimed-but-unfinished tasks are reclaimed.
"""

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from src.agent.brain import RuleBasedBrain, ToolCall
from src.agent.store import AgentStore, now_iso
from src.agent.tools import ToolRegistry, build_registry

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = float(os.environ.get("ZYPHUS_AGENT_INTERVAL", "15"))
DEFAULT_SELF_INTERVAL = float(os.environ.get("ZYPHUS_AGENT_SELF_INTERVAL", "300"))


class AgentLoop:
    def __init__(self, store: Optional[AgentStore] = None,
                 registry: Optional[ToolRegistry] = None,
                 brain: Optional[RuleBasedBrain] = None,
                 interval: float = DEFAULT_INTERVAL,
                 self_interval: float = DEFAULT_SELF_INTERVAL):
        self.store = store or AgentStore()
        self.registry = registry or build_registry()
        self.brain = brain or RuleBasedBrain()
        self.interval = interval
        self.self_interval = self_interval
        self.started_at = now_iso()
        self.ticks = 0
        self.last_tick_at: Optional[str] = None
        self._last_self_at = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    # --- one unit of work ----------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self.ticks += 1
        self.last_tick_at = now_iso()
        task = self.store.claim_next()
        if task is None:
            result = self._idle_tick()
        else:
            result = self._run_task(task)
        result["tick"] = self.ticks
        return result

    def _run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        calls: List[ToolCall] = []
        try:
            calls = self.brain.plan(task)
        except Exception as exc:
            logger.warning("planning failed for %s: %s", task["id"], exc)
            return {"action": "failed", "task_id": task["id"], "error": str(exc)}

        if not calls:
            self.store.complete(task["id"], "nothing to do")
            return {"action": "executed", "task_id": task["id"], "status": "done"}

        previous_output = ""
        for call in calls:
            if call.tool == "__invalid__":
                self.store.fail(task["id"], call.arguments.get("error", "invalid tool call"))
                return {"action": "failed", "task_id": task["id"],
                        "error": call.arguments.get("error", "invalid tool call")}

            arguments = self._substitute(call.arguments, previous_output)
            started = time.time()
            result = self.registry.run(call.tool, arguments)
            duration_ms = int((time.time() - started) * 1000)
            self.store.log_action(task["id"], call.tool, arguments, result.ok,
                                  result.output, result.error, duration_ms)
            logger.info("tool=%s ok=%s task=%s (%dms)", call.tool, result.ok, task["id"], duration_ms)

            if not result.ok:
                outcome = self.store.fail(task["id"], f"{call.tool}: {result.error}")
                return {"action": "failed", "task_id": task["id"], "outcome": outcome,
                        "tool": call.tool, "error": result.error}

            previous_output = result.output

        self.store.complete(task["id"], previous_output[:1000])
        return {"action": "executed", "task_id": task["id"], "status": "done",
                "tools": [c.tool for c in calls], "output": previous_output[:400]}

    @staticmethod
    def _substitute(arguments: Dict[str, Any], previous_output: str) -> Dict[str, Any]:
        """Let a call reuse the previous call's output with `$last`."""
        return {
            key: (value.replace("$last", previous_output) if isinstance(value, str) else value)
            for key, value in arguments.items()
        }

    def _idle_tick(self) -> Dict[str, Any]:
        """No task waiting: invent one, paced by self_interval."""
        if time.time() - self._last_self_at < self.self_interval:
            return {"action": "idle"}
        proposal = None
        try:
            proposal = self.brain.propose()
        except Exception as exc:
            logger.warning("proposal failed: %s", exc)
        if not proposal:
            return {"action": "idle"}
        task_id = self.store.enqueue(proposal["title"], proposal["instructions"],
                                     origin="self", priority=8)
        self._last_self_at = time.time()
        return {"action": "proposed", "task_id": task_id, "title": proposal["title"]}

    # --- running ------------------------------------------------------------

    def run_forever(self) -> None:
        logger.info("agent loop running (interval=%.0fs, self_interval=%.0fs)",
                    self.interval, self.self_interval)
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # a bad tick must not kill the loop
                logger.error("tick failed: %s", exc)
            self._stop.wait(self.interval)

    def start_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self.run_forever, name="zyphus-agent",
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self, action_limit: int = 15) -> Dict[str, Any]:
        return {
            "running": self.running,
            "brain": self.brain.name,
            "started_at": self.started_at,
            "ticks": self.ticks,
            "last_tick_at": self.last_tick_at,
            "interval_seconds": self.interval,
            "self_interval_seconds": self.self_interval,
            "queue": self.store.counts(),
            "queue_path": self.store.path,
            "tools": self.registry.catalog(),
            "recent_actions": [
                {**a, "arguments": _safe_json(a.get("arguments"))}
                for a in self.store.recent_actions(action_limit)
            ],
            "pending_tasks": [t for t in self.store.list_tasks(10) if t["status"] in ("pending", "running")],
        }


def _safe_json(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    return raw


_loop: Optional[AgentLoop] = None


def get_loop() -> AgentLoop:
    """Process-wide singleton, so the dashboard and the CLI share one loop."""
    global _loop
    if _loop is None:
        _loop = AgentLoop()
    return _loop
