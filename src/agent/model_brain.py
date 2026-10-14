"""
The model-backed brain: a stronger planner when an API key is configured.

It speaks to any OpenAI-compatible chat endpoint (`OPENAI_API_KEY`, optionally
`ZYPHUS_MODEL_BASE_URL` and `ZYPHUS_MODEL`), asks for a JSON plan of tool calls
drawn from the live tool catalogue, and validates every call against that
catalogue before returning it. Any failure at all - no key, no network, a bad
reply, an unknown tool - falls back to the local `DeliberativeBrain`, so the
agent is never dependent on a model being reachable.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are the planning half of an autonomous agent running inside its own container. "
    "Reply with JSON only, no prose: {\"tool_calls\": [{\"tool\": \"<name>\", \"arguments\": {...}}]}. "
    "Use only the tools listed. Prefer short plans of one to three calls. "
    'A string argument may contain "$last" to reuse the previous call\'s output.'
)

PROPOSE_PROMPT = (
    "You are the self-directed half of an autonomous agent running inside its own code repository. "
    "You are idle and must propose one productive thing to do next: inspect a source file, reflect on "
    "recent work, report your body state, run a self-check, or inventory the codebase. "
    "Reply with JSON only: {\"title\": \"<short label>\", \"instructions\": \"<one of: "
    "self:inspect, self:reflect, self:voice, self:selftest, self:inventory>\"}. "
    "Choose based on what the agent has been doing and its recent success rate."
)


class ModelBrain:
    name = "model+deliberative"

    def __init__(self, fallback, base_url: Optional[str] = None, model: Optional[str] = None,
                 api_key_env: str = "OPENAI_API_KEY"):
        self.fallback = fallback
        self.api_key_env = api_key_env
        self.base_url = (base_url or os.environ.get("ZYPHUS_MODEL_BASE_URL")
                         or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("ZYPHUS_MODEL") or DEFAULT_MODEL
        self.failures = 0

    def available(self) -> bool:
        return bool(os.environ.get(self.api_key_env))

    # --- the loop's interface ------------------------------------------------

    def plan(self, task: Dict[str, Any]) -> List:
        try:
            calls = self._ask_for_plan(task)
        except Exception:
            self.failures += 1
            return self.fallback.plan(task)
        return calls or self.fallback.plan(task)

    def propose(self, context: Optional[Dict[str, Any]] = None):
        try:
            proposal = self._ask_for_proposal(context or {})
        except Exception:
            self.failures += 1
            return self.fallback.propose(context)
        if not proposal:
            return self.fallback.propose(context)
        return proposal

    def follow_up(self, task: Dict[str, Any], outcome: Dict[str, Any]):
        return self.fallback.follow_up(task, outcome)

    def _ask_for_proposal(self, context: Dict[str, Any]) -> Optional[Dict[str, str]]:
        recent = context.get("recent_actions") or []
        summary = [
            f"- {a.get('tool', '?')}: {'ok' if a.get('ok') else 'failed'}"
            for a in recent[-10:]
        ]
        task_lines = [
            f"- [{t.get('status', '?')}] {t.get('title', '?')}"
            for t in (context.get("recent_tasks") or [])[-8:]
        ]
        user_content = (
            f"Recent actions:\n{chr(10).join(summary) or '(none)'}\n\n"
            f"Recent tasks:\n{chr(10).join(task_lines) or '(none)'}\n\n"
            f"Notes on disk: {len(context.get('notes', []))} files\n\n"
            "Propose one self-directed task."
        )
        reply = self._chat([
            {"role": "system", "content": PROPOSE_PROMPT},
            {"role": "user", "content": user_content},
        ])
        payload = _extract_json(reply)
        title = str(payload.get("title", "")).strip()
        instructions = str(payload.get("instructions", "")).strip()
        if not title or not instructions:
            raise ValueError("model returned no usable proposal")
        valid = {"self:inspect", "self:reflect", "self:voice", "self:selftest", "self:inventory"}
        if instructions not in valid:
            raise ValueError(f"model proposed an unknown routine: {instructions}")
        return {"title": title[:80], "instructions": instructions}

    # --- the model call ------------------------------------------------------

    def _ask_for_plan(self, task: Dict[str, Any]) -> List:
        from src.agent.brain import ToolCall
        from src.agent.tools import build_registry

        catalog = build_registry().catalog()
        catalogue_text = "\n".join(
            f"- {tool['name']}({', '.join(tool['parameters'])}): {tool['description']}"
            for tool in catalog
        )
        known = {tool["name"] for tool in catalog}
        reply = self._chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Tools available:\n{catalogue_text}\n\nTask: {task.get('instructions', '')}"},
        ])
        payload = _extract_json(reply)
        calls = []
        for entry in payload.get("tool_calls", []):
            name = str(entry.get("tool", "")).strip()
            if name in known:
                arguments = entry.get("arguments") or {}
                calls.append(ToolCall(name, arguments if isinstance(arguments, dict) else {}))
        if not calls:
            raise ValueError("model returned no usable tool calls")
        return calls

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        body = json.dumps({"model": self.model, "messages": messages,
                           "temperature": 0.2, "response_format": {"type": "json_object"}}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {os.environ[self.api_key_env]}"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        return payload["choices"][0]["message"]["content"]


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in the model's reply")
    return json.loads(text[start:end + 1])
