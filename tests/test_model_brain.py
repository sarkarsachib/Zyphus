"""Tests for the model-backed brain with a mocked API."""

import json
from unittest.mock import patch

from src.agent.brain import DeliberativeBrain
from src.agent.model_brain import ModelBrain, _extract_json


def _mock_brain(reply_json: str):
    brain = ModelBrain(fallback=DeliberativeBrain(), api_key_env="FAKE_KEY")
    brain.api_key_env = "FAKE_KEY"
    import os
    os.environ["FAKE_KEY"] = "test-key"
    return brain


def test_extract_json_plain():
    result = _extract_json('{"tool_calls": [{"tool": "run_shell"}]}')
    assert "tool_calls" in result


def test_extract_json_in_code_block():
    result = _extract_json('```json\n{"tool_calls": []}\n```')
    assert result == {"tool_calls": []}


def test_extract_json_with_prose():
    result = _extract_json('Here you go:\n{"tool_calls": [{"tool": "vitals"}]}\nDone.')
    assert len(result["tool_calls"]) == 1


def test_plan_falls_back_on_no_key():
    import os
    os.environ.pop("FAKE_KEY2", None)
    brain = ModelBrain(fallback=DeliberativeBrain(), api_key_env="FAKE_KEY2")
    calls = brain.plan({"instructions": "shell: echo hi"})
    assert len(calls) == 1
    assert calls[0].tool == "run_shell"


def test_plan_uses_model_reply():
    brain = _mock_brain("")
    reply = json.dumps({"tool_calls": [{"tool": "run_shell", "arguments": {"command": "echo ok"}}]})
    with patch.object(brain, "_chat", return_value=reply):
        calls = brain.plan({"instructions": "run something"})
    assert len(calls) == 1
    assert calls[0].tool == "run_shell"
    assert calls[0].arguments["command"] == "echo ok"


def test_plan_rejects_unknown_tool():
    brain = _mock_brain("")
    reply = json.dumps({"tool_calls": [{"tool": "no_such_tool", "arguments": {}}]})
    with patch.object(brain, "_chat", return_value=reply):
        calls = brain.plan({"instructions": "do something"})
    # Falls back since no usable calls
    assert calls[0].tool != "no_such_tool"


def test_propose_uses_model_reply():
    brain = _mock_brain("")
    reply = json.dumps({"title": "Check the engine", "instructions": "self:selftest"})
    with patch.object(brain, "_chat", return_value=reply):
        proposal = brain.propose({"recent_actions": []})
    assert proposal is not None
    assert proposal["instructions"] == "self:selftest"
    assert proposal["title"] == "Check the engine"


def test_propose_rejects_unknown_routine():
    brain = _mock_brain("")
    reply = json.dumps({"title": "Hack the planet", "instructions": "self:hack"})
    with patch.object(brain, "_chat", return_value=reply):
        proposal = brain.propose({"recent_actions": []})
    # Falls back to deliberative brain
    assert proposal is not None
    assert proposal["instructions"].startswith("self:")
    assert proposal["instructions"] != "self:hack"


def test_propose_falls_back_on_bad_reply():
    brain = _mock_brain("")
    with patch.object(brain, "_chat", return_value="not json at all"):
        proposal = brain.propose({"recent_actions": []})
    assert proposal is not None
    assert proposal["instructions"].startswith("self:")
