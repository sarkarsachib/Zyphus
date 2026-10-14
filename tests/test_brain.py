"""Tests for the deliberative brain's planning and self-direction."""

from src.agent.brain import DeliberativeBrain, ToolCall


def _brain():
    return DeliberativeBrain(notes_dir="/tmp/zyphus-test-notes")


def test_shell_prefix():
    calls = _brain().plan({"instructions": "shell: echo hello"})
    assert len(calls) == 1
    assert calls[0].tool == "run_shell"
    assert calls[0].arguments["command"] == "echo hello"


def test_say_prefix():
    calls = _brain().plan({"instructions": "say: hello world"})
    assert len(calls) == 1
    assert calls[0].tool == "speak"
    assert calls[0].arguments["text"] == "hello world"


def test_explicit_tool():
    calls = _brain().plan({"instructions": 'tool: run_shell {"command": "ls"}'})
    assert len(calls) == 1
    assert calls[0].tool == "run_shell"
    assert calls[0].arguments["command"] == "ls"


def test_plain_english_read_file():
    calls = _brain().plan({"instructions": "read src/agent/brain.py"})
    assert any(c.tool == "read_file" for c in calls)


def test_vitals_keyword():
    calls = _brain().plan({"instructions": "check vitals"})
    assert len(calls) == 1
    assert calls[0].tool == "vitals"


def test_search_keyword():
    calls = _brain().plan({"instructions": 'search for "heartbeat" in the code'})
    assert len(calls) == 1
    assert calls[0].tool == "run_shell"
    assert "grep" in calls[0].arguments["command"]


def test_self_inspect():
    calls = _brain().plan({"instructions": "self:inspect"})
    assert len(calls) == 2
    assert calls[0].tool == "read_file"
    assert calls[1].tool == "write_file"


def test_propose_returns_routine():
    brain = _brain()
    proposal = brain.propose({"recent_actions": [{"ok": True}], "recent_tasks": []})
    assert proposal is not None
    assert "title" in proposal
    assert "instructions" in proposal
    assert proposal["instructions"].startswith("self:")


def test_propose_prioritises_selftest_on_failure():
    brain = _brain()
    # With failures, selftest is inserted at front of the rotation order,
    # so it should appear within the first few proposals.
    proposals = [brain.propose({"recent_actions": [{"ok": False}], "recent_tasks": []})
                for _ in range(6)]
    routines = [p["instructions"] for p in proposals]
    assert "self:selftest" in routines
    # Without failures, selftest should appear later
    brain2 = _brain()
    proposals_ok = [brain2.propose({"recent_actions": [{"ok": True}], "recent_tasks": []})
                    for _ in range(2)]
    assert all(p["instructions"] != "self:selftest" for p in proposals_ok)


def test_follow_up_after_inspect():
    brain = _brain()
    follow = brain.follow_up({"instructions": "self:inspect"}, {"action": "executed"})
    assert follow is not None
    assert follow["instructions"] == "self:reflect"


def test_follow_up_on_failure():
    brain = _brain()
    follow = brain.follow_up({"instructions": "shell: false"}, {"action": "failed"})
    assert follow is not None
    assert follow["instructions"] == "self:selftest"


def test_follow_up_returns_none_for_generic_task():
    brain = _brain()
    follow = brain.follow_up({"instructions": "vitals"}, {"action": "executed"})
    assert follow is None
