"""The emergent cognitive field: regimes, cells, coalitions, evolution, morphogenesis, and the brain."""

import json
import os
import time

import pytest

from src.agent import capabilities as capability_layer
from src.agent import substrate
from src.agent.brain import DeliberativeBrain, ToolCall
from src.agent.field import (CELL_SEEDS, REGIMES, CognitiveField, Metacognition,
                             summarize)
from src.agent.field_brain import AdaptiveFieldBrain


@pytest.fixture(autouse=True)
def isolated_substrate(monkeypatch):
    """The substrate's last structure is process-global; these tests own their state."""
    monkeypatch.setattr(substrate, "last", lambda: {})


def _field(tmp_path=None, autoload=False, auto_morph=False):
    path = str(tmp_path / "field.json") if tmp_path is not None else "/tmp/zyphus-test-field.json"
    return CognitiveField(path=path, autoload=autoload, auto_morph=auto_morph)


def _settle(field, **signals):
    field.perceive(signals)
    return field.step()


def _brain(tmp_path, **kwargs):
    return AdaptiveFieldBrain(composer=DeliberativeBrain(notes_dir=str(tmp_path / "notes")),
                              field=_field(tmp_path), world_path=str(tmp_path / "world.db"),
                              **kwargs)


def _prime_world(brain, concepts=10, observations=20):
    """A world model that has looked at everything it knows: novelty reads zero."""
    brain._world_cache = (time.time(), {"concepts": concepts, "observations": observations})


# ── regimes emerge from the population ─────────────────────────────────────

def test_a_quiet_field_rests_diffuse():
    field = _field()
    assert _settle(field) == "diffuse"
    assert field.activation["diffuse"] > field.activation["convergent"]


def test_a_known_task_converges():
    field = _field()
    assert _settle(field, task=1.0, competence=0.8) == "convergent"
    assert field.activation["convergent"] > 0.5


def test_an_unmapped_world_spreads_activation():
    field = _field()
    assert _settle(field, novelty=0.9, uncertainty=0.5) == "diffuse"
    assert field.activation["diffuse"] > field.activation["structural"]


def test_a_new_task_of_unknown_shape_goes_structural():
    field = _field()
    assert _settle(field, task=1.0, novelty=0.7, uncertainty=0.5) == "structural"
    assert field.activation["structural"] > field.activation["convergent"]


def test_repetition_settles_into_commitment():
    field = _field()
    assert _settle(field, fatigue=0.9, competence=0.8) == "convergent"


def test_negative_coupling_keeps_diffuse_off_a_waiting_task():
    field = _field()
    assert _settle(field, task=1.0, novelty=1.0, competence=1.0) == "structural"


def test_satiation_tires_the_winning_coalition(monkeypatch):
    field = _field()
    field.perceive({"task": 1.0, "competence": 0.8})
    for _ in range(10):
        field.step()
    tired = field.activation["convergent"]
    assert field.cells["commit"].satiation > 0.5

    monkeypatch.setattr("src.agent.field.SATIATION", 0.0)
    fresh = _field()
    fresh.perceive({"task": 1.0, "competence": 0.8})
    for _ in range(10):
        fresh.step()
    assert tired < fresh.activation["convergent"]


def test_a_long_gap_relaxes_the_field():
    field = _field()
    field.perceive({"task": 1.0, "competence": 0.8})
    field.step()
    hot = field.activation["convergent"]
    field.perceive({})  # nothing happening any more
    field.step(seconds=12.0)
    assert field.activation["convergent"] < hot


def test_hysteresis_stops_the_regime_flickering():
    field = _field()
    field.regime = "diffuse"
    for name in ("scan", "associate", "wander"):
        field.cells[name].activation = 0.30
    means = field.regime_activation()
    for name in ("compose", "frame", "ground"):
        field.cells[name].activation = 0.315
    field._settle_regime("structural", field.regime_activation())
    assert field.regime == "diffuse"
    assert means["diffuse"] == pytest.approx(0.30)

    for name in ("compose", "frame", "ground"):
        field.cells[name].activation = 0.40
    field._settle_regime("structural", field.regime_activation())
    assert field.regime == "structural"
    assert field.transitions[-1]["from"] == "diffuse"


def test_perception_clamps_and_forgets_stale_signals():
    field = _field()
    field.perceive({"task": 5.0, "novelty": -3, "unknown": 1.0})
    assert field.signals["task"] == 1.0
    assert field.signals["novelty"] == 0.0
    assert field.signals["surprise"] == 0.0


# ── distributed cells and competing coalitions ─────────────────────────────

def test_the_population_is_distributed_across_the_three_regimes():
    field = _field()
    for regime in REGIMES:
        members = [cell for cell in field.cells.values() if cell.regime == regime]
        assert len(members) >= 2
    assert {cell.capability for cell in field.cells.values()} >= {
        "planner", "probe", "retrieval", "model", "verify", "consolidate"}
    assert len(field.cells) == len(CELL_SEEDS)


def test_competing_coalitions_rank_by_activation():
    field = _field()
    _settle(field, task=1.0, competence=0.8)
    coalitions = field.coalitions()
    assert [entry["energy"] for entry in coalitions] == sorted(
        (entry["energy"] for entry in coalitions), reverse=True)
    assert coalitions[0]["regime"] == "convergent"
    assert coalitions[0]["cells"]
    assert field.coalition()["regime"] in REGIMES
    assert field.coalition()["cells"]


def test_a_coalition_is_the_active_cells_of_its_regime():
    field = _field()
    _settle(field, novelty=0.9, uncertainty=0.5)
    winner = field.coalition()
    assert winner["regime"] == "diffuse"
    for name in winner["cells"]:
        assert field.cells[name].regime == "diffuse"
        assert field.cells[name].activation >= 0.12


def test_the_field_evolves_without_any_task():
    field = _field()
    start = dict(field.regime_activation())
    for _ in range(8):
        field.evolve(seconds=12.0)
    assert field.steps == 8
    assert field.clock > 60.0
    assert len(field.transitions) >= 1
    assert field.regime_activation() != start


# ── morphogenesis: the brain restructures its own thinking ─────────────────

def test_an_overloaded_cell_splits_into_a_branch():
    field = _field()
    field.cells["scan"].activation = 0.9
    before = len(field.cells)
    report = field.morph()
    assert report["generation"] == 1
    assert len(field.cells) == before + 1
    branch = [name for name in field.cells if name.startswith("scan-b")][0]
    assert field.cells[branch].regime == "diffuse"
    assert field.cells[branch].links["scan"] > 0
    assert any(event["type"] == "split" and event["cell"] == branch
               for event in report["events"])


def test_an_unused_branch_is_merged_back():
    field = _field()
    field.cells["scan"].activation = 0.9
    field.morph()
    branch = [name for name in field.cells if name.startswith("scan-b")][0]
    field.cells[branch].activation = 0.0
    field.cells["scan"].activation = 0.0
    report = field.morph()
    assert any(event["type"] == "merge" and event["cell"] == branch
               for event in report["events"])
    assert branch not in field.cells


def test_morphogenesis_survives_a_restart(tmp_path):
    field = _field(tmp_path)
    field.cells["scan"].activation = 0.9
    field.morph()
    field.save()

    restored = _field(tmp_path, autoload=True)
    assert restored.generation == field.generation
    assert set(restored.cells) == set(field.cells)
    assert set(restored.cells["scan"].links) == set(field.cells["scan"].links)
    assert restored.morph_log[-1]["type"] == field.morph_log[-1]["type"]


# ── metacognition: the field learns how wrong it is ────────────────────────

def test_overconfidence_costs_a_regime_its_gain():
    meta = Metacognition()
    meta.predict("convergent", confidence=0.95)
    result = meta.resolve(False)
    assert meta.gain["convergent"] < 1.0
    assert meta.surprise > 0.3
    assert result["error"] > 0.9
    assert meta.confidence("convergent") < 0.5


def test_underconfidence_that_succeeds_earns_gain():
    meta = Metacognition()
    meta.predict("diffuse", confidence=0.4)
    meta.resolve(True)
    assert meta.gain["diffuse"] > 1.0
    assert meta.confidence("diffuse") > 0.4


def test_accuracy_lowers_surprise():
    meta = Metacognition()
    for _ in range(6):
        meta.predict("structural", confidence=0.9)
        meta.resolve(True)
    assert meta.surprise < 0.2
    assert meta.calibration()["structural"]["attempts"] == 6


def test_resolving_without_a_prediction_is_a_no_op():
    meta = Metacognition()
    assert meta.resolve(True) == {}
    assert meta.attempts == {regime: 0 for regime in REGIMES}


def test_gain_stays_bounded_over_many_failures():
    meta = Metacognition()
    for _ in range(40):
        meta.predict("structural", confidence=1.0)
        meta.resolve(False)
    assert 0.5 <= meta.gain["structural"] <= 1.6


def test_losing_gain_weakens_the_regime():
    field = _field()
    field.metacognition.gain["convergent"] = 0.5
    _settle(field, task=1.0, competence=0.8)
    reduced = field.activation["convergent"]

    fresh = _field()
    _settle(fresh, task=1.0, competence=0.8)
    assert reduced < fresh.activation["convergent"]


# ── persistence ────────────────────────────────────────────────────────────

def test_field_survives_a_restart(tmp_path):
    field = _field(tmp_path)
    _settle(field, fatigue=0.9)
    field.metacognition.predict("convergent", 0.7)
    field.metacognition.resolve(True)
    path = field.save()
    assert os.path.isfile(path)

    restored = _field(tmp_path, autoload=True)
    assert restored.regime == field.regime
    assert restored.activation == field.activation
    assert restored.metacognition.attempts == field.metacognition.attempts
    assert restored.metacognition.gain == field.metacognition.gain
    assert set(restored.cells) == set(field.cells)


def test_a_corrupt_state_file_is_ignored(tmp_path):
    path = tmp_path / "field.json"
    path.write_text("{ not json", encoding="utf-8")
    field = _field(tmp_path, autoload=True)
    assert field.regime == "diffuse"
    assert field.steps == 0
    assert len(field.cells) == len(CELL_SEEDS)


def test_saved_state_holds_the_population_not_secrets(tmp_path):
    field = _field(tmp_path)
    _settle(field, task=1.0)
    payload = json.loads(open(field.save(), encoding="utf-8").read())
    assert payload["regime"] in REGIMES
    assert {cell["regime"] for cell in payload["cells"]} <= set(REGIMES)
    assert "signals" in payload and "metacognition" in payload and "morph_log" in payload


def test_summarize_orders_by_activation():
    field = _field()
    _settle(field, fatigue=0.9)
    lines = list(summarize(field.snapshot()))
    assert lines[0].startswith("convergent")


# ── the brain on top of the field ──────────────────────────────────────────

def test_brain_still_follows_an_explicit_instruction(tmp_path):
    brain = _brain(tmp_path)
    calls = brain.plan({"instructions": "shell: echo hi"})
    assert [call.tool for call in calls] == ["run_shell"]
    assert calls[0].arguments["command"] == "echo hi"


def test_brain_settles_before_it_plans(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: echo hi"})
    assert brain.field.regime in REGIMES
    assert brain.field.steps >= 1
    assert brain.field.metacognition.pending is not None


def test_the_planner_is_a_capability_not_the_brain(tmp_path):
    brain = _brain(tmp_path)
    assert brain.name == "adaptive-field"
    assert not isinstance(brain, DeliberativeBrain)
    assert isinstance(brain.capabilities["planner"], capability_layer.PlannerCapability)
    assert set(brain.capabilities) >= {"planner", "model", "retrieval", "probe"}


def test_the_planner_tool_composes_without_running_anything():
    result = capability_layer.planner_tool("shell: echo hi")
    assert result.ok
    assert result.meta["calls"] == [{"tool": "run_shell", "arguments": {"command": "echo hi"}}]
    assert "nothing was executed" in result.meta["note"]


def test_convergent_fields_only_its_primary_capability(tmp_path):
    brain = _brain(tmp_path)
    assert brain.candidate_capabilities("convergent") == ["planner"]


def test_diffuse_recruits_retrieval_only_when_its_cell_is_active(tmp_path):
    brain = _brain(tmp_path)
    assert "retrieval" not in brain.candidate_capabilities("diffuse")
    brain.field.cells["associate"].activation = 0.6
    assert "retrieval" in brain.candidate_capabilities("diffuse")


def test_each_regime_implies_its_own_work(tmp_path):
    brain = _brain(tmp_path)
    brain.field.signals["fatigue"] = 0.9
    assert brain.routine_for("convergent")["instructions"] == "self:reflect"
    brain.field.signals["fatigue"] = 0.0
    assert brain.routine_for("convergent")["instructions"] == "self:improve"
    assert brain.routine_for("structural")["instructions"] == "self:adapt"
    assert brain.routine_for("diffuse")["instructions"] == "self:explore"


def test_idle_proposal_follows_the_field_not_a_rotation(tmp_path):
    (tmp_path / "other").mkdir()
    tired = _brain(tmp_path)
    _prime_world(tired)
    for _ in range(20):
        tired.history.append({"at": "", "regime": "convergent", "ok": True,
                              "tools": ["git_status"], "task": ""})
    tired_proposal = tired.propose({"recent_actions": [], "queue": {}})

    curious = _brain(tmp_path / "other")
    curious_proposal = curious.propose({"recent_actions": [], "queue": {}})

    assert tired_proposal["instructions"] == "self:reflect"
    assert curious_proposal["instructions"] == "self:explore"
    assert tired_proposal["instructions"] != curious_proposal["instructions"]


def test_deliberation_prefers_the_plan_it_predicts_is_safer(tmp_path):
    brain = _brain(tmp_path)
    candidates = [
        {"source": "reckless", "calls": [ToolCall("run_shell", {"command": "rm -rf /tmp/zyphus"})]},
        {"source": "grounded", "calls": [ToolCall("rag", {"action": "query", "text": "loop"})]},
    ]
    chosen = brain.select(candidates, "structural")
    assert chosen["source"] == "grounded"
    assert chosen["risk"] < 0.5


def test_a_write_is_scored_without_claiming_a_radius(tmp_path):
    brain = _brain(tmp_path)
    risk, cost = brain.predict("write_file",
                               [ToolCall("write_file", {"path": "x.md", "content": ""})])
    assert risk == 0.45 and cost == 3.0


def test_probing_reads_before_it_overwrites(tmp_path):
    brain = _brain(tmp_path)
    target = tmp_path / "existing.md"
    target.write_text("keep me", encoding="utf-8")
    calls = brain.capabilities["probe"].compose(
        {"instructions": f'tool write_file {{"path": "{target}", "content": "new"}}'})
    assert calls and calls[0].tool == "read_file"
    assert calls[0].arguments["path"] == str(target)


def test_observe_scores_the_prediction_and_records_experience(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: echo hi"})
    regime = brain._last_regime
    resolution = brain.observe({"id": "t1", "instructions": "shell: echo hi"},
                               {"action": "executed", "tools": ["run_shell"]})
    assert resolution["regime"] == regime
    assert brain.field.metacognition.attempts[regime] == 1
    assert brain.tool_stats["run_shell"]["successes"] == 1
    assert brain.history[-1]["regime"] == regime
    assert os.path.isfile(brain.field.path)


def test_observe_counts_a_failure_against_the_regime(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: false"})
    regime = brain._last_regime
    brain.observe({"id": "t2", "instructions": "shell: false"},
                  {"action": "failed", "tool": "run_shell", "error": "boom"})
    assert brain.field.metacognition.attempts[regime] == 1
    assert brain.field.metacognition.successes[regime] == 0
    assert brain.tool_stats["run_shell"]["successes"] == 0
    assert brain.field.metacognition.surprise > 0.0


def test_failed_task_queues_a_self_check(tmp_path):
    brain = _brain(tmp_path)
    follow = brain.follow_up({"instructions": "shell: echo hi"}, {"action": "failed"})
    assert follow["instructions"] == "self:selftest"


def test_a_convergent_brain_consolidates_after_a_task(tmp_path):
    brain = _brain(tmp_path)
    brain._last_regime = "convergent"
    follow = brain.follow_up({"instructions": "shell: echo hi"}, {"action": "executed"})
    assert follow["instructions"] == "self:reflect"


def test_brain_evolves_without_a_task(tmp_path):
    brain = _brain(tmp_path)
    steps = brain.field.steps
    info = brain.evolve(6.0)
    assert brain.field.steps > steps
    assert info["regime"] in REGIMES
    assert brain.field.clock > 0


def test_snapshot_reports_the_field_for_the_dashboard(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: echo hi"})
    snapshot = brain.snapshot()
    for key in ("regime", "activations", "coalitions", "cells", "cell_count",
                "morphogenesis", "signals", "dominance", "metacognition", "history",
                "tools", "capabilities", "state_path"):
        assert key in snapshot
    assert set(snapshot["activations"]) == set(REGIMES)


def test_build_brain_returns_the_adaptive_field(tmp_path):
    from src.agent.brain import build_brain
    from src.agent import field_brain

    brain = build_brain()
    assert isinstance(brain, field_brain.AdaptiveFieldBrain)
    assert brain.name == "adaptive-field"
    assert isinstance(brain.composer, DeliberativeBrain)


# ── the loop keeps the field alive between tasks ───────────────────────────

def test_the_loop_evolves_the_field_between_ticks(tmp_path):
    from src.agent.loop import AgentLoop
    from src.agent.store import AgentStore
    from src.agent.tools import ToolRegistry

    class StubBrain:
        name = "stub"

        def __init__(self):
            self.evolved = []

        def evolve(self, seconds):
            self.evolved.append(seconds)

        def propose(self, context=None):
            return None

        def follow_up(self, task, outcome):
            return None

    brain = StubBrain()
    loop = AgentLoop(store=AgentStore(str(tmp_path / "agent.db")),
                     registry=ToolRegistry(), brain=brain, self_interval=10 ** 9)
    loop._consolidate_if_due = lambda: None
    loop._last_self_at = time.time()

    loop.tick()
    assert brain.evolved, "an idle tick must still evolve the field"

    loop._wait(0.05)
    assert len(brain.evolved) >= 2, "the wait between ticks must evolve the field too"
