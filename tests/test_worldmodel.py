"""Tests for memory as a generative world: relations, generated claims, measured procedures."""

import os

import pytest

from src.agent.worldmodel import WorldModel


@pytest.fixture
def world(tmp_path):
    return WorldModel(str(tmp_path / "world.db"))


def test_observing_outcomes_builds_relations_and_procedures(world):
    world.observe(["import-cycle", "config-mismatch"], "failed", klass="debug",
                  strategy="debug:deterministic+simulation")
    world.observe(["import-cycle", "missing-dependency"], "failed", klass="debug",
                  strategy="debug:deterministic+simulation")

    relations = world.neighbors("import-cycle")
    linked = {relation["dst"] for relation in relations}
    assert "config-mismatch" in linked and "missing-dependency" in linked
    assert world.stats()["observations"] == 2
    procedures = world.strategies("debug")
    assert procedures[0]["strategy"] == "debug:deterministic+simulation"
    assert procedures[0]["attempts"] == 2


def test_a_generated_claim_is_unverified_until_confirmed(world):
    world.observe(["import-cycle", "config-mismatch"], "failed", klass="debug")
    claims = world.generate_hypotheses("import-cycle", limit=3)
    assert claims, "a learned relation should generate something to test"
    assert all(claim["verified"] is False for claim in claims)
    assert all("unverified" not in claim["claim"] for claim in claims)
    assert "prior observation" in claims[0]["claim"]

    settled = world.confirm(claims[0]["id"], "supported", evidence="ran the import test")
    assert settled["confirmed"] is True
    assert world.predictions(verified=True)[0]["id"] == claims[0]["id"]
    assert world.stats()["verified"] == 1


def test_confirming_an_unknown_prediction_is_reported_not_invented(world):
    assert world.confirm(9999, "supported")["confirmed"] is False


def test_procedures_are_ranked_by_measured_success(world):
    world.observe(["a"], "observed", klass="operate", strategy="operate:fast")
    world.observe(["a"], "observed", klass="operate", strategy="operate:fast")
    world.observe(["a"], "unresolved", klass="operate", strategy="operate:slow")

    ranked = world.strategies("operate")
    assert [entry["strategy"] for entry in ranked] == ["operate:fast", "operate:slow"]
    assert ranked[0]["success_rate"] == 1.0 and ranked[1]["success_rate"] == 0.0
    assert world.prefer_strategy("operate")["strategy"] == "operate:fast"


def test_a_procedure_needs_real_runs_before_it_is_preferred(world):
    world.observe(["a"], "observed", klass="design", strategy="design:one")
    assert world.prefer_strategy("design") is None      # one run is not a measurement


def test_association_by_hand_and_forgetting(world):
    world.associate("flaky-test", "timezone", kind="co_occurs")
    assert world.relation("flaky-test", "timezone")["kind"] == "co_occurs"
    world.forget("flaky-test")
    assert world.neighbors("flaky-test") == []
    world.forget()
    assert world.stats()["relations"] == 0


def test_reading_a_missing_world_creates_nothing(tmp_path):
    path = tmp_path / "absent" / "world.db"
    assert WorldModel(path).stats()["exists"] is False
    # stats() itself must not have created it
    assert not os.path.isfile(path)
