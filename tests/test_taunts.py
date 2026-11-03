"""An idle agent is not a silent one: the loop makes him taunt the operator."""

import json
import time

from src.agent import taunts
from src.agent.loop import AgentLoop
from src.agent.store import AgentStore
from src.agent.tools import Tool, ToolRegistry, ToolResult


class StubBrain:
    """No self-directed work, so a tick can only taunt."""

    name = "stub"

    def evolve(self, seconds):
        return None

    def propose(self, context=None):
        return None

    def follow_up(self, task, outcome):
        return None


def _loop(tmp_path, spoken):
    registry = ToolRegistry()
    registry.register(Tool(
        "speak", "stub voice", {"text": "str"},
        lambda text: (spoken.append(text)
                      or ToolResult(True, output=f"said: {text}", meta={"file": "voice-1.wav"}))))
    loop = AgentLoop(store=AgentStore(str(tmp_path / "agent.db")),
                     registry=registry, brain=StubBrain(), self_interval=10 ** 9)
    loop._consolidate_if_due = lambda: None
    loop._last_self_at = time.time()
    return loop


def test_taunts_rotate_through_the_list():
    first = [taunts.taunt() for _ in range(len(taunts.TAUNTS) + 1)]
    assert len(set(first[:-1])) == len(taunts.TAUNTS)  # every line once
    assert first[0] == first[-1]                        # then it wraps


def test_idle_tick_speaks_a_taunt_and_logs_it(tmp_path):
    spoken = []
    loop = _loop(tmp_path, spoken)
    loop._last_taunt_at = 0

    result = loop.tick()

    assert result["action"] == "taunted"
    assert spoken and spoken[0] in taunts.TAUNTS
    logged = loop.store.recent_actions(tool="speak")
    assert logged and json.loads(logged[0]["arguments"])["text"] == spoken[0]


def test_taunts_respect_the_interval(tmp_path):
    spoken = []
    loop = _loop(tmp_path, spoken)
    loop._last_taunt_at = time.time()

    assert loop.tick()["action"] != "taunted"
    assert spoken == []
