"""
What the field can recruit.

The old planner used to *be* the brain: every task went through
`DeliberativeBrain.plan` first. Now it is one capability among several, listed
here with the regime that tends to recruit it:

    planner     structural / convergent   turn instructions into tool calls
    model       structural                ask a configured model for a plan
    retrieval   diffuse / structural      ground the plan in the local index
    probe       diffuse                   look before overwriting anything

`AdaptiveFieldBrain` asks these for candidate call lists and lets the winning
coalition choose. The planner is also registered as the `planner` tool, so a
task can call it directly the same way it calls any other capability.
"""

import os
import re
from typing import Any, Callable, Dict, List, Optional

from src.agent.brain import DeliberativeBrain, ToolCall
from src.agent.field import HORIZON_SECONDS
from src.agent.tools import ToolResult, _payload_result

QUESTION = re.compile(r"\b(why|how|what|where|which|who|explain|understand|investigate|"
                      r"diagnose|cause|reason)\b", re.IGNORECASE)


class Capability:
    """One thing the field can do when a coalition recruits it."""

    name = "capability"
    regime = "structural"
    description = ""

    def available(self) -> bool:
        return True

    def compose(self, task: Dict[str, Any]) -> List[ToolCall]:
        return []


class PlannerCapability(Capability):
    """The deliberative planner, demoted from brain to capability."""

    name = "planner"
    regime = "structural"
    description = "Turn plain-English instructions into a short chain of tool calls."

    def __init__(self, composer: DeliberativeBrain):
        self.composer = composer

    def compose(self, task: Dict[str, Any]) -> List[ToolCall]:
        return list(self.composer.plan(task))


class ModelCapability(Capability):
    """A configured model endpoint as one more voice, not the decision."""

    name = "model"
    regime = "structural"
    description = "Ask the active model endpoint for a plan."

    def __init__(self, model: Optional[Any]):
        self.model = model

    def available(self) -> bool:
        if self.model is None:
            return False
        try:
            return bool(self.model.available())
        except Exception:
            return False

    def compose(self, task: Dict[str, Any]) -> List[ToolCall]:
        if not self.available():
            return []
        try:
            return list(self.model.plan(task) or [])
        except Exception:
            return []


class RetrievalCapability(Capability):
    """Ground a composed plan in what the local index already holds."""

    name = "retrieval"
    regime = "diffuse"
    description = "Query the local retrieval index before the plan runs."

    def __init__(self, planner: PlannerCapability,
                 index_chunks: Optional[Callable[[], int]] = None):
        self.planner = planner
        self.index_chunks = index_chunks or (lambda: 0)

    def compose(self, task: Dict[str, Any]) -> List[ToolCall]:
        instructions = (task.get("instructions") or "").strip()
        if not instructions or not self.index_chunks():
            return []
        if not (QUESTION.search(instructions) or len(instructions) > 20):
            return []
        calls = list(self.planner.compose(task))
        return [ToolCall("rag", {"action": "query", "text": instructions[:160]})] + calls


class ProbeCapability(Capability):
    """Look at a file before a composed plan overwrites it."""

    name = "probe"
    regime = "diffuse"
    description = "Read a target that the plan is about to overwrite."

    def __init__(self, planner: PlannerCapability):
        self.planner = planner

    def compose(self, task: Dict[str, Any]) -> List[ToolCall]:
        calls = list(self.planner.compose(task))
        for call in calls[:2]:
            if call.tool != "write_file":
                continue
            path = str((call.arguments or {}).get("path") or "")
            if path and os.path.exists(path):
                return [ToolCall("read_file", {"path": path})] + calls
        return []


def default_capabilities(composer: DeliberativeBrain, model: Optional[Any] = None,
                         index_chunks: Optional[Callable[[], int]] = None
                         ) -> Dict[str, Capability]:
    planner = PlannerCapability(composer)
    capabilities: List[Capability] = [
        planner,
        ModelCapability(model),
        RetrievalCapability(planner, index_chunks),
        ProbeCapability(planner),
    ]
    return {capability.name: capability for capability in capabilities}


def planner_tool(instructions: str = "", notes_dir: str = "") -> ToolResult:
    """The planner as a tool: compose calls for an instruction, run nothing."""
    instructions = (instructions or "").strip()
    if not instructions:
        return ToolResult(False, error="instructions are required")
    composer = DeliberativeBrain(notes_dir or "devmind/agent/notes")
    calls = composer.plan({"instructions": instructions})
    return _payload_result({
        "capability": "planner",
        "instructions": instructions,
        "calls": [{"tool": call.tool, "arguments": call.arguments} for call in calls],
        "note": "composed only - nothing was executed",
    })


def field_tool(action: str = "status", seconds: float = 0.0) -> ToolResult:
    """Inspect, advance or restructure the brain's own cognitive field."""
    from src.agent.loop import get_loop

    brain = get_loop().brain
    field = getattr(brain, "field", None)
    if field is None:
        return ToolResult(False, error=f"brain {brain.name} keeps no cognitive field")

    action = (action or "status").lower()
    if action in ("status", "show"):
        return _payload_result(brain.snapshot())
    if action in ("evolve", "step"):
        brain.evolve(seconds or HORIZON_SECONDS)
        return _payload_result({"action": "evolved", "field": brain.snapshot()})
    if action in ("morph", "restructure"):
        report = field.morph()
        try:
            field.save()
        except OSError:
            pass
        return _payload_result({"action": "morphed", "morph": report, "field": brain.snapshot()})
    return ToolResult(False, error=f"unknown field action '{action}' - use status, evolve or morph")
