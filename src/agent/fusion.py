"""
Working model fusion engine — stdlib only, no random traits.

Replaces the stub `llm_superfusing_engine_adapter.py` that faked cognitive
traits with `random.uniform`.  This module fuses multiple model responses into
one by scoring each response on real, deterministic signals (length, structure,
keyword density, code-block presence) and producing a weighted blend.  It also
extracts cognitive traits from text the same way — no randomness, no guesses.

Used by the agent's `fuse` tool and available as a library from the brain.
"""

import re
import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── deterministic trait scoring ─────────────────────────────────────────────

_CODE_BLOCK = re.compile(r"```[\s\S]*?```")
_URL = re.compile(r"https?://\S+")
_WORD = re.compile(r"[a-zA-Z]{2,}")


def _score_response(text: str) -> Dict[str, float]:
    """Deterministic cognitive-trait scores for a block of text."""
    text = (text or "").strip()
    if not text:
        return {k: 0.0 for k in
                ("reasoning", "creativity", "accuracy", "depth", "clarity", "coherence")}

    words = _WORD.findall(text)
    word_count = len(words)
    sentences = re.split(r"[.!?]+", text)
    sentence_count = max(1, len([s for s in sentences if s.strip()]))
    avg_sentence = word_count / sentence_count

    has_code = bool(_CODE_BLOCK.search(text))
    has_structure = any(m in text for m in ("1.", "2.", "- ", "* ", "##", "•"))
    has_urls = bool(_URL.search(text))
    unique_words = len(set(w.lower() for w in words))
    lexical_diversity = unique_words / max(1, word_count)

    return {
        "reasoning": round(min(1.0, (word_count / 200) * (1.5 if has_structure else 0.8)), 3),
        "creativity": round(min(1.0, lexical_diversity * 1.8), 3),
        "accuracy": round(min(1.0, (0.5 + 0.3 * has_code + 0.2 * has_urls)), 3),
        "depth": round(min(1.0, (word_count / 150) + (0.2 if has_code else 0)), 3),
        "clarity": round(min(1.0, 1.0 - min(0.6, avg_sentence / 60)), 3),
        "coherence": round(min(1.0, 0.4 + lexical_diversity * 0.6), 3),
    }


# ── fusion core ─────────────────────────────────────────────────────────────

@dataclass
class FusionCore:
    """One model's contribution to the fusion."""
    id: str
    source: str
    response: str = ""
    traits: Dict[str, float] = field(default_factory=dict)
    weight: float = 0.0
    processed: int = 0

    def score(self) -> Dict[str, float]:
        self.traits = _score_response(self.response)
        self.weight = sum(self.traits.values()) / max(1, len(self.traits))
        self.processed += 1
        return self.traits


class FusionEngine:
    """Combine multiple model responses into a single best answer."""

    def __init__(self) -> None:
        self.cores: List[FusionCore] = []
        self.history: List[Dict[str, Any]] = []
        self.fusions = 0

    def add_response(self, source: str, response: str) -> FusionCore:
        core = FusionCore(
            id=hashlib.md5(f"{source}:{time.time()}".encode()).hexdigest()[:10],
            source=source,
            response=response,
        )
        core.score()
        self.cores.append(core)
        return core

    def fuse(self, responses: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Fuse a list of {"source": ..., "response": ...} dicts.

        If *responses* is omitted, fuses the cores already added.
        Returns the winning response, the weighted blend, and per-core traits.
        """
        if responses:
            self.cores = []
            for entry in responses:
                self.add_response(entry.get("source", "unknown"),
                                  entry.get("response", ""))

        if not self.cores:
            return {"error": "no responses to fuse", "fused": "", "cores": []}

        ranked = sorted(self.cores, key=lambda c: c.weight, reverse=True)
        winner = ranked[0]

        # weighted trait blend
        total_weight = sum(c.weight for c in self.cores) or 1.0
        trait_keys = winner.traits.keys()
        blended_traits = {
            k: round(sum(c.traits.get(k, 0) * c.weight for c in self.cores) / total_weight, 3)
            for k in trait_keys
        }

        # consensus: merge unique lines from all responses, winner first
        seen: set = set()
        merged_lines: List[str] = []
        for core in ranked:
            for line in core.response.splitlines():
                stripped = line.strip()
                if stripped and stripped not in seen:
                    seen.add(stripped)
                    merged_lines.append(line)

        fused_text = "\n".join(merged_lines[:50])  # cap at 50 lines

        result = {
            "fused": fused_text,
            "winner": winner.source,
            "winner_weight": round(winner.weight, 3),
            "blended_traits": blended_traits,
            "cores": [
                {"source": c.source, "weight": round(c.weight, 3), "traits": c.traits}
                for c in ranked
            ],
            "algorithm": "weighted_consensus",
        }
        self.fusions += 1
        self.history.append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), **result})
        return result

    def traits(self, text: str) -> Dict[str, float]:
        """Extract cognitive traits from a single text (no fusion)."""
        return _score_response(text)

    def status(self) -> Dict[str, Any]:
        return {
            "cores": len(self.cores),
            "fusions": self.fusions,
            "algorithms": ["weighted_consensus", "trait_scoring"],
            "history": self.history[-10:],
        }
