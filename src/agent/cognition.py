"""
The substrate's tool surface: what a task can actually call.

Kept apart from `tools.py` so the cognitive architecture stays readable as its
own thing. Every handler here returns a `ToolResult` like any other tool, and
every one of them is a thin, honest wrapper: `build` composes a structure,
`execute` runs it (analysis for real, execution only when allowed), `restructure`
rebuilds it after an observation, `phase` reports the regime decision, `world`
reads and writes the generative memory, `predict` runs the counterfactual engine,
`resources` routes a requirement, `benchmark` measures the four research goals.

The last structure built in this process is kept here, so `execute` and
`restructure` can continue it without the caller having to pass it back.
"""

import json
from typing import Any, Dict, List, Optional

from src.agent import benchmark, counterfactual, phases, resources, substrate
from src.agent.tools import ToolResult, _payload_result
from src.agent.worldmodel import WorldModel

_CURRENT: Dict[str, Optional[substrate.Substrate]] = {"structure": None}


def _world(world_path: str = "") -> WorldModel:
    return WorldModel(world_path or None)


def _current_or_new(goal: str, world: Optional[WorldModel]) -> substrate.Substrate:
    if _CURRENT["structure"] is not None and not goal:
        return _CURRENT["structure"]
    structure = substrate.generate(goal, world=world)
    _CURRENT["structure"] = structure
    return structure


def substrate_tool(action: str = "build", goal: str = "", limit: int = 12,
                   allow_execution: bool = False, command: str = "",
                   observation: str = "", world_path: str = "") -> ToolResult:
    """Compose, inspect, run or rebuild a problem's cognitive structure."""
    action = (action or "build").lower()
    world = _world(world_path)

    if action in ("stats", "primitives", "catalog"):
        return _payload_result(substrate.stats())

    if action in ("last", "show"):
        current = _CURRENT["structure"]
        if current is None:
            return _payload_result({"last": substrate.last(),
                                    "note": "nothing has been built in this process yet"})
        return _payload_result({"structure": current.to_dict(), "last_result": substrate.last()})

    if not goal and action in ("build", "generate"):
        return ToolResult(False, error="a goal is required to build a structure")

    if action in ("build", "generate", "characterize"):
        signals = substrate.characterize(goal)
        structure = substrate.generate(goal, signals, world=world)
        _CURRENT["structure"] = structure
        payload = structure.to_dict()
        payload["note"] = (f"composed {len(structure.nodes)} primitives for a "
                           f"{signals['klass']} problem; nothing has run yet")
        return _payload_result(payload)

    if action in ("execute", "run"):
        structure = _current_or_new(goal, world)
        if goal and structure.goal != goal:
            structure = substrate.generate(goal, world=world)
            _CURRENT["structure"] = structure
        result = substrate.execute(structure, limit=int(limit or 12),
                                   allow_execution=bool(allow_execution), world=world,
                                   command=command)
        return _payload_result({"execution": result, "structure": structure.to_dict()})

    if action == "restructure":
        structure = _CURRENT["structure"]
        if structure is None:
            return ToolResult(False, error="nothing to restructure - build one first")
        try:
            obs = json.loads(observation) if observation.strip().startswith("{") else \
                {"kind": observation or "evidence"}
        except ValueError as exc:
            return ToolResult(False, error=f"observation is not JSON: {exc}")
        rebuilt = substrate.restructure(structure, obs)
        _CURRENT["structure"] = rebuilt
        return _payload_result({"structure": rebuilt.to_dict(),
                                "transition": rebuilt.history[-1]})

    return ToolResult(False, error=f"unknown substrate action: {action}")


def phase_tool(action: str = "status", budget: float = 24.0, spend: float = 0.0,
               contradictions: int = 0, progress: str = "") -> ToolResult:
    """The regime the system is in, and what would move it."""
    structure = _CURRENT["structure"]
    state = structure.state() if structure is not None else {}
    series: List[float] = []
    if progress.strip():
        try:
            series = [float(part) for part in progress.replace(" ", "").split(",") if part]
        except ValueError:
            return ToolResult(False, error="progress must be comma-separated numbers")

    if action == "decide":
        metrics = phases.measure(state, contradictions=int(contradictions),
                                 budget=float(budget or 24.0), spend=float(spend or 0.0),
                                 progress=series or None)
        return _payload_result({"metrics": metrics, "decision": phases.decide(metrics)})

    controller = phases.PhaseController((structure.regime if structure else "explore"),
                                        float(budget or 24.0))
    record = controller.step(state, contradictions=int(contradictions),
                             spend=float(spend or 0.0), progress=series or None)
    if structure is not None:
        structure.regime = controller.regime
    return _payload_result({"transition": record, "state": controller.state(),
                            "regimes": list(phases.REGIMES),
                            "thresholds": phases.THRESHOLDS})


def world_tool(action: str = "stats", concepts: str = "", outcome: str = "", klass: str = "",
               strategy: str = "", source: str = "", target: str = "", kind: str = "",
               prediction_id: int = 0, limit: int = 10, world_path: str = "") -> ToolResult:
    """The generative memory: observe, generate hypotheses, confirm, measure."""
    action = (action or "stats").lower()
    world = _world(world_path)

    if action == "stats":
        return _payload_result(world.stats())
    if action in ("strategies", "procedures"):
        return _payload_result({"strategies": world.strategies(klass or None, limit=int(limit)),
                                "preferred": world.prefer_strategy(klass) if klass else None})
    if action == "observe":
        names = [part.strip() for part in concepts.split(",") if part.strip()]
        if not names:
            return ToolResult(False, error="concepts is required (comma-separated)")
        return _payload_result(world.observe(names, outcome or "unknown", klass=klass or "unknown",
                                             strategy=strategy, context=source))
    if action == "associate":
        if not source or not target:
            return ToolResult(False, error="source and target are required")
        return _payload_result(world.associate(source, target, kind or "relates_to"))
    if action in ("hypotheses", "generate", "predict"):
        if not source:
            return ToolResult(False, error="source (the concept) is required")
        return _payload_result({"concept": source,
                                "hypotheses": world.generate_hypotheses(source, int(limit or 5)),
                                "note": "generated from learned tendencies - unverified until "
                                        "confirmed against an observation"})
    if action == "confirm":
        if not prediction_id:
            return ToolResult(False, error="prediction_id is required")
        return _payload_result(world.confirm(int(prediction_id), outcome or "unknown", source))
    if action in ("predictions", "pending"):
        return _payload_result({"predictions": world.predictions(None, int(limit or 20))})
    if action == "neighbors":
        return _payload_result({"relations": world.neighbors(source, int(limit or 10))})
    if action == "forget":
        return _payload_result(world.forget(source or None))
    return ToolResult(False, error=f"unknown world action: {action}")


def predict_tool(action: str = "rank", hypotheses: str = "", candidates: str = "",
                 goal: str = "") -> ToolResult:
    """Compare possible worlds before entering one."""
    action = (action or "rank").lower()
    live: List[Dict[str, Any]] = []
    if hypotheses.strip():
        try:
            live = json.loads(hypotheses)
        except ValueError as exc:
            return ToolResult(False, error=f"hypotheses must be a JSON array: {exc}")
    elif _CURRENT["structure"] is not None:
        live = _CURRENT["structure"].hypotheses
    if not live:
        return ToolResult(False, error="no hypotheses to work with - pass a JSON array or build "
                                       "a substrate first")

    plans: List[counterfactual.Candidate] = []
    if candidates.strip():
        try:
            for entry in json.loads(candidates):
                plans.append(counterfactual.Candidate(
                    label=entry.get("label", "candidate"), kind=entry.get("kind", "command"),
                    payload=entry.get("payload", ""), cost=float(entry.get("cost", 1.0)),
                    risk=float(entry.get("risk", 0.0))))
        except (ValueError, AttributeError, TypeError) as exc:
            return ToolResult(False, error=f"candidates must be a JSON array of objects: {exc}")
    elif _CURRENT["structure"] is not None:
        plans = _CURRENT["structure"].candidates
    if not plans:
        return ToolResult(False, error="no candidate actions - pass a JSON array or build a "
                                       "substrate first")

    if action == "simulate":
        return _payload_result(counterfactual.simulate(plans, live))
    if action == "choose":
        return _payload_result(counterfactual.choose_experiment(plans, live))
    return _payload_result({"ranked": counterfactual.rank(plans, live)})


def resources_tool(action: str = "list", requirement: str = "", name: str = "", ok: bool = True,
                   cost: float = 0.0) -> ToolResult:
    """What the substrate can compute with, and how a requirement is routed."""
    action = (action or "list").lower()
    if action in ("list", "inventory"):
        return _payload_result({"resources": resources.inventory()})
    if action in ("route", "plan"):
        if not requirement:
            return ToolResult(False, error="a requirement is required to route anything")
        routing = resources.route(requirement)
        notes = routing.pop("_by_name", {})
        return _payload_result({**routing, "resource_notes": notes})
    if action == "record":
        if not name:
            return ToolResult(False, error="name is required")
        return _payload_result(resources.record(name, bool(ok), float(cost or 0.0)))
    if action == "stats":
        return _payload_result(resources.stats())
    return ToolResult(False, error=f"unknown resources action: {action}")


def benchmark_tool(action: str = "summary", root: str = "", world_path: str = "") -> ToolResult:
    """Measure the four research goals against the fixed-loop baseline."""
    action = (action or "summary").lower()
    if action == "run":
        report = benchmark.run(root=root or None, world_path=world_path or None)
        return _payload_result(report)
    report = benchmark.run(root=root or None, world_path=world_path or None)
    return _payload_result({"verdicts": report["verdicts"],
                            "metrics": report["metrics"],
                            "caveats": report["caveats"]})
