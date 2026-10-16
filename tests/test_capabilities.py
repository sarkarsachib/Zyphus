"""Tests for the agent's integration layer: config, retrieval (RAG), APIs, connectors, models."""

import json
import os

import pytest

from src.agent import config, integrations, rag
from src.agent.tools import build_registry, rag_tool, model_config, custom_api, connector


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test gets its own config file and its own index, never the repo's."""
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setattr(rag, "DB_PATH", str(tmp_path / "rag.db"))


# ── config ──

def test_config_starts_empty():
    data = config.load()
    assert data["models"] == [] and data["apis"] == {} and data["connectors"] == {}


def test_config_model_roundtrip():
    config.upsert_model("main", base_url="https://api.example.com/v1", model="test-model",
                        api_key_env="EXAMPLE_KEY")
    assert config.active_model()["name"] == "main"
    assert config.model_entry("main")["model"] == "test-model"
    config.upsert_model("backup", base_url="https://backup.example.com/v1", model="b")
    assert config.set_active_model("backup")
    assert config.load()["active_model"] == "backup"
    assert config.remove_model("backup")
    assert config.load()["active_model"] == "main"
    assert not config.set_active_model("nope")


def test_config_api_and_connector_roundtrip():
    config.upsert_api("weather", base_url="https://api.example.com", auth_env="WEATHER_KEY",
                      description="forecast")
    assert config.api_entry("weather")["base_url"] == "https://api.example.com"

    entry = config.upsert_connector("alerts", kind="slack")
    assert entry["kind"] == "slack"
    assert entry["auth_env"] == "SLACK_WEBHOOK_URL"  # kind default
    assert config.remove_connector("alerts")
    assert config.connector_entry("alerts") is None


def test_config_rejects_unknown_connector_kind():
    with pytest.raises(ValueError):
        config.upsert_connector("odd", kind="telepathy")


def test_config_never_stores_secret_values():
    config.upsert_api("signed", base_url="https://api.example.com", auth_env="SOME_KEY")
    raw = open(config.CONFIG_PATH, encoding="utf-8").read()
    assert "SOME_KEY" in raw          # the variable's name is recorded
    assert "Bearer" not in raw        # nothing that could be a value is


# ── retrieval ──

def test_rag_index_and_query(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "alpha.txt").write_text("The heartbeat engine models neural rhythms, gamma at forty hertz.\n")
    (corpus / "beta.txt").write_text("The task queue stores leases and retries in SQLite.\n")

    indexed = rag.index(str(corpus))
    assert indexed["indexed_files"] == 2
    assert indexed["chunks"] == 2

    hits = rag.search("how fast is the gamma rhythm", top_k=1)["hits"]
    assert hits and "gamma" in hits[0]["text"]
    assert hits[0]["source"].endswith("alpha.txt")


def test_rag_reindex_replaces_chunks(tmp_path):
    note = tmp_path / "note.txt"
    note.write_text("first version")
    rag.index(str(note))
    note.write_text("second version")
    rag.index(str(note))
    assert rag.stats()["chunks"] == 1


def test_rag_stats_on_missing_database_does_not_create_it():
    stats = rag.stats()
    assert stats["chunks"] == 0 and stats.get("empty") is True
    assert not os.path.exists(rag.DB_PATH)


def test_rag_forget_and_empty_query(tmp_path):
    note = tmp_path / "note.txt"
    note.write_text("something to forget")
    rag.index(str(note))
    assert rag.search("")["error"]
    assert rag.forget()["chunks"] == 0


# ── tools ──

def test_rag_tool_index_query_stats(tmp_path):
    doc = tmp_path / "doc.txt"
    doc.write_text("Zyphus fuses model responses deterministically.")
    assert rag_tool(action="index", path=str(doc)).ok
    result = rag_tool(action="query", text="how does zyphus fuse responses")
    assert result.ok and "deterministically" in result.output
    assert rag_tool(action="stats").ok
    assert rag_tool(action="nonsense").ok is False


def test_api_tool_register_and_list():
    assert custom_api(action="register", name="weather", base_url="https://api.example.com").ok
    listed = custom_api(action="list")
    assert listed.ok and "weather" in listed.output
    assert custom_api(action="call", name="missing", path="/x").ok is False


def test_connector_tool_add_list_and_unknown():
    assert connector(action="add", name="alerts", kind="slack").ok
    assert "alerts" in connector(action="list").output
    assert connector(action="add", name="odd", kind="telepathy").ok is False
    assert connector(action="test", name="nothing-here").ok is False


def test_model_tool_list_add_and_activate():
    assert model_config(action="list").ok
    assert model_config(action="add", name="main", base_url="https://api.example.com/v1",
                        model="m", api_key_env="EXAMPLE_KEY").ok
    assert model_config(action="use", name="main").ok
    listed = json.loads(model_config(action="list").output)
    assert listed["active"] == "main"
    assert listed["models"][0]["key_present"] is False
    assert model_config(action="use", name="ghost").ok is False


def test_registry_exposes_the_new_tools():
    names = set(build_registry().names())
    for tool in ("rag", "model", "api", "connector"):
        assert tool in names, f"missing tool: {tool}"
