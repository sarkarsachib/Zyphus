"""
The autonomy loop.

One tick = claim a task, turn it into tool calls, run them, record everything.
When the queue is empty it does not stop: the brain proposes its own work, and a
finished task may queue its own follow-up, so the agent keeps chaining work
without being asked. All state lives in the store, so restarting the process
loses nothing - claimed-but-unfinished tasks are reclaimed.

Pacing adapts to the backlog: a queue waiting on the agent is served faster than
an idle one. The agent's body (src/agent/embodiment.py) is read on demand for
status, and its voice (src/agent/senses.py) is exposed through the same status.
"""

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from src.agent.brain import ToolCall, build_brain
from src.agent.store import AgentStore, now_iso
from src.agent.tools import ToolRegistry, build_registry

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = float(os.environ.get("ZYPHUS_AGENT_INTERVAL", "15"))
DEFAULT_SELF_INTERVAL = float(os.environ.get("ZYPHUS_AGENT_SELF_INTERVAL", "300"))
FOLLOW_UP_DELAY = float(os.environ.get("ZYPHUS_AGENT_CHAIN_DELAY", "20"))
VITALS_TTL = 10.0


class AgentLoop:
    def __init__(self, store: Optional[AgentStore] = None,
                 registry: Optional[ToolRegistry] = None,
                 brain: Optional[Any] = None,
                 interval: float = DEFAULT_INTERVAL,
                 self_interval: float = DEFAULT_SELF_INTERVAL):
        self.store = store or AgentStore()
        self.registry = registry or build_registry()
        self.brain = brain or build_brain()
        self.interval = interval
        self.self_interval = self_interval
        self.started_at = now_iso()
        self.ticks = 0
        self.last_tick_at: Optional[str] = None
        self._last_self_at = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._vitals: Dict[str, Any] = {}
        self._vitals_at = 0.0

    # --- one unit of work ----------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self.ticks += 1
        self.last_tick_at = now_iso()
        task = self.store.claim_next()
        if task is None:
            result = self._idle_tick()
        else:
            result = self._run_task(task)
            self._chain_follow_up(task, result)
        result["tick"] = self.ticks
        return result

    def run_specific(self, task_id: str) -> Dict[str, Any]:
        """Run one named task now - how the token-gated control box drives the agent."""
        task = self.store.claim_task(task_id)
        if task is None:
            return {"action": "missing", "task_id": task_id}
        self.ticks += 1
        self.last_tick_at = now_iso()
        result = self._run_task(task)
        self._chain_follow_up(task, result)
        result["tick"] = self.ticks
        return result

    def submit(self, instructions: str, title: Optional[str] = None,
               origin: str = "dashboard", priority: int = 1) -> Dict[str, Any]:
        """Queue instructions and run them immediately, returning what happened."""
        instructions = (instructions or "").strip()
        if not instructions:
            return {"action": "rejected", "error": "nothing to do"}
        task_id = self.store.enqueue(title or instructions[:60], instructions,
                                     origin=origin, priority=priority)
        return {"task_id": task_id, **self.run_specific(task_id)}

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

    # --- keeping itself busy -------------------------------------------------

    def _chain_follow_up(self, task: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Let the brain queue the next step of its own work."""
        if task.get("origin") == "chain":
            return
        try:
            follow_up = self.brain.follow_up(task, result)
        except Exception as exc:
            logger.warning("follow-up failed for %s: %s", task["id"], exc)
            return
        if not follow_up:
            return
        self.store.enqueue(follow_up["title"], follow_up["instructions"], origin="chain",
                           priority=6, delay_seconds=FOLLOW_UP_DELAY)
        logger.info("chained follow-up after %s: %s", task["id"], follow_up["title"])

    def _idle_tick(self) -> Dict[str, Any]:
        """No task waiting: invent one, paced by self_interval."""
        if time.time() - self._last_self_at < self.self_interval:
            return {"action": "idle"}
        proposal = None
        try:
            proposal = self.brain.propose(self._context())
        except Exception as exc:
            logger.warning("proposal failed: %s", exc)
        if not proposal:
            return {"action": "idle"}
        task_id = self.store.enqueue(proposal["title"], proposal["instructions"],
                                     origin="self", priority=8)
        self._last_self_at = time.time()
        return {"action": "proposed", "task_id": task_id, "title": proposal["title"]}

    def _context(self) -> Dict[str, Any]:
        """What the brain is allowed to know about its own state when proposing."""
        notes = []
        notes_dir = os.path.join(self.store.path.rsplit(os.sep, 2)[0], "notes")
        if os.path.isdir(notes_dir):
            notes = sorted(os.listdir(notes_dir))[-10:]
        return {
            "queue": self.store.counts(),
            "recent_actions": self.store.recent_actions(20),
            "recent_tasks": self.store.list_tasks(8),
            "notes": notes,
        }

    def _activity(self) -> Dict[str, float]:
        """How the agent has actually been doing - what its mood is read from."""
        actions = self.store.recent_actions(20)
        if actions:
            success_rate = sum(1 for action in actions if action["ok"]) / len(actions)
        else:
            success_rate = 0.7
        counts = self.store.counts()
        backlog = min(1.0, (counts["pending"] + counts["failed"]) / 10.0)
        return {"success_rate": success_rate, "backlog": backlog}

    # --- running ------------------------------------------------------------

    def _wait_seconds(self) -> float:
        """A backlog is served faster than an idle queue."""
        pending = self.store.counts()["pending"]
        if pending >= 3:
            return max(2.0, self.interval / 3.0)
        if pending:
            return max(2.0, self.interval / 2.0)
        return self.interval

    def run_forever(self) -> None:
        logger.info("agent loop running (interval=%.0fs, self_interval=%.0fs)",
                    self.interval, self.self_interval)
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # a bad tick must not kill the loop
                logger.error("tick failed: %s", exc)
            self._stop.wait(self._wait_seconds())

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

    # --- reporting -----------------------------------------------------------

    def body(self) -> Dict[str, Any]:
        """The agent's vitals, cached briefly so frequent status reads stay cheap."""
        if time.time() - self._vitals_at > VITALS_TTL:
            from src.agent import embodiment

            try:
                self._vitals = embodiment.vitals(self._activity())
            except Exception as exc:
                self._vitals = {"error": f"{type(exc).__name__}: {exc}"}
            self._vitals_at = time.time()
        return self._vitals

    def status(self, action_limit: int = 15) -> Dict[str, Any]:
        from src.agent import senses

        utterances = senses.utterances(5)
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
            "vitals": self.body(),
            "voice": {
                "latest": utterances[0] if utterances else None,
                "utterances": utterances,
            },
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
