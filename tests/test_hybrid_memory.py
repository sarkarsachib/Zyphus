"""Tests for the hybrid memory vector layer (real embeddings, real search)."""

import pytest

from src.hybrid_memory_system import HybridMemorySystem, cosine_similarity, embed_text


def test_embedding_is_deterministic_and_normalised():
    first = embed_text("neural heartbeat rhythm")
    second = embed_text("neural heartbeat rhythm")
    assert first == second
    assert len(first) == 256
    assert sum(value * value for value in first) == pytest.approx(1.0, rel=1e-6)
    assert embed_text("") == [0.0] * 256
    assert cosine_similarity(first, second) == pytest.approx(1.0)


def test_store_and_search_ranks_related_text_first(tmp_path):
    system = HybridMemorySystem(str(tmp_path))
    system.vector_add_text("the heartbeat engine models gamma beta alpha bands", label="rhythm")
    system.vector_add_text("the retrieval index embeds files with hashed vectors", label="rag")
    system.vector_add_text("docker compose binds the repository into the container", label="deploy")

    hits = system.vector_search_text("neural rhythm bands heartbeat", top_k=3)
    assert hits[0]["label"] == "rhythm"
    assert hits[0]["score"] > hits[-1]["score"]

    # a negative cosine floor keeps unrelated documents out of the results
    everything = system.vector_search_text("neural rhythm bands heartbeat", top_k=3,
                                            min_score=-1.0)
    assert len(everything) == 3
    assert everything[0]["label"] == "rhythm"


def test_explicit_embedding_and_namespace_filter(tmp_path):
    system = HybridMemorySystem(str(tmp_path))
    system.vector_add_embedding({"embedding": [1.0, 0.0, 0.0], "label": "x", "namespace": "a"})
    system.vector_add_embedding({"embedding": [0.0, 1.0, 0.0], "label": "y", "namespace": "b"})

    hits = system.vector_search_embeddings([0.9, 0.1, 0.0], namespace="a")
    assert [hit["label"] for hit in hits] == ["x"]

    hits = system.vector_search_embeddings([0.0, 1.0, 0.0], min_score=0.99)
    assert [hit["label"] for hit in hits] == ["y"]


def test_reindex_replaces_instead_of_duplicating(tmp_path):
    system = HybridMemorySystem(str(tmp_path))
    first = system.vector_add_text("same text", label="note")
    second = system.vector_add_text("same text", label="note")
    assert first["id"] == second["id"]
    assert system.vector_stats()["items"] == 1


def test_delete_get_and_stats(tmp_path):
    system = HybridMemorySystem(str(tmp_path))
    stored = system.vector_add_text("alpha", label="one", namespace="ns")
    system.vector_add_text("beta", label="two", namespace="ns")

    assert system.vector_stats()["namespaces"] == {"ns": 2}
    assert system.vector_get(stored["id"])["label"] == "one"
    assert system.vector_delete(item_id=stored["id"])["removed"] == 1
    assert system.vector_get(stored["id"]) == {}
    assert system.vector_stats()["items"] == 1


def test_persists_across_instances(tmp_path):
    HybridMemorySystem(str(tmp_path)).vector_add_text("remember this", label="keep")
    reopened = HybridMemorySystem(str(tmp_path))
    assert reopened.vector_search_text("remember this")[0]["label"] == "keep"


def test_stats_on_missing_database(tmp_path):
    system = HybridMemorySystem(str(tmp_path / "fresh"))
    assert system.vector_stats()["items"] == 0


def test_add_without_text_or_embedding_is_rejected(tmp_path):
    system = HybridMemorySystem(str(tmp_path))
    with pytest.raises(ValueError):
        system.vector_add_embedding({})
