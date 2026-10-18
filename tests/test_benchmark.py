"""Tests for the research-goal benchmark: it runs the real modules and states what it measured."""

import pytest

from src.agent import benchmark, rag, substrate


@pytest.fixture(autouse=True)
def isolated_index(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "DB_PATH", str(tmp_path / "rag.db"))


def _report(tmp_path, suite):
    return benchmark.run(suite=suite, root=substrate.REPO_ROOT,
                         world_path=str(tmp_path / "bench.db"))


def test_the_suite_covers_all_four_problem_classes():
    assert {problem["klass"] for problem in benchmark.SUITE} == {"debug", "research", "design",
                                                                 "operate"}


def test_a_run_reports_every_metric_with_a_verdict(tmp_path):
    report = _report(tmp_path, benchmark.SUITE[:4])
    assert set(report["metrics"]) == {"structural_adaptability", "experimental_reasoning",
                                      "learned_procedural_improvement", "resource_awareness"}
    assert set(report["verdicts"]) == set(report["metrics"])
    for verdict in report["verdicts"].values():
        assert isinstance(verdict["holds"], bool)
        assert verdict["measure"]


def test_the_baseline_is_the_same_pipeline_for_every_problem(tmp_path):
    report = _report(tmp_path, benchmark.SUITE[:4])
    assert report["baseline"]["signature"] == benchmark.baseline_signature()
    structure = report["metrics"]["structural_adaptability"]
    assert structure["baseline_distinct_structures"] == 1
    assert structure["distinct_structures"] >= 1
    assert structure["problems"] == 4


def test_every_run_stays_inside_its_budget_and_is_reported(tmp_path):
    report = _report(tmp_path, benchmark.SUITE[:4])
    assert report["metrics"]["resource_awareness"]["budget_respected"] is True
    assert len(report["adaptive"]) == 4
    assert all(row["spend"] <= row["budget"] for row in report["adaptive"])


def test_learning_is_measured_after_the_world_model_has_run(tmp_path):
    report = _report(tmp_path, benchmark.SUITE[:4])
    learning = report["metrics"]["learned_procedural_improvement"]
    assert learning["problems"] == 4
    assert learning["strategies_measured"] >= 1        # outcomes really were recorded
    assert all("signature_before_learning" in row for row in learning["learning_rows"])


def test_the_report_says_what_it_cannot_show(tmp_path):
    report = _report(tmp_path, benchmark.SUITE[:2])
    assert any("not a comparison against any external system" in caveat
               for caveat in report["caveats"])
    assert any("neither is a claim that the code under test passed" in caveat
               for caveat in report["caveats"])


def test_a_benchmark_keeps_its_own_world_model(tmp_path):
    world_path = tmp_path / "bench.db"
    benchmark.run(suite=benchmark.SUITE[:2], root=substrate.REPO_ROOT, world_path=str(world_path))
    assert world_path.is_file()


def test_reasoning_only_counts_problems_with_competing_hypotheses(tmp_path):
    report = _report(tmp_path, benchmark.SUITE[:4])
    reasoning = report["metrics"]["experimental_reasoning"]
    assert reasoning["problems"] == 4
    assert reasoning["problems_with_competing_hypotheses"] <= reasoning["problems"]
    assert reasoning["decisive_experiments"] <= reasoning["problems_with_competing_hypotheses"]
