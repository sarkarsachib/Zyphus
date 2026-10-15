"""Tests for the fusion engine and new agent tools."""

import json
import os

from src.agent.fusion import FusionEngine, _score_response
from src.agent.tools import (
    build_registry, git_status, code_analyze, memory, python_eval,
    system_info, fuse_tool,
)


# ── fusion ──

def test_score_empty():
    traits = _score_response("")
    assert all(v == 0.0 for v in traits.values())


def test_score_basic():
    traits = _score_response("Hello world. This is a test sentence with some words.")
    assert traits["creativity"] > 0
    assert 0 < traits["clarity"] <= 1.0


def test_fuse_empty():
    engine = FusionEngine()
    result = engine.fuse()
    assert "error" in result


def test_fuse_responses():
    engine = FusionEngine()
    result = engine.fuse([
        {"source": "model-a", "response": "Short answer."},
        {"source": "model-b", "response": "A longer answer with more detail and reasoning.\n\nSecond paragraph."},
    ])
    assert "fused" in result
    assert result["winner"] in ("model-a", "model-b")
    assert len(result["cores"]) == 2
    assert result["algorithm"] == "weighted_consensus"


def test_fuse_traits():
    engine = FusionEngine()
    traits = engine.traits("Test text for trait extraction.")
    assert "reasoning" in traits
    assert all(0 <= v <= 1.0 for v in traits.values())


def test_fuse_status():
    engine = FusionEngine()
    engine.fuse([{"source": "a", "response": "test"}])
    status = engine.status()
    assert status["fusions"] == 1
    assert "weighted_consensus" in status["algorithms"]


# ── new tools ──

def test_git_status():
    result = git_status()
    assert result.ok
    assert "branch" in result.output


def test_code_analyze():
    result = code_analyze("src/agent/brain.py")
    assert result.ok
    assert "functions" in result.output
    assert "classes" in result.output


def test_code_analyze_missing():
    result = code_analyze("/no/such/file.py")
    assert not result.ok


def test_memory_store_and_recall():
    result = memory(action="store", key="test-key-123", value="hello memory")
    assert result.ok
    result = memory(action="recall", key="test-key-123")
    assert result.ok
    assert "hello memory" in result.output
    # cleanup
    memory(action="forget", key="test-key-123")


def test_memory_list():
    result = memory(action="list")
    assert result.ok


def test_python_eval():
    result = python_eval("2 + 2")
    assert result.ok
    assert "4" in result.output


def test_python_eval_error():
    result = python_eval("syntax error !!!")
    assert not result.ok


def test_system_info():
    result = system_info()
    assert result.ok
    assert "os" in result.output.lower() or "python" in result.output.lower()


def test_fuse_tool_status():
    result = fuse_tool()
    assert result.ok
    assert "fusion" in result.output.lower() or "ready" in result.output.lower()


def test_fuse_tool_with_data():
    data = json.dumps([
        {"source": "a", "response": "First answer."},
        {"source": "b", "response": "Second answer with more detail."},
    ])
    result = fuse_tool(responses=data)
    assert result.ok
    assert "winner" in result.output.lower()


def test_fuse_tool_bad_json():
    result = fuse_tool(responses="not json")
    assert not result.ok


# ── registry includes new tools ──

def test_registry_has_new_tools():
    reg = build_registry()
    names = set(reg.names())
    for tool in ("git_status", "code_analyze", "memory", "python_eval", "system_info", "fuse"):
        assert tool in names, f"missing tool: {tool}"
