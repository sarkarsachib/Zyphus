"""Tests for the SuperFusing adapter: measured traits, honest fusion."""

import asyncio

from src.llm_superfusing_engine_adapter import FusionCore, LLMSuperFusingEngine


def test_cores_start_unmeasured():
    engine = LLMSuperFusingEngine()
    assert engine.fusion_cores
    for core in engine.fusion_cores:
        assert core.measured is False
        assert core.cognitive_traits == {}
        assert core.stability == 0.0


def test_trait_extraction_is_deterministic():
    engine = LLMSuperFusingEngine()
    text = "1. measure the parser\n2. decide from the evidence\n- keep the log"
    first = asyncio.run(engine.extract_cognitive_traits(text))
    second = asyncio.run(engine.extract_cognitive_traits(text))
    assert first == second
    assert all(0.0 <= value <= 1.0 for value in first.values())


def test_fusion_without_responses_fails_honestly():
    engine = LLMSuperFusingEngine()
    result = asyncio.run(engine.fuse_models({}))
    assert result["success"] is False
    assert "no recorded responses" in result["error"]


def test_fusion_ranks_real_responses():
    engine = LLMSuperFusingEngine()
    result = asyncio.run(engine.fuse_models({"responses": [
        {"source": "Claude",
         "response": "1. Read the file\n2. Measure the parser\n```python\nx = 1\n```"},
        {"source": "LLaMA", "response": "ok"},
    ]}))
    assert result["success"] is True
    assert result["winner"] == "Claude"
    assert result["algorithm"] == "weighted_consensus"
    assert set(result["models_fused"]) == {"Claude", "LLaMA"}
    assert result["cores"][0]["weight"] >= result["cores"][1]["weight"]
    assert 0.0 <= result["confidence"] <= 1.0


def test_status_counts_measured_cores_and_fusions():
    engine = LLMSuperFusingEngine()
    asyncio.run(engine.fuse_models({"responses": [
        {"source": "Claude", "response": "- alpha\n- beta"},
        {"source": "GPT-4", "response": "A longer analysis with several sentences. "
                                        "It explains the trade-off in more detail."},
    ]}))
    status = asyncio.run(engine.get_system_status())
    assert status["measured_cores"] == 2
    assert status["total_fusions"] == 2
    assert 0.0 <= status["overall_stability"] <= 1.0
    assert status["status"] == "operational"


def test_stability_reflects_consistency():
    core = FusionCore("c1", "Claude")
    assert core.calculate_stability() == 0.0
    core.observe("short")
    assert 0.0 < core.stability <= 1.0


def test_record_response_then_fuse_by_model():
    engine = LLMSuperFusingEngine()
    engine.record_response("Gemini", "1. first step\n2. second step\n- evidence")
    result = asyncio.run(engine.fuse_models({}, models=["Gemini"]))
    assert result["success"] is True
    assert result["models_fused"] == ["Gemini"]


def test_add_model_has_no_invented_traits():
    engine = LLMSuperFusingEngine()
    added = asyncio.run(engine.add_model("NewModel"))
    assert added["success"] is True
    assert added["measured"] is False
    assert asyncio.run(engine.add_model("NewModel"))["success"] is False


def test_optimize_weights_uses_measured_data_only():
    engine = LLMSuperFusingEngine()
    asyncio.run(engine.fuse_models({"responses": [
        {"source": "Claude", "response": "- a\n- b\n1. c"}]}))
    optimized = asyncio.run(engine.optimize_fusion_weights())
    assert optimized["measured_models"] == ["Claude"]
    assert 0.0 < optimized["optimized_weights"]["Claude"] <= 1.0


def test_insights_are_empty_until_measured():
    engine = LLMSuperFusingEngine()
    insights = asyncio.run(engine.get_fusion_insights())
    assert insights["best_model"] is None
    assert insights["trait_averages"] == {}
