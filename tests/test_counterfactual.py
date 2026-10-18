"""Tests for the counterfactual reality engine: predictions, information, chosen experiments."""

import pytest

from src.agent import counterfactual


def _hypotheses():
    """Three live candidates that disagree about what two of the tests would show."""
    return [
        {"id": "h1", "score": 0.5, "claim": "an import cycle",
         "predicts": {"command: import": "separates", "command: tests": "no-signal"}},
        {"id": "h2", "score": 0.3, "claim": "the test suite",
         "predicts": {"command: import": "no-signal", "command: tests": "separates"}},
        {"id": "h3", "score": 0.2, "claim": "a missing artifact",
         "predicts": {"command: import": "separates", "command: tests": "no-signal"}},
    ]


def _candidates():
    return [
        counterfactual.Candidate("command: import", "command", "python -c \"import pkg.uses\""),
        counterfactual.Candidate("command: tests", "command", "python -m pytest tests -q"),
        counterfactual.Candidate("query: unrelated", "query", "list:."),
    ]


@pytest.fixture
def repo(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "base.py").write_text("def helper():\n    return 1\n")
    (package / "uses.py").write_text("from pkg.base import helper\n\n\ndef run():\n    return helper()\n")
    return str(tmp_path)


def test_a_proposed_patch_is_predicted_from_the_real_import_graph(repo):
    patch = ("--- a/pkg/base.py\n+++ b/pkg/base.py\n@@\n-def helper():\n-    return 1\n"
             "+def helper():\n+    return 2\n")
    forecast = counterfactual.predict(counterfactual.Candidate("patch: base", "patch", patch),
                                      root=repo)
    assert forecast["blast_radius"] >= 1
    assert "pkg/base.py" in forecast["files"] or forecast["dependents"]
    assert any("depend on what it changes" in effect for effect in forecast["predicted_effects"])
    assert forecast["verified"] is False
    assert "prediction" in forecast["note"]


def test_mutating_commands_are_predicted_as_riskier_than_reads():
    destructive = counterfactual.predict(
        counterfactual.Candidate("command: clean", "command", "rm -rf build"))
    read_only = counterfactual.predict(
        counterfactual.Candidate("command: look", "command", "ls -l src"))
    assert destructive["risk"] > read_only["risk"]
    assert any("changes the machine" in effect for effect in destructive["predicted_effects"])
    assert any("reads state only" in effect for effect in read_only["predicted_effects"])


def test_a_test_that_cannot_separate_anything_carries_no_information():
    info = counterfactual.expected_information(_candidates()[2], _hypotheses())
    assert info["gain"] == 0.0
    assert "does not split" in info["reason"]


def test_a_separating_test_carries_measurable_information():
    info = counterfactual.expected_information(_candidates()[0], _hypotheses())
    assert info["gain"] > 0
    assert info["before"] > info["after"]
    assert info["branches"] == {"separates": 2, "no-signal": 1}   # h1+h3 vs h2
    assert set(info["separates"]) == {"h1", "h2", "h3"}


def test_choosing_the_experiment_puts_information_first_and_discards_the_rest():
    decision = counterfactual.choose_experiment(_candidates(), _hypotheses())
    assert decision["chosen"]["label"] in ("command: import", "command: tests")
    assert decision["chosen"]["gain"] > 0
    discarded = {entry["label"]: entry["reason"] for entry in decision["discarded"]}
    assert "cannot separate any hypothesis" in discarded["query: unrelated"]
    assert "separates" in decision["reason"]


def test_ranking_returns_predictions_not_verdicts():
    ranked = counterfactual.rank(_candidates(), _hypotheses())
    assert all(item["verified"] is False for item in ranked)
    values = [item["expected_value"] for item in ranked]
    assert values == sorted(values, reverse=True)


def test_simulating_a_plan_names_the_worlds_and_the_order():
    simulation = counterfactual.simulate(_candidates(), _hypotheses())
    assert simulation["recommended_order"][0] == simulation["worlds"][0]["label"]
    assert "query: unrelated" in simulation["discarded_before_execution"]
    assert simulation["total_predicted_cost"] > 0
    assert "confirmed" in simulation["note"]


def test_no_hypotheses_means_nothing_is_worth_running():
    decision = counterfactual.choose_experiment(_candidates(), [])
    assert decision["chosen"] is None
    assert "nothing worth running" in decision["reason"]
