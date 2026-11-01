"""Tests for the new system tools: vector memory, code checks, processes."""

import os

from src.agent.tools import build_registry, code_check, process, vector_memory


def test_vector_memory_store_and_search(tmp_path):
    stored = vector_memory(action="store", text="the heartbeat models neural bands",
                           label="rhythm", namespace="notes", path=str(tmp_path))
    assert stored.ok
    vector_memory(action="store", text="docker compose binds the repository",
                  label="deploy", namespace="notes", path=str(tmp_path))

    found = vector_memory(action="search", text="neural heartbeat bands",
                          namespace="notes", top_k=2, path=str(tmp_path))
    assert found.ok
    assert found.meta["hits"][0]["label"] == "rhythm"


def test_vector_memory_delete_and_stats(tmp_path):
    stored = vector_memory(action="store", text="temporary", label="tmp", path=str(tmp_path))
    assert stored.ok
    removed = vector_memory(action="delete", item_id=stored.meta["id"], path=str(tmp_path))
    assert removed.ok
    assert removed.meta["removed"] == 1
    stats = vector_memory(action="stats", path=str(tmp_path))
    assert stats.ok
    assert stats.meta["items"] == 0


def test_vector_memory_rejects_empty_store(tmp_path):
    assert not vector_memory(action="store", path=str(tmp_path)).ok


def test_code_check_python_valid():
    result = code_check(code="def add(a, b):\n    return a + b\n")
    assert result.ok
    assert result.meta["valid"] is True


def test_code_check_python_invalid():
    result = code_check(code="def broken(:\n")
    assert not result.ok
    assert result.meta["valid"] is False


def test_code_check_reports_missing_toolchain():
    result = code_check(code="fn main() {}", language="rust")
    if result.meta.get("available"):
        assert result.ok
    else:
        assert not result.ok
        assert "not installed" in result.error


def test_code_check_reads_a_file(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("value = 1\n")
    assert code_check(path=str(path)).ok


def test_process_lists_and_inspects_self():
    listed = process(action="list", limit=5)
    assert listed.ok
    assert listed.meta["count"] > 0
    info = process(action="info", pid=os.getpid())
    assert info.ok
    assert info.meta["pid"] == os.getpid()


def test_brain_routes_the_tool_prefix_without_a_colon():
    from src.agent.brain import DeliberativeBrain

    plan = DeliberativeBrain().plan(
        {"instructions": 'tool process {"action":"list","limit":1}'})
    assert [(call.tool, call.arguments) for call in plan] == [
        ("process", {"action": "list", "limit": 1})]


def test_registry_has_the_new_system_tools():
    names = set(build_registry().names())
    for tool in ("vector_memory", "code_check", "process"):
        assert tool in names, f"missing tool: {tool}"
