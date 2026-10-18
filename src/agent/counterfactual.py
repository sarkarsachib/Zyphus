"""
Counterfactual reality engine: compare possible worlds before entering one.

Before touching anything, the substrate proposes candidate actions and predicts
what each would do - using measurements, not narration. A proposed patch is
parsed and its footprint read off the real import graph (which modules depend on
what it touches); a proposed command contributes its cost and a risk reading
based on what it does to the system. Nothing here executes: `predict` reads and
reasons, and every prediction is labelled a prediction until an observation
arrives.

Given competing hypotheses, `choose_experiment` picks the action that actually
separates them - the one with the largest expected drop in hypothesis entropy per
unit of cost. Paths that cannot tell the candidates apart are discarded and
reported with the reason, so nothing is spent on them.
"""

import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agent import analysis

# Commands that change the machine rather than read it. A prediction, not a
# verdict: it only shapes which path is tried first.
_MUTATING = re.compile(r"\b(rm|mv|dd|truncate|drop|delete|kill|chmod|chown|sudo|apt|pip\s+install|"
                       r"npm\s+install|git\s+(push|reset|clean|checkout))\b", re.IGNORECASE)


@dataclass
class Candidate:
    """One possible world: an action the substrate could take."""

    label: str
    kind: str                      # patch | command | query | probe
    payload: str = ""
    cost: float = 1.0
    risk: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"label": self.label, "kind": self.kind, "payload": self.payload,
                "cost": self.cost, "risk": self.risk, "notes": self.notes}


def predict(candidate: Candidate, graph: Optional[Dict[str, Any]] = None,
            root: Optional[str] = None) -> Dict[str, Any]:
    """What this action would touch, and what that would cost - before running it."""
    effects: List[str] = []
    blast = {"count": 0, "dependents": []}
    touch: Dict[str, Any] = {"files": [], "touched": [], "added_lines": 0, "removed_lines": 0}
    cost = float(candidate.cost)

    if candidate.kind == "patch":
        touch = analysis.diff_touch(candidate.payload)
        # patch paths are repo-relative: resolve them against the root being analysed
        resolved = [f if os.path.isabs(f) else os.path.join(root or analysis.REPO_ROOT, f)
                    for f in touch["files"]]
        modules = [analysis.module_name(f, root) for f in resolved if f.endswith(".py")]
        blast = analysis.blast_radius(modules, graph or analysis.import_graph(root))
        cost = max(cost, 0.5 + 0.1 * (touch["added_lines"] + touch["removed_lines"]))
        risk = min(1.0, 0.15 + 0.1 * blast["count"] + 0.02 * len(touch["touched"]))
        effects.append(f"touches {len(touch['touched'])} symbol(s) across {len(touch['files'])} file(s)")
        if blast["count"]:
            effects.append(f"{blast['count']} module(s) depend on what it changes")
        if not touch["files"]:
            effects.append("no file headers in the patch - the target is unclear")
    elif candidate.kind == "command":
        mutating = bool(_MUTATING.search(candidate.payload))
        risk = 0.7 if mutating else 0.1
        cost = max(cost, 2.0 if mutating else 1.0)
        effects.append("changes the machine" if mutating else "reads state only")
        effects.append(f"would run: {candidate.payload.strip()[:120]}")
    elif candidate.kind == "query":
        cost = max(cost, 0.5)
        risk = 0.05
        effects.append("retrieves existing evidence, changes nothing")
    else:
        effects.append("inspects without changing anything")
        risk = max(candidate.risk, 0.05)

    return {
        "label": candidate.label,
        "kind": candidate.kind,
        "cost": round(cost, 3),
        "risk": round(min(1.0, max(risk, candidate.risk)), 3),
        "files": touch["files"] if candidate.kind == "patch" else [],
        "touched": touch["touched"] if candidate.kind == "patch" else [],
        "predicted_effects": effects,
        "blast_radius": blast["count"],
        "dependents": blast["dependents"][:10],
        "verified": False,
        "note": "prediction from static analysis - must be confirmed by an observation",
    }


def _weights(hypotheses: List[Dict[str, Any]]) -> List[float]:
    return [float(h.get("score", h.get("confidence", 0.5)) or 0.0) for h in hypotheses]


def _normalized(values: List[float]) -> List[float]:
    total = sum(max(0.0, v) for v in values)
    if total <= 0:
        return [1.0 / len(values)] * len(values) if values else []
    return [max(0.0, v) / total for v in values]


def entropy(values: List[float]) -> float:
    out = 0.0
    for value in _normalized(values):
        if value > 0:
            out -= value * math.log2(value)
    return round(out, 4)


def expected_information(candidate: Candidate, hypotheses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """How much this action would tell us, given what each hypothesis predicts.

    A hypothesis states, per candidate label, which branch it expects
    (`predicts[label] = "fails"`). Running the action sorts the hypotheses into
    those branches, so the expected entropy after the test is the weighted
    entropy of the branches. Hypotheses that make no prediction for this action
    stay consistent with every branch, which is exactly why an uninformative
    action scores zero.
    """
    live = [h for h in hypotheses if float(h.get("score", h.get("confidence", 0.5)) or 0.0) > 0]
    if not live:
        return {"gain": 0.0, "branches": {}, "separates": [], "reason": "no live hypotheses"}

    before = entropy(_weights(live))
    branches: Dict[str, List[Dict[str, Any]]] = {}
    explicit: List[str] = []
    for hypothesis in live:
        predicted = (hypothesis.get("predicts") or {}).get(candidate.label)
        if predicted is None:
            continue
        explicit.append(str(hypothesis.get("id") or hypothesis.get("claim", "")))
        branches.setdefault(str(predicted), []).append(hypothesis)

    if len(branches) < 2:
        return {"gain": 0.0, "branches": {k: len(v) for k, v in branches.items()},
                "separates": [], "before": before,
                "reason": f"{candidate.label} does not split the live hypotheses"}

    total = sum(sum(_weights(group)) for group in branches.values())
    after = 0.0
    for group in branches.values():
        weight = sum(_weights(group)) / total if total else 0.0
        after += weight * entropy(_weights(group))
    gain = max(0.0, before - after)
    return {
        "gain": round(gain, 4),
        "before": before,
        "after": round(after, 4),
        "branches": {k: len(v) for k, v in sorted(branches.items())},
        "separates": sorted(explicit),
    }


def rank(candidates: List[Candidate], hypotheses: List[Dict[str, Any]],
         graph: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Score every candidate: information per unit of cost, discounted by risk."""
    ranked: List[Dict[str, Any]] = []
    for candidate in candidates:
        forecast = predict(candidate, graph)
        info = expected_information(candidate, hypotheses)
        cost = max(0.1, forecast["cost"])
        value = round(info["gain"] / cost * (1.0 - 0.5 * forecast["risk"]), 4)
        ranked.append({**forecast, **info, "expected_value": value,
                       "cost_per_bit": round(cost / info["gain"], 3) if info["gain"] else None})
    return sorted(ranked, key=lambda item: (-item["expected_value"], item["cost"], item["label"]))


def choose_experiment(candidates: List[Candidate], hypotheses: List[Dict[str, Any]],
                      graph: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The action worth spending resources on, and why the others are not."""
    live = [h for h in hypotheses if float(h.get("score", h.get("confidence", 0.5)) or 0.0) > 0]
    if not live:
        return {"chosen": None, "discarded": [],
                "reason": "no live hypotheses to separate - there is nothing worth running yet"}
    scored = rank(candidates, hypotheses, graph)
    if not scored:
        return {"chosen": None, "discarded": [], "reason": "no candidate actions were proposed"}
    best = scored[0]
    discarded = [
        {"label": item["label"], "reason": (
            "cannot separate any hypothesis" if not item["gain"]
            else f"same information for {item['cost']} cost" if item["cost"] > best["cost"]
            else f"risk {item['risk']:.2f} outweighs {item['gain']:.2f} bits"
        )}
        for item in scored[1:]
    ]
    return {
        "chosen": best,
        "discarded": discarded,
        "reason": (f"{best['label']} separates {len(best['separates'])} hypothesis(es) for "
                   f"{best['cost']} cost: {best['gain']} bits of uncertainty removed"),
        "hypotheses_considered": len(hypotheses),
    }


def simulate(plan: List[Candidate], hypotheses: List[Dict[str, Any]],
             graph: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compare the possible worlds a plan opens, cheapest informative first."""
    ranked = rank(plan, hypotheses, graph)
    return {
        "worlds": ranked,
        "recommended_order": [item["label"] for item in ranked],
        "discarded_before_execution": [item["label"] for item in ranked if not item["gain"]],
        "total_predicted_cost": round(sum(item["cost"] for item in ranked), 2),
        "note": "predictions only - every one of these still has to be confirmed by running it",
    }
