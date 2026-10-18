"""
Measuring the claim instead of asserting it.

Four things are supposed to make this architecture different, so four things are
measured here, on a suite of problems, against a baseline that stands in for the
fixed loop: one pipeline for every problem.

  structural adaptability   do different problem classes really produce
                            materially different structures?
  experimental reasoning    does the chosen experiment actually carry more
                            information than the first idea that came up?
  learned procedural        does a world model with measured outcomes change how
      improvement           the next problem of that class is attacked?
  resource-aware            information gained per unit of compute, against the
      intelligence          baseline's fixed spend?

Every number comes from running the real modules. What these measurements can
and cannot show is stated plainly in `CAVEATS`, because a local benchmark is not
a claim about anyone else's system. The benchmark keeps its world model in a
temporary file, so a run never pollutes the agent's own learned state.
"""

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

from src.agent import counterfactual, phases, substrate
from src.agent.worldmodel import WorldModel

CAVEATS = [
    "measured locally, on this repository and a small synthetic suite - not a comparison "
    "against any external system",
    "a run's outcome is 'decisive' when it produced an experiment that separated its candidates, "
    "and 'observed' only when a real command was allowed to run; neither is a claim that the code "
    "under test passed",
    "structural and information metrics need no execution; success rates come only from what "
    "the agent actually observed and recorded",
    "the baseline models the fixed loop (one pipeline per problem), not any particular "
    "implementation of it",
    "a benchmark run uses a temporary world model, so it neither reads nor writes the agent's "
    "own learned state",
]

SUITE: List[Dict[str, str]] = [
    {"id": "debug-import", "klass": "debug",
     "goal": "why does src/agent/loop.py fail to import - find the cause"},
    {"id": "debug-tests", "klass": "debug",
     "goal": "which change broke the tests in tests/ - fix the failing test"},
    {"id": "research-pacing", "klass": "research",
     "goal": "why does the loop pace itself faster with a backlog - explain the evidence"},
    {"id": "research-index", "klass": "research",
     "goal": "how does the retrieval index rank chunks - understand the ranking"},
    {"id": "design-memory", "klass": "design",
     "goal": "design a memory layer; it must not slow the loop and must stay stdlib only"},
    {"id": "design-tool", "klass": "design",
     "goal": "design a new agent tool; it should be cheap and must not need the network"},
    {"id": "operate-health", "klass": "operate",
     "goal": "check the engine health and verify the build with the test suite"},
    {"id": "operate-bench", "klass": "operate",
     "goal": "benchmark the dashboard response time and measure it"},
]

# What the fixed loop does with every one of them.
BASELINE_PIPELINE = ["retrieve", "hypotheses", "compress"]


def baseline_signature() -> str:
    return "+".join(sorted(BASELINE_PIPELINE))


def baseline_cost() -> float:
    return round(sum(substrate.PRIMITIVES[name]["cost"] for name in BASELINE_PIPELINE), 2)


def _jaccard(left: List[str], right: List[str]) -> float:
    a, b = set(left), set(right)
    return round(1.0 - len(a & b) / max(1, len(a | b)), 4)


def _pass(suite: List[Dict[str, str]], root: str, world: WorldModel,
          remember: bool) -> List[Dict[str, Any]]:
    """Run the whole suite once. `remember` decides whether the world model seeds generation."""
    rows: List[Dict[str, Any]] = []
    for problem in suite:
        signals = substrate.characterize(problem["goal"], root)
        structure = substrate.generate(problem["goal"], signals, root=root,
                                       world=world if remember else None)
        initial_regime = structure.regime
        result = substrate.execute(structure, limit=max(8, len(structure.nodes)), root=root,
                                   world=world)
        ranked = structure.artifacts.get("ranked_actions") or []
        chosen = structure.chosen_experiment or {}
        gain_of = {item["label"]: item.get("gain", 0.0) for item in ranked}
        # the blind baseline is the first idea that came up, not the first of the ranking
        proposed = [candidate.label for candidate in structure.candidates]
        first_label = proposed[0] if proposed else ""
        rows.append({
            "id": problem["id"],
            "klass": signals["klass"],
            "signature": structure.signature(),
            "primitives": structure.primitive_names(),
            "nodes": len(structure.nodes),
            "hypotheses": len(structure.hypotheses),
            "chosen": chosen.get("label"),
            "chosen_gain": round(chosen.get("gain", 0.0), 4),
            "best_gain": round(max(gain_of.values()) if gain_of else 0.0, 4),
            "first_candidate_label": first_label,
            "first_candidate_gain": round(gain_of.get(first_label, 0.0), 4),
            "decisive": bool(chosen) and chosen.get("gain", 0.0) > 0,
            "spend": result["spend"],
            "initial_regime": initial_regime,
            "final_regime": result["regime"],
            "remembered": structure.node("recall_strategy") is not None,
            "budget": structure.budget,
        })
    return rows


def structural_adaptability(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    signatures = [row["signature"] for row in rows]
    distinct = sorted(set(signatures))
    distances = [_jaccard(left, right)
                 for index, left in enumerate(rows)
                 for right in rows[index + 1:]]
    classes = sorted({row["klass"] for row in rows})
    per_class = {}
    for klass in classes:
        per_class[klass] = sorted({row["signature"] for row in rows if row["klass"] == klass})
    return {
        "problems": len(rows),
        "distinct_structures": len(distinct),
        "baseline_distinct_structures": 1,
        "mean_pairwise_distance": round(sum(distances) / len(distances), 4) if distances else 0.0,
        "structures_per_class": per_class,
        "signatures": distinct,
    }


def experimental_reasoning(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Only problems with competing hypotheses can say anything about this.

    A single live hypothesis needs no experiment - there is nothing to tell apart -
    so it is excluded rather than counted as a zero.
    """
    contestable = [row for row in rows if row["hypotheses"] >= 2]
    chosen = [row["chosen_gain"] for row in contestable]
    first = [row["first_candidate_gain"] for row in contestable]
    decisive = [row for row in contestable if row["decisive"]]
    better = [row for row in contestable if row["chosen_gain"] > row["first_candidate_gain"]]
    return {
        "problems": len(rows),
        "problems_with_competing_hypotheses": len(contestable),
        "decisive_experiments": len(decisive),
        "baseline_decisive_experiments": 0,
        "mean_chosen_gain": round(sum(chosen) / len(chosen), 4) if chosen else 0.0,
        "mean_first_candidate_gain": round(sum(first) / len(first), 4) if first else 0.0,
        "problems_where_selection_beat_the_first_idea": len(better),
        "note": "gain is expected entropy removed from the live hypotheses (bits); only problems "
                "with two or more live hypotheses are counted",
    }


def learned_procedural_improvement(cold: List[Dict[str, Any]],
                                   warm: List[Dict[str, Any]],
                                   world: WorldModel) -> Dict[str, Any]:
    """Did measured outcomes change how the same class of problem is attacked?"""
    remembered = [row for row in warm if row["remembered"]]
    regime_shift = [row for row in warm if row["initial_regime"] != "explore"
                    and cold_by_id(cold, row["id"]) == "explore"]
    measured: List[Dict[str, Any]] = []
    for klass in sorted({row["klass"] for row in warm}):
        measured.extend(world.strategies(klass)[:2])
    return {
        "problems": len(warm),
        "attacked_from_remembered_knowledge": len(remembered),
        "regime_changed_by_experience": len(regime_shift),
        "strategies_measured": len(measured),
        "strategy_examples": measured[:4],
        "learning_rows": [{"id": row["id"],
                           "signature_before_learning": cold_signature(cold, row["id"]),
                           "signature_after_learning": row["signature"],
                           "signature_changed": (cold_signature(cold, row["id"])
                                                 != row["signature"]),
                           "remembered": row["remembered"]} for row in warm],
        "note": "a problem is 'attacked from remembered knowledge' when the world model's measured "
                "strategy for its class adds a recall node to its structure",
    }


def cold_by_id(cold: List[Dict[str, Any]], problem_id: str) -> Optional[str]:
    for row in cold:
        if row["id"] == problem_id:
            return row["initial_regime"]
    return None


def cold_signature(cold: List[Dict[str, Any]], problem_id: str) -> str:
    for row in cold:
        if row["id"] == problem_id:
            return row["signature"]
    return ""


def resource_awareness(rows: List[Dict[str, Any]], cold: List[Dict[str, Any]]) -> Dict[str, Any]:
    adaptive_spend = round(sum(row["spend"] for row in rows), 2)
    adaptive_spend_cold = round(sum(row["spend"] for row in cold), 2)
    baseline_spend = round(baseline_cost() * len(rows), 2)
    decisive = sum(1 for row in rows if row["decisive"])
    return {
        "adaptive_spend": adaptive_spend,
        "adaptive_spend_before_learning": adaptive_spend_cold,
        "baseline_spend": baseline_spend,
        "budget_respected": all(row["spend"] <= row["budget"] for row in rows),
        "decisive_per_100_cost": round(100.0 * decisive / adaptive_spend, 3) if adaptive_spend else 0.0,
        "baseline_decisive_per_100_cost": 0.0,
        "mean_spend": round(adaptive_spend / len(rows), 2) if rows else 0.0,
        "note": "cheap computation replaced expensive paths where the prediction allowed it; the "
                "baseline proposes no experiment, so it gains nothing per unit of compute",
    }


def run(suite: Optional[List[Dict[str, str]]] = None, root: Optional[str] = None,
        world_path: Optional[str] = None) -> Dict[str, Any]:
    """Run the suite twice - before and after the world model has measured outcomes."""
    suite = suite or SUITE
    root = root or substrate.REPO_ROOT
    world_path = world_path or os.path.join(tempfile.mkdtemp(prefix="zyphus-bench-"), "world.db")
    world = WorldModel(world_path)

    cold_rows = _pass(suite, root, world, remember=False)
    warm_rows = _pass(suite, root, world, remember=True)

    report = {
        "suite": [problem["id"] for problem in suite],
        "world_model": world_path,
        "baseline": {"pipeline": BASELINE_PIPELINE, "signature": baseline_signature(),
                     "cost_per_problem": baseline_cost()},
        "adaptive": warm_rows,
        "before_learning": cold_rows,
        "metrics": {
            "structural_adaptability": structural_adaptability(warm_rows),
            "experimental_reasoning": experimental_reasoning(warm_rows),
            "learned_procedural_improvement": learned_procedural_improvement(cold_rows, warm_rows, world),
            "resource_awareness": resource_awareness(warm_rows, cold_rows),
        },
        "caveats": CAVEATS,
    }
    report["verdicts"] = verdicts(report["metrics"])
    return report


def verdicts(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Each goal, with the number that decides it and an honest verdict."""
    structure = metrics["structural_adaptability"]
    reasoning = metrics["experimental_reasoning"]
    learning = metrics["learned_procedural_improvement"]
    resources = metrics["resource_awareness"]
    return {
        "structural_adaptability": {
            "holds": structure["distinct_structures"] > 1,
            "measure": f"{structure['distinct_structures']} distinct structures over "
                       f"{structure['problems']} problems (baseline 1)",
        },
        "experimental_reasoning": {
            "holds": reasoning["mean_chosen_gain"] > reasoning["mean_first_candidate_gain"],
            "measure": f"chosen {reasoning['mean_chosen_gain']} bits vs first idea "
                       f"{reasoning['mean_first_candidate_gain']} bits",
        },
        "learned_procedural_improvement": {
            "holds": learning["attacked_from_remembered_knowledge"] > 0,
            "measure": f"{learning['attacked_from_remembered_knowledge']} problem(s) attacked from "
                       f"measured experience, {learning['strategies_measured']} strategy row(s)",
        },
        "resource_awareness": {
            "holds": resources["decisive_per_100_cost"] > resources["baseline_decisive_per_100_cost"],
            "measure": f"{resources['decisive_per_100_cost']} decisive experiments per 100 compute "
                       f"for {resources['adaptive_spend']} spend (baseline 0 per 100)",
        },
    }


def summary(report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    report = report or run()
    return {"metrics": report["metrics"]["structural_adaptability"], "verdicts": report["verdicts"],
            "reasoning": report["metrics"]["experimental_reasoning"],
            "learning": report["metrics"]["learned_procedural_improvement"],
            "resources": report["metrics"]["resource_awareness"]}


if __name__ == "__main__":  # python -m src.agent.benchmark
    print(json.dumps(run(), indent=2, default=str))
