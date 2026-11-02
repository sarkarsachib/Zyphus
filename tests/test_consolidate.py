"""Tests for the consolidation phase: replay, measured competence, promotion."""

import os

from src.agent import consolidate
from src.agent.store import AgentStore
from src.agent.worldmodel import WorldModel


def _phase(tmp_path):
    store = AgentStore(path=str(tmp_path / "agent.db"))
    world = WorldModel(str(tmp_path / "world.db"))
    phase = consolidate.Consolidation(store=store, world=world,
                                      path=str(tmp_path / "consolidation.db"))
    return store, world, phase


def _log(store, tool, ok, ms=10):
    store.log_action("task-1", tool, {"arg": 1}, ok, "out", "" if ok else "boom", ms)


def test_empty_store_records_a_pass_that_says_so(tmp_path):
    _, _, phase = _phase(tmp_path)

    report = phase.run()

    assert report["replayed"] == 0
    assert report["tools"] == []
    assert report["promoted"] == [] and report["weak"] == []
    latest = phase.latest()
    assert latest["passes"] == 1
    assert latest["last"]["replayed"] == 0


def test_replay_measures_outcome_and_latency(tmp_path):
    store, _, phase = _phase(tmp_path)
    for ok, ms in ((True, 10), (True, 20), (False, 30)):
        _log(store, "run_shell", ok, ms)

    report = phase.run()

    assert report["replayed"] == 3
    assert report["tools"] == [{
        "tool": "run_shell", "attempts": 3, "successes": 2,
        "success_rate": 0.667, "mean_ms": 20.0, "runs": 3,
    }]


def test_second_pass_only_replays_new_ground(tmp_path):
    store, _, phase = _phase(tmp_path)
    _log(store, "read_file", True)
    _log(store, "read_file", True)
    phase.run()

    _log(store, "read_file", False)
    report = phase.run()

    assert report["replayed"] == 1
    skill = phase.skill("read_file")
    assert skill["attempts"] == 3          # cumulative, not just this pass
    assert skill["successes"] == 2
    assert skill["passes"] == 2


def test_reliable_tool_becomes_a_world_strategy(tmp_path):
    store, world, phase = _phase(tmp_path)
    for _ in range(3):
        _log(store, "read_file", True)

    report = phase.run()

    assert report["promoted"] == ["read_file"]
    strategies = world.strategies("tool")
    assert strategies and strategies[0]["strategy"] == "read_file"
    assert strategies[0]["attempts"] == 1      # one observation per pass
    assert strategies[0]["success_rate"] == 1.0
    assert phase.skill("read_file")["promoted_at"]


def test_failing_tool_is_recorded_as_failing_not_promoted(tmp_path):
    store, world, phase = _phase(tmp_path)
    for _ in range(3):
        _log(store, "web_fetch", False)

    report = phase.run()

    assert report["weak"] == ["web_fetch"]
    assert report["promoted"] == []
    assert world.strategies("tool")[0]["success_rate"] == 0.0
    assert phase.skill("web_fetch")["promoted_at"] is None


def test_a_single_run_is_not_evidence(tmp_path):
    store, world, phase = _phase(tmp_path)
    _log(store, "vitals", True)

    report = phase.run()

    assert report["promoted"] == [] and report["weak"] == []
    assert world.strategies("tool") == []


def test_dry_run_writes_nothing(tmp_path):
    store, world, phase = _phase(tmp_path)
    for _ in range(3):
        _log(store, "read_file", True)

    report = phase.run(dry_run=True)

    assert report["replayed"] == 3
    assert report["promoted"] == ["read_file"]
    assert not os.path.exists(phase.path)
    assert world.strategies("tool") == []
    assert phase.latest()["passes"] == 0


def test_reading_latest_does_not_create_the_database(tmp_path):
    _, _, phase = _phase(tmp_path)

    latest = phase.latest()

    assert latest == {"database": phase.path, "passes": 0, "last": None, "skills": []}
    assert not os.path.exists(phase.path)


def test_should_run_once_there_is_new_ground(tmp_path):
    store, _, phase = _phase(tmp_path)
    assert phase.should_run(3) is False

    for _ in range(3):
        _log(store, "read_file", True)
    assert phase.should_run(3) is True

    phase.run()
    assert phase.should_run(3) is False
