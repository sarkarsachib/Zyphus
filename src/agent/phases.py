"""
Intelligence phase transitions: one system, five computational regimes.

The same reasoning cycle is the wrong tool for every moment of a problem. This
module measures where a task actually stands - how uncertain the evidence is,
how far apart the leading hypotheses are, whether the last few moves changed
anything, how much budget is left - and moves the whole substrate into the
regime the measurement calls for:

  explore    the unknowns are not mapped yet: generate hypotheses
  converge   several candidates are live: narrow them with evidence
  execute    one candidate dominates and the claim is testable: act
  recover    progress stalled or evidence conflicts: change approach
  compress   the work is settled or the budget is nearly gone: distil it

Transitions are triggered by numbers, never by a schedule, and every
transition carries the measurements that caused it so it can be argued with.
"""

from typing import Any, Dict, List, Optional

REGIMES = ("explore", "converge", "execute", "recover", "compress")

# A transition happens when a measurement crosses one of these. They are
# deliberately explicit: change a number here and the behaviour changes.
THRESHOLDS = {
    "budget_spent": 0.90,      # remaining compute
    "contradictions": 2,       # conflicting pieces of evidence
    "stagnation": 3,           # consecutive steps with no measurable progress
    "certainty": 0.25,         # uncertainty low enough to commit
    "dominance": 0.35,         # margin between the two leading hypotheses
    "converging": 0.45,        # uncertainty low enough to narrow
}


def normalize(weights: List[float]) -> List[float]:
    total = sum(max(0.0, w) for w in weights)
    if total <= 0:
        return [1.0 / len(weights)] * len(weights) if weights else []
    return [max(0.0, w) / total for w in weights]


def entropy(weights: List[float]) -> float:
    """Shannon entropy of a weighting, in bits. One live candidate -> 0."""
    out = 0.0
    for value in normalize(weights):
        if value > 0:
            import math
            out -= value * math.log2(value)
    return round(out, 4)


def dominance(scores: List[float]) -> float:
    """How far the leading candidate is ahead of the runner-up, 0..1."""
    if not scores:
        return 0.0
    ordered = sorted(normalize(scores), reverse=True)
    if len(ordered) == 1:
        return 1.0
    return round(ordered[0] - ordered[1], 4)


def measure(substrate: Optional[Dict[str, Any]] = None, contradictions: int = 0,
            budget: float = 100.0, spend: float = 0.0,
            progress: Optional[List[float]] = None) -> Dict[str, Any]:
    """The numbers a regime decision is allowed to look at.

    `substrate` is a substrate as `to_dict()` reports it. `progress` is the score
    after each completed step - the stagnation counter is how many trailing steps
    failed to beat the best score seen so far.
    """
    hypotheses = list((substrate or {}).get("hypotheses") or [])
    scores = [float(h.get("score", h.get("confidence", 0.5)) or 0.0) for h in hypotheses]
    raw = (substrate or {}).get("uncertainty")
    uncertainty = 1.0 if raw is None else float(raw)
    if hypotheses:
        live = [s for s in scores if s > 0]
        uncertainty = round(min(1.0, entropy(live) / 2.0), 4) if len(live) > 1 else 0.15

    # Stagnation is how many trailing steps failed to beat the best score seen
    # before them - a step that improves the picture resets the counter.
    history = list(progress or [])
    stagnation = 0
    best: Optional[float] = None
    for value in history:
        if best is None or value > best + 1e-9:
            best = value
            stagnation = 0
        else:
            stagnation += 1

    budget = max(1.0, float(budget))
    spend = max(0.0, float(spend))
    return {
        "uncertainty": round(uncertainty, 4),
        "entropy": entropy(scores),
        "dominance": dominance(scores),
        "hypotheses": len(hypotheses),
        "contradictions": int(contradictions),
        "progress": round(history[-1], 4) if history else 0.0,
        "stagnation": stagnation,
        "budget": budget,
        "spend": spend,
        "budget_spent": round(spend / budget, 4),
        "testable": bool((substrate or {}).get("testable", False)),
    }


def decide(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Which regime the measurements call for, and why."""
    triggers: List[str] = []
    if metrics["budget_spent"] >= THRESHOLDS["budget_spent"]:
        triggers.append(f"budget {metrics['budget_spent']:.0%} spent")
        return {"regime": "compress", "reason": "budget nearly exhausted - distil what is known",
                "triggers": triggers}
    if metrics["contradictions"] >= THRESHOLDS["contradictions"]:
        triggers.append(f"{metrics['contradictions']} contradictory observations")
    if metrics["stagnation"] >= THRESHOLDS["stagnation"]:
        triggers.append(f"{metrics['stagnation']} steps without progress")
    if triggers:
        return {"regime": "recover", "reason": "evidence conflicts or progress stalled - change approach",
                "triggers": triggers}

    if (metrics["uncertainty"] <= THRESHOLDS["certainty"]
            and metrics["dominance"] >= THRESHOLDS["dominance"]):
        triggers.append(f"uncertainty {metrics['uncertainty']:.2f} <= {THRESHOLDS['certainty']}")
        triggers.append(f"dominance {metrics['dominance']:.2f} >= {THRESHOLDS['dominance']}")
        if metrics["testable"]:
            return {"regime": "execute", "reason": "a dominant hypothesis can be tested directly",
                    "triggers": triggers}
        return {"regime": "converge", "reason": "leading hypothesis is ahead but nothing is testable yet",
                "triggers": triggers}

    if metrics["uncertainty"] <= THRESHOLDS["converging"]:
        triggers.append(f"uncertainty {metrics['uncertainty']:.2f} <= {THRESHOLDS['converging']}")
        return {"regime": "converge", "reason": "enough evidence to start narrowing", "triggers": triggers}

    triggers.append(f"uncertainty {metrics['uncertainty']:.2f} above {THRESHOLDS['converging']}")
    return {"regime": "explore", "reason": "the unknowns are not mapped yet", "triggers": triggers}


class PhaseController:
    """Tracks the regime a substrate is in and records every transition."""

    def __init__(self, regime: str = "explore", budget: float = 100.0):
        self.regime = regime if regime in REGIMES else "explore"
        self.budget = budget
        self.history: List[Dict[str, Any]] = []

    def step(self, substrate: Optional[Dict[str, Any]] = None, contradictions: int = 0,
             spend: float = 0.0, progress: Optional[List[float]] = None) -> Dict[str, Any]:
        metrics = measure(substrate, contradictions=contradictions, budget=self.budget,
                          spend=spend, progress=progress)
        decision = decide(metrics)
        previous, self.regime = self.regime, decision["regime"]
        record = {
            "from": previous,
            "to": self.regime,
            "changed": previous != self.regime,
            "reason": decision["reason"],
            "triggers": decision["triggers"],
            "metrics": metrics,
        }
        self.history.append(record)
        return record

    def state(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "budget": self.budget,
            "transitions": len([r for r in self.history if r["changed"]]),
            "history": self.history[-10:],
        }
