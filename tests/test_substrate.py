"""Tests for the cognitive substrate: characterization, morphogenesis, execution, restructuring."""

import json

import pytest

from src.agent import cognition, rag, substrate
from src.agent.tools import build_registry
from src.agent.worldmodel import WorldModel


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """No test may touch the repo's own index or world model."""
    monkeypatch.setattr(rag, "DB_PATH", str(tmp_path / "rag.db"))


@pytest.fixture
def repo(tmp_path):
    """A tiny repository the analysis primitives can really read."""
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "base.py").write_text("def helper():\n    return 1\n")
    (package / "uses.py").write_text(
        "from pkg.base import helper\n\n\ndef run():\n    return helper()\n")
    return str(tmp_path)


@pytest.fixture
def world(tmp_path):
    return WorldModel(str(tmp_path / "world.db"))


# ── characterization ──

def test_characterization_separates_problem_classes(repo):
    debug = substrate.characterize("the loop fails to import after the change", repo)
    research = substrate.characterize("why does the loop pace itself with a backlog", repo)
    design = substrate.characterize("design a new memory layer for the agent", repo)
    operate = substrate.characterize("check the engine health and verify the build", repo)
    assert debug["klass"] == "debug"
    assert research["klass"] == "research"
    assert design["klass"] == "design"
    assert operate["klass"] == "operate"


def test_characterization_only_counts_artifacts_that_exist(repo):
    signals = substrate.characterize("why does pkg/base.py fail, and not ghost/none.py", repo)
    assert "pkg/base.py" in signals["existing_artifacts"]
    assert "ghost/none.py" not in signals["existing_artifacts"]
    assert signals["testable"] is True  # a real artifact exists to look at


def test_cost_aware_goals_get_a_smaller_budget(repo):
    assert substrate.characterize("design it cheaply, keep it minimal", repo)["budget"] < \
        substrate.characterize("design it thoroughly", repo)["budget"]


# ── morphogenesis ──

def test_a_debugging_structure_is_wired_by_data_flow(repo):
    structure = substrate.generate("why does pkg/base.py fail - find the cause", root=repo)
    names = structure.primitive_names()
    for expected in ("scope_repo", "import_graph", "hypotheses", "counterfactual", "discriminate",
                     "compress"):
        assert expected in names
    produced = {node["id"]: node["produces"] for node in structure.nodes}
    # every edge really joins a producer to a consumer
    for source, target, product in structure.edges:
        if product == "restructure":
            continue
        assert product in produced[source], (source, product)
        assert product in [p for node in structure.nodes
                           if node["id"] == target for p in node["consumes"]]


def test_generation_closes_required_inputs(repo):
    """`hypotheses` cannot work without an uncertainty reading, so it is pulled in."""
    structure = substrate.generate("design a connector registry", root=repo)
    assert structure.node("hypotheses") is not None
    assert structure.node("uncertainty") is not None
    assert structure.node("counterfactual") is not None
    assert structure.node("discriminate") is not None


def test_different_classes_produce_materially_different_structures(repo):
    goals = [
        "why does pkg/uses.py fail to import - fix it",
        "why does the queue retry the way it does - explain",
        "design a plugin system; it must stay stdlib only",
        "check the engine health and verify the build",
    ]
    signatures = {substrate.generate(goal, root=repo).signature() for goal in goals}
    assert len(signatures) >= 3
    assert len({node["primitive"] for node in
                substrate.generate(goals[2], root=repo).nodes} -
               {node["primitive"] for node in
                substrate.generate(goals[3], root=repo).nodes}) > 0


def test_a_remembered_procedure_changes_the_next_structure(repo, world):
    procedure = "debug:deterministic+retrieval+simulation"
    world.observe(["debug"], "observed", klass="debug", strategy=procedure)
    world.observe(["debug"], "observed", klass="debug", strategy=procedure)

    structure = substrate.generate("why does pkg/uses.py fail - find the cause", root=repo,
                                   world=world)
    assert structure.node("recall_strategy") is not None
    assert structure.regime == "converge"          # experience moves the starting regime
    assert any(entry["operator"] == "recall" for entry in structure.history)


# ── execution ──

def test_execution_runs_the_analysis_for_real(repo, world):
    structure = substrate.generate("why does pkg/uses.py fail - find the cause", root=repo)
    result = substrate.execute(structure, limit=12, root=repo, world=world)
    ran = {entry["primitive"] for entry in result["ran"]}
    assert {"scope_repo", "import_graph", "hypotheses", "counterfactual", "discriminate"} <= ran
    assert structure.artifacts["dependency_graph"]["module_count"] >= 3
    assert structure.hypotheses
    assert result["spend"] > 0 and result["spend"] <= structure.budget
    assert result["regime"] in substrate.phases.REGIMES


def test_execution_waits_for_permission(repo, world):
    structure = substrate.generate("check the engine health and verify the build", root=repo)
    blocked = substrate.execute(structure, limit=12, root=repo, world=world)
    assert any(item["node"].startswith("execute_test") for item in blocked["pending"])
    assert "observation" not in structure.artifacts

    allowed = substrate.execute(structure, limit=12, root=repo, world=world,
                                allow_execution=True, command="python -c 'print(1)'")
    assert allowed["ran"], "an explicitly allowed command still has to run"
    observation = structure.artifacts["observation"]
    assert observation["command"] == "python -c 'print(1)'"
    assert observation["branch"] == "pass"


def test_a_tiny_budget_still_buys_the_learning_step(repo, world):
    structure = substrate.generate("why does pkg/base.py fail", root=repo)
    structure.budget = 3.0
    result = substrate.execute(structure, limit=20, root=repo, world=world)
    assert "compress" in {entry["primitive"] for entry in result["ran"]}
    assert result["pending"], "what does not fit is reported, not silently skipped"
    assert result["spend"] <= structure.budget


def test_compression_writes_what_was_learned_into_the_world_model(repo, world):
    structure = substrate.generate("why does pkg/base.py fail - find the cause", root=repo)
    substrate.execute(structure, limit=12, root=repo, world=world)
    learned = structure.artifacts["knowledge"]
    assert learned["outcome"] in ("decisive", "observed", "unresolved")
    assert learned["outcome_meaning"]
    assert world.stats()["observations"] >= 1
    assert world.strategies("debug")


# ── restructuring ──

def test_a_stall_broadens_the_hypothesis_space(repo):
    structure = substrate.generate("why does pkg/base.py fail", root=repo)
    rebuilt = substrate.restructure(structure, {"kind": "stall"})
    assert rebuilt.revision == 1
    assert rebuilt.history[-1]["operator"] == "broaden"
    assert len(rebuilt.nodes) == len(structure.nodes) + 1
    assert any(node["tag"] == "alternatives" for node in rebuilt.nodes)


def test_a_refutation_narrows_the_candidates(repo, world):
    structure = substrate.generate("why does pkg/base.py fail", root=repo)
    substrate.execute(structure, limit=12, root=repo, world=world)
    loser = structure.hypotheses[0]["id"]
    rebuilt = substrate.restructure(structure, {"kind": "test_result", "refutes": [loser]})
    assert rebuilt.history[-1]["operator"] == "narrow"
    assert loser not in [hypothesis["id"] for hypothesis in rebuilt.hypotheses]


def test_an_inconclusive_test_deepens_the_structure(repo, world):
    structure = substrate.generate("why does pkg/base.py fail", root=repo)
    substrate.execute(structure, limit=12, root=repo, world=world)
    rebuilt = substrate.restructure(structure, {"kind": "test_result", "supports": []})
    assert rebuilt.history[-1]["operator"] == "deepen"
    assert rebuilt.node("execute_test") is not None


def test_a_cost_overrun_reroutes_to_cheaper_computation(repo):
    structure = substrate.generate("why does pkg/base.py fail", root=repo)
    expensive = substrate._node("execute_test", tag="probe")
    structure.nodes.append(expensive)
    rebuilt = substrate.restructure(structure, {"kind": "cost"})
    assert rebuilt.history[-1]["operator"] in ("reroute", "deepen")
    assert rebuilt.revision == structure.revision + 1


# ── tool surface ──

def test_the_registry_exposes_the_cognitive_layer():
    names = set(build_registry().names())
    assert {"substrate", "phase", "world", "predict", "resources", "benchmark"} <= names


def test_substrate_tool_builds_and_reports(tmp_path, repo):
    result = cognition.substrate_tool(action="build",
                                      goal="why does pkg/base.py fail - find the cause")
    payload = json.loads(result.output)
    assert result.ok is True
    assert payload["klass"] == "debug"
    assert payload["nodes"] and payload["signature"]


def test_substrate_tool_needs_a_goal():
    result = cognition.substrate_tool(action="build", goal="")
    assert result.ok is False and "goal is required" in result.error


def test_predict_tool_uses_the_current_structure(repo, world, tmp_path):
    cognition.substrate_tool(action="execute",
                             goal="why does pkg/base.py fail - find the cause",
                             world_path=str(tmp_path / "world.db"))
    result = cognition.predict_tool(action="choose")
    assert result.ok is True
    payload = json.loads(result.output)
    assert payload["chosen"] is None or payload["chosen"]["label"]
