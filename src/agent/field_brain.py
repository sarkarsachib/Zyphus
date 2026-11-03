"""
The brain, as one continuously evolving field.

`AdaptiveFieldBrain` is the whole decision layer, and it does not choose a
regime. It perceives the situation as signals, lets the population of cognitive
cells settle, and then thinks *through* whichever coalition currently holds the
field:

    diffuse      spread activation: probe what is there, ground the attempt
    structural   compose: recruit the planner, the model, the retrieval index
    convergent   narrow and commit to the strongest candidate

The old deliberative planner is no longer the brain. It is the `planner`
capability (`capabilities.py`), recruited by the composing cells like any other
capability. Instruction parsing and tool composition still live in
`DeliberativeBrain`; what changed is who decides to use it.

Nothing here is scheduled: a waiting task raises `task` pressure, a run of
failures raises `stagnation` and `surprise`, repetition raises `fatigue`, an
unmapped world model raises `novelty`, and the coalition that wins is what those
add up to. `evolve()` steps the same dynamics with no task at all, so the field
keeps moving between perceptions instead of freezing.
"""

import os
import time
from collections import deque
from typing import Any, Dict, List, Optional

from src.agent import capabilities as capability_layer
from src.agent import counterfactual, rag, substrate
from src.agent.brain import DeliberativeBrain, ToolCall
from src.agent.field import ACTIVE_THRESHOLD, HORIZON_SECONDS, CognitiveField

# What kind of act each tool is, for the counterfactual engine.
TOOL_KINDS = {
    "run_shell": "command",
    "write_file": "patch",
    "read_file": "query",
    "list_dir": "query",
    "rag": "query",
    "git_status": "query",
    "code_analyze": "query",
    "memory": "query",
    "world": "query",
    "substrate": "query",
    "phase": "query",
    "predict": "query",
    "resources": "query",
    "vitals": "probe",
    "speak": "probe",
    "look": "probe",
}

# Which capability the regime's coalition always fields, even before a secondary
# cell has crossed the activation threshold.
PRIMARY_CAPABILITY = {"diffuse": "probe", "structural": "planner", "convergent": "planner"}

# Signals whose world-model readings are cached: they are a SQLite read each.
WORLD_TTL = 60.0
INDEX_TTL = 120.0


class AdaptiveFieldBrain:
    """One continuously operating field, not a set of modes."""

    name = "adaptive-field"

    def __init__(self, composer: Optional[DeliberativeBrain] = None,
                 model: Optional[Any] = None,
                 field: Optional[CognitiveField] = None,
                 notes_dir: str = "devmind/agent/notes",
                 world_path: Optional[str] = None,
                 history: int = 24,
                 capabilities: Optional[Dict[str, Any]] = None):
        self.composer = composer or DeliberativeBrain(notes_dir)
        self.model = model
        self.field = field or CognitiveField()
        self.world_path = world_path
        self.capabilities = capabilities or capability_layer.default_capabilities(
            self.composer, model, index_chunks=self._index_chunks)
        self.history: deque = deque(maxlen=history)
        self.tool_stats: Dict[str, Dict[str, int]] = {}
        self._world_cache = (0.0, {})
        self._index_cache = (0.0, 0)
        self._last_regime: Optional[str] = None
        self._last_step_at = 0.0
        self._last_context: Dict[str, Any] = {}

    # --- the loop's interface ------------------------------------------------

    def plan(self, task: Dict[str, Any]) -> List[ToolCall]:
        """Perceive the task, settle the field, and act through the winning coalition."""
        regime = self.settle(task_pressure=1.0)
        coalition = self.field.coalition()
        chosen = self.select(self.candidates(task, regime), regime, coalition)
        self.field.metacognition.predict(regime, chosen["expected"])
        self._last_regime = regime
        return chosen["calls"]

    def propose(self, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """Idle: what the field is drawn to now decides what gets worked on."""
        context = context or {}
        regime = self.settle(task_pressure=0.0, context=context)
        proposal = self.routine_for(regime)
        self.field.metacognition.predict(regime)
        self._last_regime = regime
        return proposal

    def follow_up(self, task: Dict[str, Any], outcome: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Queue the next step the current coalition implies."""
        if outcome.get("action") == "failed":
            return {"title": "Re-check after a failed task", "instructions": "self:selftest"}
        if self._last_regime == "convergent":
            return {"title": "Consolidate what the last task produced",
                    "instructions": "self:reflect"}
        if (task.get("instructions") or "").startswith("self:inspect"):
            return {"title": "Reflect on what it just read", "instructions": "self:reflect"}
        return None

    def observe(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Close the loop with reality: score the prediction, then reshape the field."""
        success = result.get("action") != "failed"
        resolution = self.field.observe(success)
        tools = list(result.get("tools") or [])
        if result.get("tool"):
            tools.append(result["tool"])
        for tool in tools:
            entry = self.tool_stats.setdefault(tool, {"attempts": 0, "successes": 0})
            entry["attempts"] += 1
            entry["successes"] += 1 if success else 0
        self.history.append({
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "regime": self._last_regime or self.field.regime,
            "ok": success,
            "tools": tools,
            "task": (task.get("instructions") or "")[:80],
        })
        self._last_regime = None
        try:
            self.field.save()
        except OSError:
            pass
        return resolution

    # --- continuous evolution ------------------------------------------------

    def evolve(self, seconds: float = HORIZON_SECONDS) -> Dict[str, Any]:
        """Step the field with no task: the population keeps running on its own."""
        signals = self.sense(task_pressure=0.0, context=self._last_context)
        self.field.perceive(signals)
        self.field.step(seconds=seconds if seconds and seconds > 0 else HORIZON_SECONDS)
        self._last_step_at = time.time()
        return {"regime": self.field.regime, "coalitions": self.field.coalitions(),
                "steps": self.field.steps}

    # --- perception ----------------------------------------------------------

    def settle(self, task_pressure: float, context: Optional[Dict[str, Any]] = None) -> str:
        """Read the situation, integrate the field for the elapsed time, return the regime."""
        self._last_context = context or {}
        signals = self.sense(task_pressure=task_pressure, context=context)
        self.field.perceive(signals)
        now = time.time()
        elapsed = now - self._last_step_at if self._last_step_at else HORIZON_SECONDS
        self._last_step_at = now
        return self.field.step(seconds=max(HORIZON_SECONDS, elapsed))

    def sense(self, task_pressure: float = 0.0,
              context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Every signal the field is allowed to see, measured from real state."""
        context = context or {}
        recent = self._recent(context)
        return {
            "task": 1.0 if task_pressure else 0.0,
            "backlog": self._backlog(context),
            "novelty": self._novelty(),
            "uncertainty": self._uncertainty(recent),
            "surprise": self.field.metacognition.surprise,
            "stagnation": self._stagnation(recent),
            "competence": self._competence(recent),
            "fatigue": self._fatigue(recent),
        }

    def _recent(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """The loop hands over its action log when it has one; otherwise use own record."""
        actions = context.get("recent_actions")
        if actions:
            return [{"ok": bool(a.get("ok")), "tool": a.get("tool", "")} for a in actions]
        return [{"ok": bool(entry.get("ok")),
                 "tool": (entry.get("tools") or [""])[0]} for entry in self.history]

    @staticmethod
    def _backlog(context: Dict[str, Any]) -> float:
        queue = context.get("queue") or {}
        waiting = int(queue.get("pending", 0) or 0) + int(queue.get("failed", 0) or 0)
        return min(1.0, waiting / 10.0)

    @staticmethod
    def _competence(recent: List[Dict[str, Any]]) -> float:
        if not recent:
            return 0.65
        successes = sum(1 for entry in recent if entry.get("ok"))
        return round((successes + 1.3) / (len(recent) + 2), 4)

    @staticmethod
    def _stagnation(recent: List[Dict[str, Any]]) -> float:
        """How much of the recent tail failed to do anything useful."""
        tail = recent[-5:]
        if not tail:
            return 0.0
        failures = 0
        for entry in reversed(tail):
            if entry.get("ok"):
                break
            failures += 1
        return round(min(1.0, failures / len(tail)), 4)

    @staticmethod
    def _fatigue(recent: List[Dict[str, Any]]) -> float:
        """Repetition plus sustained busyness - what makes a coalition want to settle."""
        if not recent:
            return 0.0
        tools = [entry.get("tool") or "" for entry in recent]
        common = max(tools.count(tool) for tool in set(tools))
        repetition = common / len(tools)
        load = min(1.0, len(recent) / 20.0)
        return round(min(1.0, 0.5 * repetition + 0.5 * load), 4)

    def _world_stats(self) -> Dict[str, Any]:
        now = time.time()
        cached_at, cached = self._world_cache
        if cached and now - cached_at < WORLD_TTL:
            return cached
        try:
            from src.agent.worldmodel import WorldModel

            stats = WorldModel(self.world_path or None).stats()
        except Exception:
            stats = {}
        self._world_cache = (now, stats)
        return stats

    def _novelty(self) -> float:
        """How much of what the world model knows it has never actually looked at."""
        stats = self._world_stats()
        concepts = int(stats.get("concepts", 0) or 0)
        observations = int(stats.get("observations", 0) or 0)
        if concepts <= 0:
            return 0.85
        return round(max(0.0, min(1.0, 1.0 - observations / (concepts * 2.0))), 4)

    def _uncertainty(self, recent: List[Dict[str, Any]]) -> float:
        """The current cognitive structure's own reading, else unverified predictions."""
        last = substrate.last()
        value = last.get("uncertainty")
        if value is not None:
            return round(max(0.0, min(1.0, float(value))), 4)
        stats = self._world_stats()
        predictions = int(stats.get("predictions", 0) or 0)
        verified = int(stats.get("verified", 0) or 0)
        if predictions:
            return round(1.0 - verified / predictions, 4)
        if recent:
            return round(1.0 - self._competence(recent), 4)
        return 0.5

    def _index_chunks(self) -> int:
        now = time.time()
        cached_at, cached = self._index_cache
        if now - cached_at < INDEX_TTL:
            return cached
        try:
            chunks = int(rag.stats().get("chunks", 0) or 0)
        except Exception:
            chunks = 0
        self._index_cache = (now, chunks)
        return chunks

    # --- recruiting capabilities ---------------------------------------------

    def candidate_capabilities(self, regime: str) -> List[str]:
        """Which capabilities the winning coalition fields, in recruitment order."""
        names = [PRIMARY_CAPABILITY.get(regime, "planner")]
        extras = {"diffuse": ("retrieval",), "structural": ("model", "retrieval"),
                  "convergent": ()}.get(regime, ())
        for name in extras:
            if name not in names and self.field.recruited(name, ACTIVE_THRESHOLD):
                names.append(name)
        return names

    def candidates(self, task: Dict[str, Any], regime: str,
                   coalition: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """The plans the active cells are willing to field."""
        out: List[Dict[str, Any]] = []
        for name in self.candidate_capabilities(regime):
            capability = self.capabilities.get(name)
            if capability is None or not capability.available():
                continue
            calls = capability.compose(task)
            if calls:
                out.append({"source": name, "capability": name, "calls": calls})
        if not out:
            out.append({"source": "probe", "capability": "probe",
                        "calls": [ToolCall("list_dir", {"path": "src"})]})
        return out

    # --- choosing between them -----------------------------------------------

    def select(self, candidates: List[Dict[str, Any]], regime: str,
               coalition: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score each candidate against predicted risk and measured reliability."""
        scored = [self.score(candidate, regime, coalition) for candidate in candidates]
        best = scored[0]
        for entry in scored[1:]:
            if entry["score"] > best["score"]:
                best = entry
        return best

    def confidence(self, regime: str, coalition: Optional[Dict[str, Any]] = None) -> float:
        """How much this regime is trusted, blended with the coalition's own strength."""
        meta = self.field.metacognition.confidence(regime)
        energy = float((coalition or {}).get("energy", 0.0) or 0.0)
        strength = min(1.0, energy * 1.5)
        return round(0.6 * meta + 0.4 * strength, 4)

    def score(self, candidate: Dict[str, Any], regime: str,
              coalition: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        calls = candidate.get("calls") or []
        first = calls[0].tool if calls else ""
        confidence = self.confidence(regime, coalition)
        tool_rate = self.tool_rate(first)
        risk, cost = self.predict(first, calls)
        score = (0.55 * confidence + 0.25 * tool_rate + 0.20 * (1.0 - risk)
                 - 0.02 * min(len(calls), 5) - 0.001 * min(cost, 10.0))
        return {**candidate, "risk": risk, "cost": cost, "score": round(score, 4),
                "expected": round(0.6 * confidence + 0.4 * tool_rate, 4)}

    def tool_rate(self, tool: str) -> float:
        entry = self.tool_stats.get(tool)
        if not entry or not entry["attempts"]:
            return 0.65
        return round((entry["successes"] + 1.0) / (entry["attempts"] + 2.0), 4)

    @staticmethod
    def predict(tool: str, calls: List[ToolCall]) -> tuple:
        """Predicted risk and cost of a candidate's opening move.

        Commands go through the counterfactual engine, which knows which ones
        change the machine. A write cannot be predicted from a diff that does not
        exist yet, so it is scored from its kind alone rather than pretending a
        blast radius was measured.
        """
        kind = TOOL_KINDS.get(tool, "probe")
        if kind == "command":
            payload = str((calls[0].arguments or {}).get("command", "")) if calls else ""
            prediction = counterfactual.predict(
                counterfactual.Candidate(label="candidate", kind="command", payload=payload))
            return float(prediction["risk"]), float(prediction["cost"])
        if kind == "patch":
            return 0.45, 3.0
        return 0.05, 0.5

    # --- what an idle field is drawn to --------------------------------------

    def routine_for(self, regime: str) -> Dict[str, str]:
        """The work the winning coalition implies - no rotation counter anywhere."""
        if regime == "convergent":
            if (self.field.signals.get("fatigue", 0.0) > 0.5
                    or self.field.signals.get("stagnation", 0.0) > 0.3):
                return self._routine("self:reflect", "Consolidate what the last work produced")
            return self._routine("self:improve", "Analyze a module with the AST analyzer")
        if regime == "structural":
            concept = self._concept()
            if concept and self._open_hypothesis_work():
                return self._routine(f"world: hypotheses {concept}",
                                     f"Generate hypotheses about {concept}")
            return self._routine("self:adapt", "Compose a structure for an open question")
        return self._routine("self:explore", "Read something it has not read")

    @staticmethod
    def _routine(instructions: str, title: str) -> Dict[str, str]:
        return {"title": title, "instructions": instructions}

    def _concept(self) -> str:
        stats = self._world_stats()
        relations = stats.get("top_relations") or []
        if relations:
            return str(relations[0].get("src") or "")
        return ""

    @staticmethod
    def _open_hypothesis_work() -> bool:
        last = substrate.last()
        return bool(last.get("hypotheses"))

    # --- reporting -----------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Everything the field is currently made of, for the dashboard and the CLI."""
        data = self.field.snapshot()
        data["history"] = list(self.history)[-8:]
        data["tools"] = {
            tool: {**entry, "rate": round(entry["successes"] / entry["attempts"], 3)}
            for tool, entry in sorted(self.tool_stats.items())[:8] if entry["attempts"]
        }
        data["capabilities"] = {
            name: {"regime": capability.regime, "available": capability.available(),
                   "description": capability.description}
            for name, capability in sorted(self.capabilities.items())
        }
        data["state_path"] = self.field.path
        return data
