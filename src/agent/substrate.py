"""
Cognitive morphogenesis: the architecture grows around the problem.

A fixed reasoning loop treats a debugging task, a research question and a design
question the same way. This module builds a *different* structure for each: it
characterizes the problem (what is unknown, what is testable, which artifacts it
names, how much compute it deserves), derives the products the work must produce,
and composes a temporary computational graph out of reusable primitives - wiring
them by what each one consumes and produces, not by picking a workflow off a
shelf. Two problems of the same class with different signals get different
graphs, and `restructure` rebuilds the graph while the work is running when the
evidence says the current shape is wrong.

Execution is real: the analysis primitives run the repository's own AST
measurements, retrieval runs the local index, discrimination runs the
counterfactual engine, and `compress` writes what was learned into the world
model. An execution primitive never runs on its own initiative - it waits for an
explicit command, and until then it is reported as pending rather than pretended
to have happened.

Stdlib only. Predictions are labelled predictions until an observation confirms
them.
"""

import os
import re
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agent import analysis, counterfactual, phases, rag, resources
from src.agent.worldmodel import WorldModel

REPO_ROOT = analysis.REPO_ROOT

# ── the primitive catalog ────────────────────────────────────────────────────
# What the substrate can build from. `consumes`/`produces` are what the wiring
# follows; `required` are the inputs a primitive cannot work without.
PRIMITIVES: Dict[str, Dict[str, Any]] = {
    "scope_repo": {
        "kind": "deterministic", "cost": 1, "regime": "explore",
        "produces": ["repo_shape"], "consumes": ["hints"], "required": [],
        "description": "Walk the tree the goal points at"},
    "import_graph": {
        "kind": "deterministic", "cost": 1, "regime": "explore",
        "produces": ["dependency_graph"], "consumes": ["repo_shape"], "required": ["repo_shape"],
        "description": "Build the real import graph and find cycles"},
    "symbol_index": {
        "kind": "deterministic", "cost": 1, "regime": "explore",
        "produces": ["symbols"], "consumes": ["repo_shape"], "required": [],
        "description": "Index definitions and their locations"},
    "retrieve": {
        "kind": "retrieval", "cost": 2, "regime": "explore",
        "produces": ["evidence"], "consumes": ["hints"], "required": [],
        "description": "Pull the closest existing evidence out of the local index"},
    "evidence_graph": {
        "kind": "deterministic", "cost": 1, "regime": "explore",
        "produces": ["explanations"], "consumes": ["evidence"], "required": ["evidence"],
        "description": "Turn retrieved evidence into competing explanations"},
    "uncertainty": {
        "kind": "deterministic", "cost": 1, "regime": "explore",
        "produces": ["uncertainty"], "consumes": ["evidence", "repo_shape"], "required": [],
        "description": "Measure how much of the goal the evidence actually covers"},
    "hypotheses": {
        "kind": "deterministic", "cost": 2, "regime": "explore",
        "produces": ["hypotheses"],
        "consumes": ["uncertainty", "dependency_graph", "symbols", "explanations",
                     "remembered_approach"],
        "required": ["uncertainty"],
        "description": "Generate the candidate explanations to work against"},
    "constraint_space": {
        "kind": "deterministic", "cost": 2, "regime": "explore",
        "produces": ["constraints"], "consumes": ["hints"], "required": [],
        "description": "Extract the constraints and requirements the goal states"},
    "design_search": {
        "kind": "deterministic", "cost": 3, "regime": "converge",
        "produces": ["designs"], "consumes": ["constraints"], "required": ["constraints"],
        "description": "Explore designs that satisfy different constraint subsets"},
    "counterfactual": {
        "kind": "simulation", "cost": 2, "regime": "converge",
        "produces": ["ranked_actions"], "consumes": ["hypotheses", "dependency_graph"],
        "required": ["hypotheses"],
        "description": "Predict what each candidate action would do, before doing it"},
    "discriminate": {
        "kind": "simulation", "cost": 1, "regime": "converge",
        "produces": ["experiment"], "consumes": ["hypotheses", "ranked_actions"],
        "required": ["ranked_actions"],
        "description": "Choose the action that separates the live hypotheses"},
    "execute_test": {
        "kind": "execution", "cost": 5, "regime": "execute",
        "produces": ["observation"], "consumes": ["experiment"], "required": ["experiment"],
        "description": "Run the chosen test for real and read what happens"},
    "fuse_resources": {
        "kind": "model", "cost": 3, "regime": "converge",
        "produces": ["synthesis"], "consumes": ["explanations"], "required": [],
        "description": "Coordinate heterogeneous computation for an ambiguous goal"},
    "compress": {
        "kind": "deterministic", "cost": 1, "regime": "compress",
        "produces": ["knowledge"], "consumes": ["observation", "designs", "synthesis", "hypotheses"],
        "required": [],
        "description": "Distil the outcome into the world model"},
    "recall_strategy": {
        "kind": "deterministic", "cost": 1, "regime": "converge",
        "produces": ["remembered_approach"], "consumes": [], "required": [],
        "description": "Start from what this class of problem responded to before"},
}

CLASS_WORDS = {
    "debug": ("bug", "error", "fail", "failure", "broken", "crash", "traceback", "exception",
              "regression", "fix", "stuck", "hangs", "not working"),
    "research": ("why", "how does", "explain", "understand", "compare", "evidence", "hypothesis",
                 "investigate", "research", "what causes", "figure out"),
    "design": ("design", "build", "add", "implement", "create", "architecture", "refactor",
               "propose", "should we", "options", "approach", "new"),
    "operate": ("run", "deploy", "status", "check", "verify", "test", "benchmark", "monitor",
                "measure", "health", "performance"),
}
VAGUE = ("maybe", "probably", "somehow", "unclear", "not sure", "kind of", "roughly", "might",
         "seems", "somewhat")
QUESTION_WORDS = ("what", "why", "how", "which", "where", "when", "who", "unknown", "unclear")
HINT = re.compile(r"[\w./-]+\.(?:py|js|mjs|md|json|html|txt|ya?ml|toml|css|db)\b")
DIR_HINT = re.compile(r"(?<![\w./-])(src|web|tests|docs|devmind|nishkraman)(?:/[\w./-]+)*")
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{3,}")

_lock = threading.Lock()
_LAST: Dict[str, Any] = {}


# ── characterization ─────────────────────────────────────────────────────────

def _hints(goal: str) -> List[str]:
    found: List[str] = []
    for match in HINT.findall(goal or ""):
        if match not in found:
            found.append(match)
    for match in DIR_HINT.findall(goal or ""):
        if match not in found:
            found.append(match)
    return found[:8]


def characterize(goal: str, root: Optional[str] = None) -> Dict[str, Any]:
    """What kind of problem this is, and what it demands.

    Purely textual plus one real filesystem check: which of the paths the goal
    names actually exist.
    """
    text = (goal or "").strip()
    low = text.lower()
    scores = {klass: sum(1 for word in words if word in low) for klass, words in CLASS_WORDS.items()}
    best = max(scores.values()) if scores else 0
    klass = "unknown"
    if best:
        klass = [name for name, score in scores.items() if score == best][0]

    hints = _hints(text)
    root = root or REPO_ROOT
    existing = [hint for hint in hints
                if os.path.isfile(os.path.join(root, hint)) or os.path.isdir(os.path.join(root, hint))]

    unknowns = sum(1 for word in QUESTION_WORDS if word in low)
    vague = sum(1 for word in VAGUE if word in low)
    cost_sensitive = any(word in low for word in ("quick", "cheap", "fast", "minimal", "budget",
                                                  "as cheap", "don't spend"))
    testable = bool(existing) or any(word in low for word in (
        "test", "run", "verify", "check", "reproduce", "measure", "benchmark", "health"))
    return {
        "klass": klass,
        "class_scores": scores,
        "unknowns": unknowns,
        "ambiguity": round(min(1.0, vague / 4.0), 3),
        "vague_markers": vague,
        "hints": hints,
        "existing_artifacts": existing,
        "testable": testable,
        "cost_sensitive": cost_sensitive,
        "budget": 16.0 if cost_sensitive else 24.0,
        "tokens": sorted(set(TOKEN.findall(low)))[:40],
    }


def required_products(signals: Dict[str, Any]) -> List[str]:
    """The products this problem needs before it can be settled."""
    klass = signals.get("klass", "unknown")
    products = ["evidence", "uncertainty", "hypotheses", "ranked_actions", "experiment", "knowledge"]
    if klass in ("debug", "operate") or signals.get("existing_artifacts"):
        products += ["repo_shape", "dependency_graph"]
    if klass == "debug":
        products += ["symbols", "explanations"]
    elif klass == "research":
        products += ["explanations"]
    elif klass == "design":
        products += ["constraints", "designs"]
    if signals.get("ambiguity", 0.0) >= 0.25:
        products += ["synthesis"]
    if signals.get("testable"):
        products += ["observation"]
    return products


# ── the substrate ────────────────────────────────────────────────────────────

@dataclass
class Substrate:
    """One problem's temporary cognitive structure."""

    goal: str
    klass: str = "unknown"
    signals: Dict[str, Any] = field(default_factory=dict)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[List[str]] = field(default_factory=list)
    budget: float = 24.0
    spend: float = 0.0
    revision: int = 0
    regime: str = "explore"
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    chosen_experiment: Optional[Dict[str, Any]] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def primitive_names(self) -> List[str]:
        return sorted(node["primitive"] for node in self.nodes)

    def signature(self) -> str:
        return "+".join(self.primitive_names())

    def node(self, primitive: str) -> Optional[Dict[str, Any]]:
        for node in self.nodes:
            if node["primitive"] == primitive:
                return node
        return None

    def state(self) -> Dict[str, Any]:
        """The measurements the phase controller is allowed to look at."""
        return {"hypotheses": self.hypotheses, "uncertainty": self.artifacts.get("uncertainty"),
                "testable": self.signals.get("testable", False)}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "klass": self.klass,
            "signals": self.signals,
            "revision": self.revision,
            "regime": self.regime,
            "budget": self.budget,
            "spend": round(self.spend, 2),
            "signature": self.signature(),
            "nodes": [{"id": n["id"], "primitive": n["primitive"], "kind": n["kind"],
                       "cost": n["cost"], "regime": n.get("regime"), "tag": n.get("tag", ""),
                       "resource": n.get("resource", "")} for n in self.nodes],
            "edges": self.edges,
            "hypotheses": [{"id": h.get("id"), "claim": h.get("claim"),
                            "score": h.get("score"), "basis": h.get("basis", ""),
                            "expected_observation": h.get("expected_observation", ""),
                            "verified": h.get("verified", False),
                            "test": (h.get("test") or {}).get("payload", "")}
                           for h in self.hypotheses],
            "candidates": self.candidates,
            "chosen_experiment": self.chosen_experiment,
            "uncertainty": self.artifacts.get("uncertainty"),
            "testable": self.signals.get("testable", False),
            "artifacts": _artifact_summary(self.artifacts),
            "observations": self.observations[-5:],
            "history": self.history[-10:],
        }


def _artifact_summary(artifacts: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-safe shape of everything the nodes produced, for the dashboard."""
    out: Dict[str, Any] = {}
    shape = artifacts.get("repo_shape")
    if shape:
        out["repo_shape"] = {"entries": shape["entries"], "python_files": shape["python_files"],
                             "candidates": shape["candidates"], "by_suffix": shape["by_suffix"]}
    graph = artifacts.get("dependency_graph")
    if graph:
        out["dependency_graph"] = {"module_count": graph["module_count"],
                                   "cycles": graph["cycles"],
                                   "top_fan_in": list(graph["fan_in"].items())[:8],
                                   "unparsed": graph["unparsed"][:5]}
    symbols = artifacts.get("symbols")
    if symbols:
        out["symbols"] = {"count": symbols["count"],
                          "sample": symbols["symbols"][:12]}
    evidence = artifacts.get("evidence")
    if evidence:
        hits = evidence.get("hits") or []
        out["evidence"] = {"chunks": len(hits), "searched": evidence.get("searched", 0),
                           "sources": [hit.get("source") for hit in hits][:6],
                           "note": evidence.get("note", "")}
    for key in ("explanations", "constraints", "designs", "ranked_actions"):
        if artifacts.get(key):
            out[key] = artifacts[key][:8]
    for key in ("uncertainty", "observation", "synthesis", "remembered_approach", "knowledge",
                "experiment"):
        if artifacts.get(key):
            out[key] = artifacts[key]
    return out


def _node(primitive: str, tag: str = "") -> Dict[str, Any]:
    spec = PRIMITIVES[primitive]
    return {
        "id": primitive + (f"#{tag}" if tag else ""),
        "primitive": primitive,
        "kind": spec["kind"],
        "cost": spec["cost"],
        "regime": spec["regime"],
        "produces": list(spec["produces"]),
        "consumes": list(spec["consumes"]),
        "tag": tag,
        "resource": "",
    }


def generate(goal: str, signals: Optional[Dict[str, Any]] = None, root: Optional[str] = None,
             world: Optional[WorldModel] = None) -> Substrate:
    """Compose a cognitive structure for this goal."""
    signals = signals or characterize(goal, root)
    products = required_products(signals)
    chosen: Dict[str, Dict[str, Any]] = {}

    for product in products:
        producers = [name for name, spec in PRIMITIVES.items() if product in spec["produces"]]
        if producers:
            chosen[min(producers, key=lambda name: (PRIMITIVES[name]["cost"], name))] = None

    # close the required inputs transitively
    changed = True
    while changed:
        changed = False
        for name in list(chosen):
            for need in PRIMITIVES[name]["required"]:
                if any(need in PRIMITIVES[other]["produces"] for other in chosen):
                    continue
                producers = [p for p, spec in PRIMITIVES.items() if need in spec["produces"]]
                if producers:
                    best = min(producers, key=lambda p: (PRIMITIVES[p]["cost"], p))
                    if best not in chosen:
                        chosen[best] = None
                        changed = True

    strategy = world.prefer_strategy(signals.get("klass", "unknown")) if world is not None else None
    if strategy:
        chosen["recall_strategy"] = None

    nodes = [_node(name) for name in chosen]
    node_ids = {node["primitive"]: node["id"] for node in nodes}
    edges: List[List[str]] = []
    for node in nodes:
        for product in node["consumes"]:
            for other in nodes:
                if other["id"] != node["id"] and product in other["produces"]:
                    edges.append([other["id"], node["id"], product])
    if "execute_test" in node_ids and "hypotheses" in node_ids and signals.get("testable"):
        edges.append([node_ids["execute_test"], node_ids["hypotheses"], "restructure"])

    for node in nodes:
        if node["kind"] == "model":
            routing = resources.route(goal)
            node["resource"] = ", ".join(pick["resource"] for pick in routing["picks"]) or "none"
            node["coordination"] = routing["coordination"]["mode"]

    substrate = Substrate(
        goal=goal,
        klass=signals.get("klass", "unknown"),
        signals=signals,
        nodes=nodes,
        edges=edges,
        budget=float(signals.get("budget", 24.0)),
        hypotheses=[],
        history=[{
            "revision": 0,
            "operator": "generate",
            "reason": (f"characterized as {signals.get('klass')}: {len(nodes)} primitives wired "
                       f"for {len(products)} required products"),
            "added": [node["primitive"] for node in nodes],
            "removed": [],
        }],
    )
    if strategy:
        substrate.regime = "converge"
        substrate.history.append({
            "revision": 0,
            "operator": "recall",
            "reason": (f"the world model has {strategy['strategy'][:60]} at "
                       f"{strategy['success_rate']:.0%} success on {strategy['klass']} - starting "
                       f"in converge instead of explore"),
            "added": ["recall_strategy"], "removed": [],
        })
    return substrate


# ── execution ────────────────────────────────────────────────────────────────

def _exec_scope_repo(substrate: Substrate, artifacts: Dict[str, Any],
                     ctx: Dict[str, Any]) -> Dict[str, Any]:
    hints = substrate.signals.get("hints") or []
    shape = analysis.scan_repo(ctx.get("root"), hints=hints)
    artifacts["repo_shape"] = shape
    return {"summary": f"{shape['entries']} files, {shape['python_files']} python, "
                       f"{len(shape['candidates'])} named path(s) exist"}


def _exec_import_graph(substrate: Substrate, artifacts: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    graph = analysis.import_graph(ctx.get("root"))
    artifacts["dependency_graph"] = graph
    return {"summary": f"{graph['module_count']} modules, {len(graph['edges'])} import edges, "
                       f"{len(graph['cycles'])} cycle(s)"}


def _exec_symbol_index(substrate: Substrate, artifacts: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    index = analysis.symbol_index(ctx.get("root"))
    artifacts["symbols"] = index
    return {"summary": f"{index['count']} definitions indexed"}


def _exec_retrieve(substrate: Substrate, artifacts: Dict[str, Any],
                   ctx: Dict[str, Any]) -> Dict[str, Any]:
    result = rag.search(substrate.goal, top_k=5)
    if not result.get("hits"):
        result = {**result, "note": "the retrieval index is empty - run `rag: index src` to fill it"}
    artifacts["evidence"] = result
    return {"summary": f"{len(result.get('hits') or [])} chunk(s) retrieved"
                       + (" (index empty)" if not result.get("hits") else "")}


def _exec_evidence_graph(substrate: Substrate, artifacts: Dict[str, Any],
                         ctx: Dict[str, Any]) -> Dict[str, Any]:
    hits = (artifacts.get("evidence") or {}).get("hits") or []
    counts: Dict[str, int] = {}
    for hit in hits:
        for token in TOKEN.findall((hit.get("text") or "").lower()):
            if token in substrate.signals.get("tokens", []) or len(token) < 5:
                continue
            counts[token] = counts.get(token, 0) + 1
    explanations = [{"keyword": word, "support": count,
                     "claim": f"'{word}' is what the existing material is about"}
                    for word, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
    artifacts["explanations"] = explanations
    return {"summary": f"{len(explanations)} explanation(s) from retrieved evidence"}


def _exec_uncertainty(substrate: Substrate, artifacts: Dict[str, Any],
                      ctx: Dict[str, Any]) -> Dict[str, Any]:
    tokens = substrate.signals.get("tokens") or []
    haystack = " ".join([
        str((artifacts.get("evidence") or {}).get("hits") or ""),
        str(_artifact_summary(artifacts).get("repo_shape") or ""),
        str((artifacts.get("dependency_graph") or {}).get("cycles") or ""),
    ]).lower()
    covered = [token for token in tokens if token in haystack]
    coverage = len(covered) / max(1, len(tokens))
    uncertainty = round(min(1.0, max(0.05, 1.0 - coverage)), 4)
    artifacts["uncertainty"] = uncertainty
    artifacts["coverage"] = {"tokens": len(tokens), "covered": len(covered)}
    return {"summary": f"evidence covers {coverage:.0%} of the goal - uncertainty {uncertainty}"}


SUBJECT_STOP = {"the", "and", "for", "with", "that", "this", "from", "python", "import",
                "tests", "test", "command", "query", "list", "rag", "constraint", "src", "does"}


def _subjects(text: str) -> List[str]:
    """The concrete things a claim or a test is about - what makes a test decisive."""
    words = [token.lower() for token in re.split(r"[^A-Za-z0-9_]+", text or "")]
    return sorted({word for word in words
                   if len(word) >= 3 and word not in SUBJECT_STOP and not word.isdigit()})


def _hyp(hid: str, claim: str, score: float, expected: str, expects: str, test: Dict[str, str],
         basis: str = "static signals", subjects: Optional[List[str]] = None) -> Dict[str, Any]:
    """One candidate. `subjects` is what it is about - what makes a test decisive for it."""
    return {"id": hid, "claim": claim, "score": round(min(1.0, score), 3),
            "expected_observation": expected, "expects": expects, "test": test, "basis": basis,
            "subjects": subjects or _subjects(f"{claim} {' '.join(test.values())}"),
            "verified": False}


def _seed_hypotheses(substrate: Substrate, artifacts: Dict[str, Any],
                     world: Optional[WorldModel]) -> List[Dict[str, Any]]:
    """Deterministic candidates from real measurements, plus remembered tendencies."""
    klass = substrate.klass
    signals = substrate.signals
    graph = artifacts.get("dependency_graph") or {}
    shape = artifacts.get("repo_shape") or {}
    evidence = artifacts.get("evidence") or {}
    explanations = artifacts.get("explanations") or []
    out: List[Dict[str, Any]] = []

    if klass in ("debug", "operate", "unknown") or shape.get("python_files"):
        cycles = graph.get("cycles") or []
        if cycles:
            out.append(_hyp(
                "h1", f"one of the {len(cycles)} import cycle(s) "
                      f"({' -> '.join(cycles[0][:3])}) is behind this",
                0.35 + 0.1 * min(3, len(cycles)),
                "an import error naming one of those modules", "fail",
                {"kind": "command", "payload": f"python -c \"import {cycles[0][0]}\""},
                basis=f"import graph: {len(cycles)} cycle(s)"))
        if graph.get("unparsed"):
            out.append(_hyp(
                "h2", f"{len(graph['unparsed'])} module(s) do not even parse",
                0.3, "a syntax error naming one of those files", "fail",
                {"kind": "command",
                 "payload": f"python -m py_compile {graph['unparsed'][0].replace('.', '/')}.py"},
                basis="AST scan could not parse these files"))

    if signals.get("testable"):
        out.append(_hyp(
            "h3", "the repository's own checks already expose the state of this",
            0.4, "test failures naming the area in question", "fail",
            {"kind": "command", "payload": "python -m pytest tests -q"}, basis="tests/ exists"))

    if signals.get("existing_artifacts"):
        first = signals["existing_artifacts"][0]
        out.append(_hyp(
            "h4", f"the artifact named in the goal ({first}) is where the answer is",
            0.45, "the artifact is present and readable", "pass",
            {"kind": "command", "payload": f"ls -l {first}"}, basis="path named in the goal exists"))

    if klass == "design":
        for constraint in (artifacts.get("constraints") or [])[:3]:
            out.append(_hyp(
                f"d-{constraint['id']}", f"respecting the constraint '{constraint['text'][:60]}' "
                                         f"is what decides the design",
                0.4, f"a design that fails '{constraint['text'][:40]}'", "fail",
                {"kind": "query", "payload": f"constraint:{constraint['id']}"},
                basis="constraint extracted from the goal",
                subjects=[constraint["id"]] + _subjects(constraint["text"])[:2]))

    for explanation in explanations[:3]:
        out.append(_hyp(
            f"e-{explanation['keyword']}", explanation["claim"],
            0.3 + 0.05 * explanation["support"],
            f"the material about '{explanation['keyword']}' is confirmed", "pass",
            {"kind": "query", "payload": f"rag: {explanation['keyword']}"},
            basis=f"{explanation['support']} retrieved hit(s)"))

    if not out:
        out.append(_hyp("h0", "the goal needs its artifacts located before anything can be said",
                        0.25, "no usable artifact was found", "fail",
                        {"kind": "query", "payload": "list:."}, basis="no signals matched"))

    if world is not None:
        leading = (substrate.signals.get("tokens") or ["unknown"])[0]
        for claim in world.generate_hypotheses(klass if klass != "unknown" else leading, limit=3):
            out.append(_hyp(
                f"w-{claim['id']}", f"{claim['claim']} (learned tendency, unverified)",
                max(0.2, claim["confidence"]), f"{claim['predicts']} is observed", "pass",
                {"kind": "query", "payload": claim["test"]},
                basis=f"world model {claim['basis']} - unverified until confirmed"))
            out[-1]["prediction_id"] = claim["id"]

    total = sum(h["score"] for h in out) or 1.0
    for hypothesis in out:
        hypothesis["score"] = round(hypothesis["score"] / total, 4)
    return out


def _exec_hypotheses(substrate: Substrate, artifacts: Dict[str, Any],
                     ctx: Dict[str, Any]) -> Dict[str, Any]:
    substrate.hypotheses = _seed_hypotheses(substrate, artifacts, ctx.get("world"))
    return {"summary": f"{len(substrate.hypotheses)} candidate(s) generated"}


def _exec_constraint_space(substrate: Substrate, artifacts: Dict[str, Any],
                           ctx: Dict[str, Any]) -> Dict[str, Any]:
    text = substrate.goal
    constraints: List[Dict[str, Any]] = []
    for index, sentence in enumerate(re.split(r"[.;\n]", text)):
        low = sentence.lower().strip()
        if not low:
            continue
        kind = None
        for marker, label in (("must not", "prohibition"), ("avoid", "prohibition"),
                              ("must", "requirement"), ("should", "preference"),
                              ("needs to", "requirement"), ("without", "prohibition")):
            if marker in low:
                kind = label
                break
        if kind:
            constraints.append({"id": f"c{len(constraints) + 1}", "kind": kind,
                                "text": sentence.strip()[:160], "source_sentence": index})
    if not constraints:
        constraints.append({"id": "c1", "kind": "implicit",
                            "text": "the design must actually solve the stated goal",
                            "source_sentence": 0})
    artifacts["constraints"] = constraints
    return {"summary": f"{len(constraints)} constraint(s) extracted from the goal"}


def _exec_design_search(substrate: Substrate, artifacts: Dict[str, Any],
                        ctx: Dict[str, Any]) -> Dict[str, Any]:
    constraints = artifacts.get("constraints") or []
    remembered = artifacts.get("remembered_approach") or {}
    designs: List[Dict[str, Any]] = []
    for index in range(len(constraints)):
        satisfied = [constraints[index]["id"]]
        designs.append({
            "id": f"design-{index + 1}",
            "satisfies": satisfied,
            "violates": [c["id"] for c in constraints if c["id"] not in satisfied],
            "shape": f"built around '{constraints[index]['text'][:60]}'",
        })
    if remembered:
        designs.append({
            "id": "design-remembered",
            "satisfies": [c["id"] for c in constraints],
            "violates": [],
            "shape": f"reuses what worked before: {remembered['strategy'][:80]}",
            "basis": f"world model, {remembered['success_rate']:.0%} on "
                     f"{remembered['attempts']} run(s)",
        })
    artifacts["designs"] = designs
    return {"summary": f"{len(designs)} candidate design(s) from the constraint space"}


def _candidates_from(hypotheses: List[Dict[str, Any]]) -> List[counterfactual.Candidate]:
    """Turn each hypothesis into the action that would test it.

    Each hypothesis then states what it expects of *every* candidate, not just
    its own: a test is decisive for a hypothesis when the test is about the same
    thing the hypothesis is about, and tells us nothing about it otherwise. That
    is the difference between a test that separates the candidates and one that
    merely repeats what is already believed.
    """
    candidates: List[counterfactual.Candidate] = []
    target_of: Dict[str, set] = {}
    for hypothesis in hypotheses:
        test = hypothesis.get("test") or {}
        payload = (test.get("payload") or "").strip()
        if not payload:
            continue
        kind = test.get("kind", "command")
        label = f"{kind}: {payload[:60]}"
        if label not in target_of:
            target_of[label] = set(hypothesis.get("subjects") or _subjects(payload))
            candidates.append(counterfactual.Candidate(
                label=label, kind="query" if kind == "query" else kind, payload=payload,
                cost=1.0 if kind == "query" else 3.0, notes=hypothesis.get("claim", "")))

    for hypothesis in hypotheses:
        own = set(hypothesis.get("subjects") or [])
        hypothesis["predicts"] = {
            candidate.label: ("separates" if own & target_of[candidate.label] else "no-signal")
            for candidate in candidates
        }
    return candidates


def _exec_counterfactual(substrate: Substrate, artifacts: Dict[str, Any],
                         ctx: Dict[str, Any]) -> Dict[str, Any]:
    substrate.candidates = _candidates_from(substrate.hypotheses)
    ranked = counterfactual.rank(substrate.candidates, substrate.hypotheses,
                                 artifacts.get("dependency_graph"))
    artifacts["ranked_actions"] = ranked
    return {"summary": f"{len(ranked)} candidate action(s) predicted before execution"}


def _exec_discriminate(substrate: Substrate, artifacts: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    decision = counterfactual.choose_experiment(substrate.candidates, substrate.hypotheses,
                                                artifacts.get("dependency_graph"))
    substrate.chosen_experiment = decision.get("chosen")
    artifacts["experiment"] = decision
    if not decision.get("chosen"):
        return {"summary": "nothing to run: no candidate separates the hypotheses"}
    return {"summary": f"chose {decision['chosen']['label'][:60]} "
                       f"({decision['chosen']['gain']} bits for {decision['chosen']['cost']} cost)"}


def _exec_fuse_resources(substrate: Substrate, artifacts: Dict[str, Any],
                         ctx: Dict[str, Any]) -> Dict[str, Any]:
    routing = resources.route(substrate.goal)
    routing.pop("_by_name", None)
    artifacts["synthesis"] = {
        "routing": routing,
        "answer": "",
        "note": ("no model resource is configured, so the deterministic path carries this: "
                 "add one with `model: add` to bring a model into the composition"),
    }
    return {"summary": f"coordinated {len(routing['picks'])} resource(s) "
                       f"({routing['coordination']['mode']})"}


KNOWN_BRANCHES = {"pass": ("pass", "ok", "healthy", "success"), "fail": ("fail", "error", "traceback")}


def _exec_execute_test(substrate: Substrate, artifacts: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run the chosen test for real - only when the caller explicitly allows execution."""
    chosen = substrate.chosen_experiment or {}
    command = ctx.get("command") or chosen.get("payload") or ""
    if not command:
        return {"summary": "no command to run", "pending": True}

    if chosen.get("kind") == "query" and not ctx.get("command"):
        payload = chosen.get("payload", "")
        if not payload.startswith("rag:"):
            return {"summary": f"the chosen test {payload[:60]!r} is a retrieval query, not a "
                               f"runnable command", "pending": True}
        hits = rag.search(payload.split(":", 1)[1].strip(), top_k=3).get("hits") or []
        observation = {"command": payload, "exit_code": 0 if hits else 1,
                       "branch": "pass" if hits else "fail",
                       "output": f"{len(hits)} chunk(s) retrieved"}
    else:
        try:
            proc = subprocess.run(command, shell=True, cwd=ctx.get("root") or REPO_ROOT,
                                  capture_output=True, text=True,
                                  timeout=ctx.get("timeout", 120))
            observation = {"command": command, "exit_code": proc.returncode,
                           "branch": "pass" if proc.returncode == 0 else "fail",
                           "output": ((proc.stdout or "") + (proc.stderr or "")).strip()[-1500:]}
        except subprocess.TimeoutExpired:
            observation = {"command": command, "exit_code": None, "branch": "fail",
                           "output": "timed out"}
        except OSError as exc:
            observation = {"command": command, "exit_code": None, "branch": "fail",
                           "output": f"{type(exc).__name__}: {exc}"}

    observation["predicted"] = False
    label = chosen.get("label")
    consistent, refuted = [], []
    world = ctx.get("world")
    for hypothesis in substrate.hypotheses:
        predicted = (hypothesis.get("predicts") or {}).get(label)
        if predicted is None:
            continue
        agrees = (hypothesis.get("expects") or "fail") == observation["branch"]
        hypothesis["verified"] = agrees
        hypothesis["observed"] = observation["branch"]
        (consistent if agrees else refuted).append(hypothesis["id"])
        if hypothesis.get("prediction_id") and world is not None:
            world.confirm(hypothesis["prediction_id"],
                          "supported" if agrees else "refuted", evidence=command)
    observation["consistent_with"] = consistent
    observation["refuted"] = refuted
    artifacts["observation"] = observation
    substrate.observations.append(observation)
    return {"summary": f"ran `{command[:60]}` -> {observation['branch']} "
                       f"({len(consistent)} candidate(s) consistent, {len(refuted)} refuted)"}


def procedure(substrate: Substrate) -> str:
    """The class-level procedure tag experience is measured against.

    Deliberately coarser than the topology: two problems of a class that call on
    the same *kinds* of computation share a procedure, so what one learns about
    the class is available to the next. The exact structure stays in the history.
    """
    kinds = "+".join(sorted({node["kind"] for node in substrate.nodes}))
    return f"{substrate.klass}:{kinds}"


def _exec_compress(substrate: Substrate, artifacts: Dict[str, Any],
                   ctx: Dict[str, Any]) -> Dict[str, Any]:
    world = ctx.get("world")
    if world is None:
        return {"summary": "no world model attached - nothing to distil into"}
    observation = artifacts.get("observation") or {}
    chosen = substrate.chosen_experiment or {}
    if observation:
        outcome = "observed"
        meaning = "a real command ran and its result was recorded"
    elif chosen.get("gain", 0.0) > 0:
        outcome = "decisive"
        meaning = ("the run produced an experiment that separated its candidates - not a "
                   "claim about the code under test, which only execution can settle")
    else:
        outcome = "unresolved"
        meaning = "the run stayed open: nothing was separable and nothing was executed"
    concepts = [substrate.klass] + substrate.signals.get("tokens", [])[:3]
    if substrate.chosen_experiment:
        concepts.append(substrate.chosen_experiment["label"][:60])
    if substrate.hypotheses:
        concepts.append(substrate.hypotheses[0]["id"])
    record = world.observe(concepts=concepts, outcome=outcome, klass=substrate.klass,
                           strategy=procedure(substrate), cost=substrate.spend,
                           extra={"context": substrate.goal[:160],
                                  "topology": substrate.signature(),
                                  "success_meaning": meaning})
    artifacts["knowledge"] = {
        "recorded": record,
        "procedure": procedure(substrate),
        "topology": substrate.signature(),
        "outcome": outcome,
        "outcome_meaning": meaning,
        "runs": len([entry for entry in world.strategies(substrate.klass)
                     if entry["strategy"] == procedure(substrate)]),
        "note": "written to the world model - it will seed the next problem of this class",
    }
    return {"summary": f"distilled {procedure(substrate)[:40]}… into the world model "
                       f"as {outcome}"}


def _exec_recall_strategy(substrate: Substrate, artifacts: Dict[str, Any],
                          ctx: Dict[str, Any]) -> Dict[str, Any]:
    world = ctx.get("world")
    strategy = world.prefer_strategy(substrate.klass) if world is not None else None
    artifacts["remembered_approach"] = strategy or {
        "strategy": "", "success_rate": 0.0, "attempts": 0,
        "note": "no measured procedure for this class yet"}
    return {"summary": (f"remembered {strategy['strategy'][:50]} "
                        f"({strategy['success_rate']:.0%} over {strategy['attempts']} run(s))"
                        if strategy else "nothing remembered for this class yet")}


EXECUTORS = {
    "scope_repo": _exec_scope_repo,
    "import_graph": _exec_import_graph,
    "symbol_index": _exec_symbol_index,
    "retrieve": _exec_retrieve,
    "evidence_graph": _exec_evidence_graph,
    "uncertainty": _exec_uncertainty,
    "hypotheses": _exec_hypotheses,
    "constraint_space": _exec_constraint_space,
    "design_search": _exec_design_search,
    "counterfactual": _exec_counterfactual,
    "discriminate": _exec_discriminate,
    "fuse_resources": _exec_fuse_resources,
    "execute_test": _exec_execute_test,
    "compress": _exec_compress,
    "recall_strategy": _exec_recall_strategy,
}


def _by_phase(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Explore before converge before execute before compress - a node's regime is its rank."""
    rank = {name: index for index, name in enumerate(phases.REGIMES)}
    return sorted(nodes, key=lambda node: (rank.get(node.get("regime"), 9), node["cost"], node["id"]))


def _order(substrate: Substrate) -> List[Dict[str, Any]]:
    """Producers before consumers, ignoring the restructure feedback edges."""
    nodes = {node["id"]: node for node in substrate.nodes}
    incoming: Dict[str, int] = {node_id: 0 for node_id in nodes}
    forward: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
    for src, dst, product in substrate.edges:
        if product == "restructure" or src not in nodes or dst not in nodes:
            continue
        incoming[dst] += 1
        forward[src].append(dst)
    ready = _by_phase([nodes[node_id] for node_id, count in incoming.items() if count == 0])
    order: List[Dict[str, Any]] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for nxt in forward[node["id"]]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                ready.append(nodes[nxt])
        ready = _by_phase(ready)
    if len(order) != len(nodes):  # a cycle slipped in - fall back to the phase order
        return _by_phase(list(substrate.nodes))
    return order


def execute(substrate: Substrate, limit: int = 12, allow_execution: bool = False,
            root: Optional[str] = None, world: Optional[WorldModel] = None,
            controller: Optional[phases.PhaseController] = None,
            command: str = "") -> Dict[str, Any]:
    """Run the structure. Analysis runs for real; execution waits to be allowed."""
    ctx = {"root": root or REPO_ROOT, "world": world, "command": command}
    ran: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    already: List[Dict[str, Any]] = []
    if limit <= 0 or substrate.spend >= substrate.budget:
        return {"ran": [], "pending": [{"node": n["id"], "reason": "budget spent"}
                                       for n in substrate.nodes],
                "spend": substrate.spend, "budget": substrate.budget, "regime": substrate.regime}

    # The last unit of budget is held back for compression: a run that cannot distil
    # what it learned teaches the agent nothing, so the cheap learning step is
    # protected from everything ahead of it.
    reserve = 1.0 if any(node["primitive"] == "compress" for node in substrate.nodes) else 0.0
    for node in _order(substrate):
        primitive = node["primitive"]
        if node.get("done"):
            # a structure can be executed again without paying for its analysis twice
            already.append({"node": node["id"], "reason": "already ran in this structure"})
            continue
        ceiling = substrate.budget if primitive == "compress" else substrate.budget - reserve
        if substrate.spend + node["cost"] > ceiling:
            pending.append({"node": node["id"], "reason": "would exceed the compute budget"})
            continue
        if len(ran) >= limit and primitive != "compress":
            pending.append({"node": node["id"], "reason": "step limit reached"})
            continue
        if primitive == "execute_test" and not allow_execution:
            pending.append({"node": node["id"],
                            "reason": "execution not allowed: it runs a real command, so it waits "
                                      "for an explicit go-ahead"})
            continue
        executor = EXECUTORS.get(primitive)
        if executor is None:
            pending.append({"node": node["id"], "reason": "no executor"})
            continue
        try:
            outcome = executor(substrate, substrate.artifacts, ctx) or {}
            ran.append({"node": node["id"], "primitive": primitive, "kind": node["kind"],
                        "cost": node["cost"], "summary": outcome.get("summary", "")})
        except Exception as exc:  # a node failing must not lose the rest of the structure
            ran.append({"node": node["id"], "primitive": primitive, "kind": node["kind"],
                        "cost": node["cost"], "ok": False,
                        "summary": f"{type(exc).__name__}: {exc}"})
        node["done"] = True
        substrate.spend = round(substrate.spend + node["cost"], 2)

    series = list(substrate.artifacts.get("progress_series") or [])
    series.append(round(max([float(h.get("score", 0.0)) for h in substrate.hypotheses] or [0.0]), 4))
    substrate.artifacts["progress_series"] = series
    contradictions = sum(len(observation.get("refuted") or [])
                         for observation in substrate.observations)
    controller = controller or phases.PhaseController(substrate.regime, substrate.budget)
    transition = controller.step(substrate.state(), contradictions=contradictions,
                                 spend=substrate.spend, progress=series)
    substrate.regime = controller.regime

    result = {
        "ran": ran,
        "pending": pending,
        "already_done": already,
        "spend": substrate.spend,
        "budget": substrate.budget,
        "regime": substrate.regime,
        "transition": transition,
        "hypotheses": len(substrate.hypotheses),
        "chosen_experiment": (substrate.chosen_experiment or {}).get("label"),
        "uncertainty": substrate.artifacts.get("uncertainty"),
        "signature": substrate.signature(),
        "progress_series": substrate.artifacts.get("progress_series", []),
    }
    remember(substrate, result)
    return result


# ── restructuring ────────────────────────────────────────────────────────────

def restructure(substrate: Substrate, observation: Dict[str, Any]) -> Substrate:
    """Rebuild the structure when the evidence says the current one is wrong."""
    obs = dict(observation or {})
    kind = str(obs.get("kind") or "evidence").lower()
    nodes = [dict(node) for node in substrate.nodes]
    edges = [list(edge) for edge in substrate.edges]
    hypotheses = [dict(hypothesis) for hypothesis in substrate.hypotheses]
    added: List[str] = []
    removed: List[str] = []
    operator, reason = "deepen", "no decisive signal: add a step that measures something"

    if kind in ("contradiction", "stall", "surprise"):
        operator = "broaden"
        reason = "the measurements conflict or progress stalled: widen the hypothesis space"
        node = _node("hypotheses", tag="alternatives")
        nodes.append(node)
        added.append(node["id"])
        for hypothesis in hypotheses:
            hypothesis["score"] = round(float(hypothesis.get("score", 0.5)) * 0.85, 4)
        for other in nodes:
            if other["primitive"] in ("counterfactual", "discriminate"):
                edges.append([node["id"], other["id"], "hypotheses"])
    elif kind == "test_result":
        supported = {str(item) for item in obs.get("supports") or []}
        refuted = {str(item) for item in obs.get("refutes") or []}
        if refuted:
            operator = "narrow"
            reason = f"{len(refuted)} candidate(s) were refuted: drop them and keep the survivors"
            hypotheses = [h for h in hypotheses if str(h.get("id")) not in refuted]
            removed.extend(sorted(refuted))
            for hypothesis in hypotheses:
                if str(hypothesis.get("id")) in supported:
                    hypothesis["score"] = round(min(1.0, float(hypothesis.get("score", 0.5)) * 1.5), 4)
            if not any(h["primitive"] == "evidence_graph" for h in nodes):
                node = _node("evidence_graph")
                nodes.append(node)
                added.append(node["id"])
                edges.append([node["id"], "hypotheses", "explanations"])
        else:
            operator = "deepen"
            reason = "the test did not separate the candidates: add a real verification step"
            node = _node("execute_test", tag="verification")
            nodes.append(node)
            added.append(node["id"])
            for other in nodes:
                if other["primitive"] == "discriminate":
                    edges.append([node["id"], other["id"], "observation"])
    elif kind == "cost":
        operator = "reroute"
        reason = "spend outran the plan: hand the work to cheaper computation"
        expensive = max((n for n in nodes if n["kind"] in ("model", "execution")),
                        key=lambda n: n["cost"], default=None)
        if expensive is not None:
            product = expensive["produces"][0]
            alternatives = [name for name, spec in PRIMITIVES.items()
                            if product in spec["produces"] and name != expensive["primitive"]]
            if alternatives:
                cheapest = min(alternatives, key=lambda name: PRIMITIVES[name]["cost"])
                old = expensive["primitive"]
                expensive.update(_node(cheapest, tag="reroute"))
                added.append(expensive["id"])
                removed.append(old)
            else:
                node = _node("compress", tag="early")
                nodes.append(node)
                added.append(node["id"])
    else:
        node = _node("execute_test", tag="verification")
        nodes.append(node)
        added.append(node["id"])

    rebuild = Substrate(
        goal=substrate.goal,
        klass=substrate.klass,
        signals=substrate.signals,
        nodes=nodes,
        edges=edges,
        budget=substrate.budget,
        spend=substrate.spend,
        revision=substrate.revision + 1,
        regime=substrate.regime,
        hypotheses=hypotheses,
        candidates=[],
        chosen_experiment=None,
        artifacts=dict(substrate.artifacts),
        observations=list(substrate.observations) + [obs],
        history=list(substrate.history) + [{
            "revision": substrate.revision + 1,
            "operator": operator,
            "reason": reason,
            "added": added,
            "removed": removed,
            "trigger": kind,
        }],
    )
    return rebuild


def remember(substrate: Substrate, result: Optional[Dict[str, Any]] = None) -> None:
    """Keep the most recent structure in memory so the dashboard can show it."""
    with _lock:
        _LAST.clear()
        _LAST.update(substrate.to_dict())
        if result:
            _LAST["last_result"] = {key: result[key] for key in
                                    ("spend", "budget", "regime", "signature", "hypotheses",
                                     "chosen_experiment", "uncertainty") if key in result}


def last() -> Dict[str, Any]:
    with _lock:
        return dict(_LAST)


def stats() -> Dict[str, Any]:
    """What the substrate can do, without building one."""
    return {
        "primitives": {name: {"kind": spec["kind"], "cost": spec["cost"],
                              "produces": spec["produces"], "regime": spec["regime"],
                              "description": spec["description"]}
                       for name, spec in sorted(PRIMITIVES.items())},
        "classes": sorted(CLASS_WORDS),
        "regimes": list(phases.REGIMES),
        "thresholds": phases.THRESHOLDS,
        "last": last(),
    }
