"""The adaptive cognitive field: dynamics, metacognition, persistence, and the brain on top."""

import json
import os

import pytest

from src.agent import substrate
from src.agent.brain import DeliberativeBrain, ToolCall
from src.agent.field import ATTRACTORS, CognitiveField, Metacognition, summarize
from src.agent.field_brain import AdaptiveFieldBrain


@pytest.fixture(autouse=True)
def isolated_substrate(monkeypatch):
    """The substrate's last structure is process-global; these tests own their state."""
    monkeypatch.setattr(substrate, "last", lambda: {})


def _field(tmp_path=None, autoload=False):
    path = str(tmp_path / "field.json") if tmp_path is not None else "/tmp/zyphus-test-field.json"
    return CognitiveField(path=path, autoload=autoload)


def _settle(field, **signals):
    field.perceive(signals)
    return field.step()


def _brain(tmp_path, **kwargs):
    return AdaptiveFieldBrain(composer=DeliberativeBrain(notes_dir=str(tmp_path / "notes")),
                              field=_field(tmp_path), world_path=str(tmp_path / "world.db"),
                              **kwargs)


# ── dynamics: the mode is an equilibrium, not a decision ────────────────────

def test_quiet_field_keeps_the_default_mode():
    field = _field()
    assert _settle(field) == "plan"
    assert max(field.activation.values()) == 0.0


def test_a_waiting_task_settles_into_plan():
    field = _field()
    assert _settle(field, task=1.0, competence=0.8) == "plan"
    assert field.activation["plan"] > 0.5


def test_an_unmapped_world_settles_into_explore():
    field = _field()
    assert _settle(field, novelty=0.9, uncertainty=0.5) == "explore"
    assert field.activation["explore"] > field.activation["plan"]


def test_surprise_and_stagnation_settle_into_deliberation():
    field = _field()
    mode = _settle(field, surprise=0.8, stagnation=1.0, uncertainty=0.7)
    assert mode == "deliberate"
    assert field.activation["deliberate"] > field.activation["plan"]


def test_repetition_settles_into_inhibition():
    field = _field()
    mode = _settle(field, fatigue=0.9, competence=0.8)
    assert mode == "inhibit"


def test_negative_coupling_keeps_exploration_off_a_waiting_task():
    field = _field()
    assert _settle(field, task=1.0, novelty=1.0, competence=0.8) == "plan"


def test_satiation_tires_the_dominant_attractor():
    field = _field()
    field.perceive({"task": 1.0, "competence": 0.8})
    field.step()
    peak = field.activation["plan"]
    for _ in range(6):
        field.step()
    assert field.satiation["plan"] > 0.1
    assert field.activation["plan"] < peak


def test_a_long_gap_relaxes_the_field(tmp_path):
    field = _field(tmp_path)
    field.perceive({"task": 1.0})
    field.step()
    hot = field.activation["plan"]
    field.perceive({})  # nothing happening any more
    field.step(seconds=12.0)
    assert field.activation["plan"] < hot


def test_hysteresis_stops_the_mode_flickering():
    field = _field()
    field.mode = "plan"
    field.activation = {"plan": 0.30, "explore": 0.33, "deliberate": 0.0, "inhibit": 0.0}
    field._settle_mode("explore")          # a margin inside the band changes nothing
    assert field.mode == "plan"

    field.activation["explore"] = 0.40     # a clear margin does
    field._settle_mode("explore")
    assert field.mode == "explore"
    assert field.transitions[-1]["from"] == "plan"


def test_perception_clamps_and_forgets_stale_signals():
    field = _field()
    field.perceive({"task": 5.0, "novelty": -3, "unknown": 1.0})
    assert field.signals["task"] == 1.0
    assert field.signals["novelty"] == 0.0
    assert field.signals["surprise"] == 0.0


# ── metacognition: the field learns how wrong it is ────────────────────────

def test_overconfidence_costs_a_mode_its_gain():
    meta = Metacognition()
    meta.predict("plan", confidence=0.95)
    result = meta.resolve(False)
    assert meta.gain["plan"] < 1.0
    assert meta.surprise > 0.3
    assert result["error"] > 0.9
    assert meta.confidence("plan") < 0.5


def test_underconfidence_that_succeeds_earns_gain():
    meta = Metacognition()
    meta.predict("explore", confidence=0.4)
    meta.resolve(True)
    assert meta.gain["explore"] > 1.0
    assert meta.confidence("explore") > 0.4


def test_accuracy_lowers_surprise():
    meta = Metacognition()
    for _ in range(6):
        meta.predict("plan", confidence=0.9)
        meta.resolve(True)
    assert meta.surprise < 0.2
    assert meta.calibration()["plan"]["attempts"] == 6


def test_resolving_without_a_prediction_is_a_no_op():
    meta = Metacognition()
    assert meta.resolve(True) == {}
    assert meta.attempts == {name: 0 for name in ATTRACTORS}


def test_gain_stays_bounded_over_many_failures():
    meta = Metacognition()
    for _ in range(40):
        meta.predict("deliberate", confidence=1.0)
        meta.resolve(False)
    assert 0.5 <= meta.gain["deliberate"] <= 1.6


def test_losing_gain_weakens_the_attractor():
    field = _field()
    field.metacognition.gain["plan"] = 0.5
    _settle(field, task=1.0, competence=0.8)
    reduced = field.activation["plan"]

    fresh = _field()
    _settle(fresh, task=1.0, competence=0.8)
    assert reduced < fresh.activation["plan"]


# ── persistence ────────────────────────────────────────────────────────────

def test_field_survives_a_restart(tmp_path):
    field = _field(tmp_path)
    _settle(field, fatigue=0.9)
    field.metacognition.predict("inhibit", 0.7)
    field.metacognition.resolve(True)
    path = field.save()
    assert os.path.isfile(path)

    restored = _field(tmp_path, autoload=True)
    assert restored.mode == field.mode
    assert restored.activation == field.activation
    assert restored.metacognition.attempts == field.metacognition.attempts
    assert restored.metacognition.gain == field.metacognition.gain


def test_a_corrupt_state_file_is_ignored(tmp_path):
    path = tmp_path / "field.json"
    path.write_text("{ not json", encoding="utf-8")
    field = _field(tmp_path, autoload=True)
    assert field.mode == "plan"
    assert field.steps == 0


def test_saved_state_holds_no_secret_values(tmp_path):
    field = _field(tmp_path)
    _settle(field, task=1.0)
    payload = json.loads(open(field.save(), encoding="utf-8").read())
    assert set(payload["activation"]) == set(ATTRACTORS)
    assert "signals" in payload and "metacognition" in payload


def test_summarize_orders_by_activation():
    field = _field()
    _settle(field, fatigue=0.9)
    lines = list(summarize(field.snapshot()))
    assert lines[0].startswith("inhibit")


# ── the brain on top of the field ──────────────────────────────────────────

def test_brain_still_follows_an_explicit_instruction(tmp_path):
    brain = _brain(tmp_path)
    calls = brain.plan({"instructions": "shell: echo hi"})
    assert [call.tool for call in calls] == ["run_shell"]
    assert calls[0].arguments["command"] == "echo hi"


def test_brain_settles_before_it_plans(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: echo hi"})
    assert brain.field.mode in ATTRACTORS
    assert brain.field.steps >= 1
    assert brain.field.metacognition.pending is not None


def test_each_mode_implies_its_own_work(tmp_path):
    brain = _brain(tmp_path)
    assert brain.routine_for("inhibit")["instructions"] == "self:reflect"
    assert brain.routine_for("explore")["instructions"] == "self:explore"
    assert brain.routine_for("plan")["instructions"] == "self:improve"
    assert brain.routine_for("deliberate")["instructions"].startswith("self:")


def test_idle_proposal_follows_the_field_not_a_rotation(tmp_path):
    tired = _brain(tmp_path)
    for _ in range(20):
        tired.history.append({"at": "", "mode": "plan", "ok": True, "tools": ["git_status"], "task": ""})
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
    chosen = brain.select(candidates, "deliberate")
    assert chosen["source"] == "grounded"
    assert chosen["risk"] < 0.5


def test_a_write_is_scored_without_claiming_a_radius(tmp_path):
    brain = _brain(tmp_path)
    risk, cost = brain.predict("write_file", [ToolCall("write_file", {"path": "x.md", "content": ""})])
    assert risk == 0.45 and cost == 3.0


def test_explore_mode_reads_before_it_overwrites(tmp_path):
    brain = _brain(tmp_path)
    target = tmp_path / "existing.md"
    target.write_text("keep me", encoding="utf-8")
    calls = brain._read_before_write([ToolCall("write_file", {"path": str(target), "content": "new"})])
    assert calls is not None and calls[0].tool == "read_file"
    assert brain._read_before_write([ToolCall("write_file", {"path": "/tmp/fresh.md"})]) is None


def test_observe_scores_the_prediction_and_records_experience(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: echo hi"})
    resolution = brain.observe({"id": "t1", "instructions": "shell: echo hi"},
                               {"action": "executed", "tools": ["run_shell"]})
    assert resolution["mode"] == "plan"
    assert brain.field.metacognition.attempts["plan"] == 1
    assert brain.tool_stats["run_shell"]["successes"] == 1
    assert brain.history[-1]["ok"] is True
    assert os.path.isfile(brain.field.path)


def test_observe_counts_a_failure_against_the_mode(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: false"})
    brain.observe({"id": "t2", "instructions": "shell: false"},
                  {"action": "failed", "tool": "run_shell", "error": "boom"})
    assert brain.field.metacognition.attempts["plan"] == 1
    assert brain.field.metacognition.successes["plan"] == 0
    assert brain.tool_stats["run_shell"]["successes"] == 0
    assert brain.field.metacognition.surprise > 0.0


def test_failed_task_queues_a_self_check(tmp_path):
    brain = _brain(tmp_path)
    follow = brain.follow_up({"instructions": "shell: echo hi"}, {"action": "failed"})
    assert follow["instructions"] == "self:selftest"


def test_inhibited_brain_consolidates_after_a_task(tmp_path):
    brain = _brain(tmp_path)
    brain._last_mode = "inhibit"
    follow = brain.follow_up({"instructions": "shell: echo hi"}, {"action": "executed"})
    assert follow["instructions"] == "self:reflect"


def test_snapshot_reports_the_field_for_the_dashboard(tmp_path):
    brain = _brain(tmp_path)
    brain.plan({"instructions": "shell: echo hi"})
    snapshot = brain.snapshot()
    for key in ("mode", "activations", "signals", "satiation", "dominance",
                "metacognition", "history", "tools", "state_path"):
        assert key in snapshot
    assert set(snapshot["activations"]) == set(ATTRACTORS)


def test_build_brain_returns_the_adaptive_field(tmp_path):
    from src.agent.brain import build_brain
    from src.agent import field_brain

    brain = build_brain()
    assert isinstance(brain, field_brain.AdaptiveFieldBrain)
    assert brain.name == "adaptive-field"
    assert isinstance(brain.composer, DeliberativeBrain)
