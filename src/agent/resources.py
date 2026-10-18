"""
A cognitive substrate, not a model wrapper.

The intelligence is meant to be the composition, so what a question needs is
decided before anything answers it. Each available resource carries what it is
actually good at: the Python interpreter for formal work, the retrieval index
for recall, the container's shell and the test suite for verification, the
configured model endpoints for language and ambiguity, HTTP for the outside
world, the fusion engine for coordinating several model answers.

`route` maps a requirement onto the resources that can serve it, ordered by
measured reliability first and cost second - and its measured numbers come from
real runs (`record`), so a resource that keeps failing stops being picked.
`coordinate` says *how* the picks work together: a deterministic gate in front
of a model, a fusion across several models, or a chain. That is what Superfusing
becomes here - not the same question asked of several models, but different
kinds of computation composed for one requirement.
"""

import json
import os
import sys
import threading
from typing import Any, Dict, List, Optional

from src.agent import config

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATS_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "resources.json")

KINDS = ("deterministic", "retrieval", "execution", "model", "external")

# What each capability sounds like in a requirement.
CAPABILITY_WORDS = {
    "calculation": ("calculate", "compute", "count", "sum", "convert", "parse", "validate",
                    "compare numbers", "sort", "formula", "how many", "difference"),
    "verification": ("test", "verify", "check", "reproduce", "confirm", "benchmark", "measure",
                     "does it work", "run it", "assert"),
    "recall": ("where", "which file", "find", "documented", "history", "recall", "search",
               "previously", "look up", "mentioned"),
    "ambiguity": ("why", "explain", "summarize", "design", "propose", "write", "brainstorm",
                  "interpret", "should", "feel", "unclear", "ambiguous", "how might"),
    "external": ("http", "api", "url", "web", "fetch", "download", "endpoint", "webhook"),
}

_lock = threading.Lock()


def _load() -> Dict[str, Any]:
    if not os.path.isfile(STATS_PATH):
        return {}
    try:
        with open(STATS_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
    with open(STATS_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def record(name: str, ok: bool, cost: float = 0.0, kind: str = "") -> Dict[str, Any]:
    """Remember how a resource actually performed. This is what reorders routing."""
    with _lock:
        data = _load()
        entry = data.setdefault(name, {"attempts": 0, "successes": 0, "cost": 0.0, "kind": kind})
        entry["attempts"] += 1
        entry["successes"] += 1 if ok else 0
        entry["cost"] = round(float(entry.get("cost", 0.0)) + float(cost or 0.0), 3)
        if kind:
            entry["kind"] = kind
        _save(data)
    return reliability(name)


def reliability(name: str) -> Dict[str, Any]:
    entry = _load().get(name)
    if not entry or not entry.get("attempts"):
        return {"resource": name, "attempts": 0, "successes": 0, "rate": None,
                "note": "no measured runs yet"}
    return {"resource": name, "attempts": entry["attempts"], "successes": entry["successes"],
            "rate": round(entry["successes"] / entry["attempts"], 3)}


def _model_resources() -> List[Dict[str, Any]]:
    """Configured model endpoints, plus whatever is reachable without one."""
    out: List[Dict[str, Any]] = []
    for entry in config.models():
        key_env = entry.get("api_key_env") or ""
        available = config.env_present(key_env) if key_env else True
        out.append({
            "name": f"model:{entry.get('name')}",
            "kind": "model",
            "cost": 4.0,
            "strengths": ["ambiguity", "synthesis"],
            "available": available,
            "note": f"{entry.get('model') or 'model'} at {entry.get('base_url') or '?'}"
                    + ("" if available else f" (needs {key_env})"),
        })
    return out


def inventory() -> List[Dict[str, Any]]:
    """Everything the substrate can compute with, and whether it is usable now."""
    from src.agent import rag  # imported late: reading the index must never be required

    index = rag.stats()
    entries: List[Dict[str, Any]] = [
        {"name": "python-eval", "kind": "deterministic", "cost": 0.5,
         "strengths": ["calculation"], "available": True,
         "note": f"{sys.version.split()[0]} in the container"},
        {"name": "static-analysis", "kind": "deterministic", "cost": 1.0,
         "strengths": ["structure", "dependency", "measurement"], "available": True,
         "note": "AST over the repository: imports, symbols, patch footprint"},
        {"name": "deliberative-planner", "kind": "deterministic", "cost": 0.5,
         "strengths": ["ambiguity", "structure"], "available": True,
         "note": "local planner in src/agent/brain.py"},
        {"name": "rag-index", "kind": "retrieval", "cost": 1.0,
         "strengths": ["recall"], "available": bool(index.get("chunks")),
         "note": f"{index.get('chunks', 0)} chunks indexed"
                 + ("" if index.get("chunks") else " - empty, run `rag: index src`")},
        {"name": "container-shell", "kind": "execution", "cost": 3.0,
         "strengths": ["verification", "measurement"], "available": True,
         "note": "real commands in the container"},
        {"name": "test-suite", "kind": "execution", "cost": 4.0,
         "strengths": ["verification"], "available": os.path.isdir(
             os.path.join(REPO_ROOT, "tests")),
         "note": "pytest over tests/"},
        {"name": "http-request", "kind": "external", "cost": 2.0,
         "strengths": ["external"], "available": True, "note": "any host, any method"},
        {"name": "fusion-engine", "kind": "deterministic", "cost": 1.0,
         "strengths": ["coordination"], "available": True,
         "note": "weighted consensus over model answers (src/agent/fusion.py)"},
    ]
    entries.extend(_model_resources())
    for entry in entries:
        entry["measured"] = reliability(entry["name"])
    return entries


def classify(requirement: str) -> List[str]:
    """Which capabilities a requirement actually asks for."""
    low = (requirement or "").lower()
    return [capability for capability, words in CAPABILITY_WORDS.items()
            if any(word in low for word in words)]


def route(requirement: str, capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
    """Pick and order the resources for a requirement, and say how they combine."""
    wanted = capabilities or classify(requirement) or ["structure"]
    catalogue = inventory()
    by_name = {entry["name"]: entry for entry in catalogue}
    picks: List[Dict[str, Any]] = []
    unmet: List[str] = []

    for capability in wanted:
        candidates = [entry for entry in catalogue
                      if capability in entry["strengths"] and entry["available"]]
        if not candidates:
            blocked = [entry for entry in catalogue if capability in entry["strengths"]]
            unmet.append({
                "capability": capability,
                "would_serve": [entry["name"] for entry in blocked],
                "enable": "; ".join(entry["note"] for entry in blocked)
                          or "nothing in the catalogue serves this capability",
            })
            continue
        candidates.sort(key=lambda entry: (
            -(entry["measured"]["rate"] if entry["measured"]["rate"] is not None else 0.5),
            entry["cost"], entry["name"]))
        chosen = candidates[0]
        rate = chosen["measured"]["rate"]
        picks.append({
            "capability": capability,
            "resource": chosen["name"],
            "kind": chosen["kind"],
            "cost": chosen["cost"],
            "reason": (f"measured rate {rate}" if rate is not None else "no measured runs yet")
                      + f", cost {chosen['cost']}",
            "measured": chosen["measured"],
        })

    if not picks:
        fallback = next((entry for entry in catalogue
                         if entry["name"] == "static-analysis" and entry["available"]), None)
        if fallback is not None:
            picks.append({
                "capability": "structure",
                "resource": fallback["name"],
                "kind": fallback["kind"],
                "cost": fallback["cost"],
                "reason": "no available resource matched the requirement - measuring instead of "
                          "answering blind",
                "measured": fallback["measured"],
            })

    coordination = coordinate(picks)
    return {
        "requirement": requirement,
        "capabilities": wanted,
        "picks": picks,
        "unmet_capabilities": unmet,
        "coordination": coordination,
        "resources_available": len([e for e in catalogue if e["available"]]),
        "note": "routing decision only - nothing has been called",
        "_by_name": {name: by_name[name]["note"] for name in
                     [p["resource"] for p in picks] if name in by_name},
    }


def coordinate(picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """How the picked resources should work together."""
    kinds = [pick["kind"] for pick in picks]
    models = [pick for pick in picks if pick["kind"] == "model"]
    if len(models) > 1:
        return {"mode": "fuse",
                "why": f"{len(models)} model resources - fuse with the weighted-consensus engine",
                "engine": "src/agent/fusion.py"}
    if models and any(kind in ("deterministic", "execution") for kind in kinds):
        return {"mode": "gate",
                "why": "deterministic computation checks the model's answer before it is trusted"}
    if "retrieval" in kinds and models:
        return {"mode": "chain", "why": "retrieve evidence first, then let the model reason over it"}
    if len(picks) > 1:
        return {"mode": "chain", "why": "run the picks in order, feeding each result forward"}
    return {"mode": "single", "why": "one resource serves this requirement"}


def stats() -> Dict[str, Any]:
    """Inventory plus measured performance. Reading never writes."""
    data = _load()
    catalogue = inventory()
    return {
        "store": STATS_PATH,
        "kinds": list(KINDS),
        "available": [entry["name"] for entry in catalogue if entry["available"]],
        "unavailable": [{"name": entry["name"], "note": entry["note"]}
                        for entry in catalogue if not entry["available"]],
        "measured": [{"resource": name, **value} for name, value in sorted(data.items())],
    }


def usage() -> Dict[str, Any]:
    """Total measured calls and successes per resource."""
    data = _load()
    attempts = sum(entry.get("attempts", 0) for entry in data.values())
    successes = sum(entry.get("successes", 0) for entry in data.values())
    return {"calls": attempts, "successes": successes,
            "success_rate": round(successes / attempts, 3) if attempts else None}
