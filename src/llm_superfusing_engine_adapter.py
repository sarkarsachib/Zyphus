"""
SuperFusing engine adapter - deterministic, measurement-driven.

This module used to be a stub: it seeded every "cognitive trait" with
`random.uniform(...)`, picked its algorithm with `random.choice(...)`, and then
reported numbers that meant nothing. It now delegates all scoring to
`src.agent.fusion`, which scores text on real signals (length, structure,
keyword density, code blocks, lexical diversity) with no randomness at all.

A core holds no traits until a response is actually recorded for it, and a
fusion with nothing recorded fails honestly instead of inventing an answer.
The public surface is unchanged, so existing callers keep working:

    engine = LLMSuperFusingEngine()
    await engine.initialize()
    await engine.fuse_models({"responses": [{"source": "Claude", "response": "..."}]})
    await engine.get_system_status()
"""

import hashlib
import json
import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional

from src.agent.fusion import FusionEngine, _score_response


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


class FusionCore:
    """One model's measured contribution to the fusion."""

    def __init__(self, core_id: str, model_source: str):
        self.id = core_id
        self.model_source = model_source
        self.stability = 0.0
        self.active = True
        self.processed_requests = 0
        self.successful_fusions = 0
        self.cognitive_traits: Dict[str, float] = {}
        self.integration_strength = 0.0
        self.responses: List[str] = []
        self.observations: List[Dict[str, float]] = []
        self.created_at = time.time()

    @property
    def measured(self) -> bool:
        return bool(self.observations)

    def observe(self, text: str) -> Dict[str, float]:
        """Record a real response and re-derive this core's traits from it."""
        traits = _score_response(text)
        self.responses.append(text)
        self.observations.append(traits)
        self.cognitive_traits = {
            name: round(_mean([obs.get(name, 0.0) for obs in self.observations]), 3)
            for name in traits
        }
        self.processed_requests += 1
        self.integration_strength = round(_mean(list(self.cognitive_traits.values())), 3)
        self.stability = self.calculate_stability()
        return traits

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Score one input through this core."""
        if isinstance(input_data, dict):
            text = (input_data.get("text") or input_data.get("response")
                    or json.dumps(input_data, default=str))
        else:
            text = str(input_data)
        traits = self.observe(text)
        return {
            "core_id": self.id,
            "model": self.model_source,
            "processed": True,
            "traits": traits,
            "stability": self.stability,
            "integration_strength": self.integration_strength,
        }

    def calculate_stability(self) -> float:
        """How consistent this core's real observations are.

        No observations means no measurement, and that is reported as 0.0 -
        not as a confident default.
        """
        if not self.observations:
            return 0.0
        scores = [_mean(list(obs.values())) for obs in self.observations]
        mean = _mean(scores)
        spread = (max(scores) - min(scores)) / max(mean, 1e-9)
        consistency = max(0.0, 1.0 - spread)
        success_rate = self.successful_fusions / max(1, self.processed_requests)
        return round(0.6 * consistency + 0.4 * success_rate, 3)


class LLMSuperFusingEngine:
    """Fuse real model responses; every number comes from measured text."""

    def __init__(self):
        self.initialized = False
        self.fusion_cores: List[FusionCore] = []
        self.fusion_history = deque(maxlen=500)
        self.cognitive_weights: Dict[str, Dict[str, float]] = {}
        self.fusion_algorithms = ["weighted_consensus", "trait_scoring"]
        self._engine = FusionEngine()
        self._initialize_cores()

    def _initialize_cores(self):
        """Create one core per known model source - with no invented traits."""
        sources = ["GPT-4", "Claude", "LLaMA", "Gemini", "Mistral"]
        for index, source in enumerate(sources):
            self.fusion_cores.append(FusionCore(f"core_{index + 1}", source))

    def _core(self, model_source: str) -> Optional[FusionCore]:
        return next((c for c in self.fusion_cores if c.model_source == model_source), None)

    async def initialize(self):
        """Mark the engine ready; cores stay unmeasured until data arrives."""
        self.initialized = True
        self._record_fusion_event("initialized", {
            "cores": len(self.fusion_cores),
            "measured_cores": len([c for c in self.fusion_cores if c.measured]),
        })
        return {"success": True, "cores": len(self.fusion_cores),
                "measured_cores": len([c for c in self.fusion_cores if c.measured])}

    def _record_fusion_event(self, event_type: str, data: Dict[str, Any]):
        self.fusion_history.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "data": data,
        })

    def record_response(self, model_source: str, text: str) -> Dict[str, Any]:
        """Attach a real response to a model core, adding the core if needed."""
        core = self._core(model_source)
        if core is None:
            core = FusionCore(f"core_{len(self.fusion_cores) + 1}", model_source)
            self.fusion_cores.append(core)
        traits = core.observe(text)
        return {"ok": True, "model": model_source, "core_id": core.id,
                "traits": traits, "stability": core.stability}

    async def fuse_models(self, input_data: Dict[str, Any],
                          models: List[str] = None) -> Dict[str, Any]:
        """Fuse recorded responses (optionally supplied inline) by measured weight."""
        entries: List[Dict[str, Any]] = []
        if isinstance(input_data, dict):
            entries = list(input_data.get("responses") or [])
        elif isinstance(input_data, list):
            entries = list(input_data)

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source = entry.get("source") or entry.get("model") or "unknown"
            text = entry.get("response") or entry.get("text") or ""
            self.record_response(source, text)

        selected = [core for core in self.fusion_cores
                    if core.active and (not models or core.model_source in models)]
        measured = [core for core in selected if core.measured]
        if not measured:
            return {
                "success": False,
                "error": "no recorded responses to fuse",
                "models_fused": [],
                "note": "record a response first (fuse_models with responses, or "
                        "record_response(model, text)) - traits are never invented",
            }

        fused = self._engine.fuse([
            {"source": core.model_source, "response": core.responses[-1]}
            for core in measured
        ])
        for core in measured:
            core.successful_fusions += 1
            core.stability = core.calculate_stability()

        result = {
            "success": True,
            "fusion_id": uuid.uuid4().hex[:8],
            "models_fused": [core.model_source for core in measured],
            "fused": fused["fused"],
            "winner": fused["winner"],
            "winner_weight": fused["winner_weight"],
            "fused_traits": fused["blended_traits"],
            "cores": fused["cores"],
            "algorithm": "weighted_consensus",
            "confidence": round(_mean([core.integration_strength for core in measured]), 3),
        }
        self._record_fusion_event("fusion", {
            "fusion_id": result["fusion_id"],
            "models_fused": result["models_fused"],
            "winner": result["winner"],
            "confidence": result["confidence"],
        })
        return result

    async def extract_cognitive_traits(self, text: str) -> Dict[str, float]:
        """Deterministic trait scores for a piece of text."""
        traits = _score_response(text or "")
        digest = hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:8]
        self.cognitive_weights[digest] = traits
        return traits

    async def get_system_status(self) -> Dict[str, Any]:
        """Status built from real counters and measured stability."""
        active_cores = [core for core in self.fusion_cores if core.active]
        measured_cores = [core for core in active_cores if core.measured]
        stable_cores = [core for core in measured_cores if core.stability > 0.7]
        total_requests = sum(core.processed_requests for core in self.fusion_cores)
        total_success = sum(core.successful_fusions for core in self.fusion_cores)

        return {
            "fusion_cores": [
                {
                    "id": core.id,
                    "model": core.model_source,
                    "stability": core.stability,
                    "measured": core.measured,
                    "active": core.active,
                    "processed": core.processed_requests,
                    "integration_strength": core.integration_strength,
                    "traits": core.cognitive_traits,
                }
                for core in self.fusion_cores
            ],
            "total_cores": len(active_cores),
            "measured_cores": len(measured_cores),
            "stable_cores": len(stable_cores),
            "overall_stability": round(_mean([core.stability for core in active_cores]), 3),
            "total_fusions": total_success,
            "success_rate": round(total_success / max(1, total_requests), 3),
            "fusion_history_size": len(self.fusion_history),
            "status": "operational",
            "note": ("cores are unmeasured until a response is recorded for them"
                     if not measured_cores else "stability is derived from recorded responses"),
        }

    async def add_model(self, model_source: str,
                        traits: Dict[str, float] = None) -> Dict[str, Any]:
        """Add a model core. Traits are only set when explicitly supplied."""
        if self._core(model_source) is not None:
            return {"success": False, "error": "Model already exists"}

        core = FusionCore(f"core_{len(self.fusion_cores) + 1}", model_source)
        if traits:
            core.cognitive_traits = {name: float(value) for name, value in traits.items()}
            core.observations.append(dict(core.cognitive_traits))
            core.integration_strength = round(_mean(list(core.cognitive_traits.values())), 3)
            core.stability = core.calculate_stability()
        self.fusion_cores.append(core)
        return {
            "success": True,
            "core_id": core.id,
            "model": model_source,
            "measured": core.measured,
            "note": "" if core.measured else "traits stay empty until a response is recorded",
        }

    async def optimize_fusion_weights(self) -> Dict[str, Any]:
        """Weight each core by its measured trait mean and fusion success rate."""
        optimized = {}
        for core in self.fusion_cores:
            if core.measured:
                success_rate = core.successful_fusions / max(1, core.processed_requests)
                core.integration_strength = round(
                    max(0.0, min(1.0, core.integration_strength * (0.5 + 0.5 * success_rate))), 3)
            optimized[core.model_source] = core.integration_strength
        return {"success": True, "optimized_weights": optimized,
                "measured_models": [c.model_source for c in self.fusion_cores if c.measured]}

    async def get_fusion_insights(self) -> Dict[str, Any]:
        """Trait averages and the strongest core, over measured cores only."""
        measured = [core for core in self.fusion_cores if core.measured and core.active]
        if not measured:
            return {"trait_averages": {}, "best_model": None, "best_stability": 0.0,
                    "fusion_capability": 0,
                    "note": "no responses recorded yet - nothing to be insightful about"}

        trait_names = measured[0].cognitive_traits.keys()
        trait_averages = {
            name: round(_mean([core.cognitive_traits.get(name, 0.0) for core in measured]), 3)
            for name in trait_names
        }
        best = max(measured, key=lambda core: core.stability)
        return {
            "trait_averages": trait_averages,
            "best_model": best.model_source,
            "best_stability": best.stability,
            "fusion_capability": len(measured),
        }
