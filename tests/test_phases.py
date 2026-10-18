"""Tests for intelligence phase transitions: the measurements and the regimes they trigger."""

from src.agent import phases


def test_entropy_and_dominance_read_a_hypothesis_set():
    assert phases.entropy([1.0]) == 0.0                      # one candidate, no uncertainty
    assert phases.entropy([0.5, 0.5]) == 1.0                  # two even candidates, one bit
    assert phases.entropy([0.5, 0.5]) > phases.entropy([0.9, 0.1])
    assert phases.dominance([0.9, 0.1]) > phases.dominance([0.5, 0.5])
    assert phases.dominance([]) == 0.0


def test_missing_uncertainty_is_read_as_unknown_not_certain():
    metrics = phases.measure({"hypotheses": [], "uncertainty": None})
    assert metrics["uncertainty"] == 1.0
    assert phases.decide(metrics)["regime"] == "explore"


def test_unmapped_unknowns_explore():
    decision = phases.decide(phases.measure({"hypotheses": [], "uncertainty": 0.9}))
    assert decision["regime"] == "explore"
    assert decision["triggers"]


def test_enough_evidence_converges():
    state = {"hypotheses": [{"score": 0.7}, {"score": 0.3}], "uncertainty": 0.35}
    metrics = phases.measure(state)
    # with live hypotheses, uncertainty is read off their spread, not the stored number
    assert metrics["uncertainty"] == round(phases.entropy([0.7, 0.3]) / 2.0, 4)
    assert phases.decide(metrics)["regime"] == "converge"


def test_a_dominant_testable_candidate_executes():
    state = {"hypotheses": [{"score": 0.9}, {"score": 0.1}], "uncertainty": 0.1, "testable": True}
    decision = phases.decide(phases.measure(state))
    assert decision["regime"] == "execute"
    assert any("dominance" in trigger for trigger in decision["triggers"])


def test_a_dominant_but_untestable_candidate_only_converges():
    state = {"hypotheses": [{"score": 0.9}, {"score": 0.1}], "uncertainty": 0.1, "testable": False}
    assert phases.decide(phases.measure(state))["regime"] == "converge"


def test_conflicting_evidence_recovers():
    decision = phases.decide(phases.measure({"hypotheses": [], "uncertainty": 0.2},
                                            contradictions=3))
    assert decision["regime"] == "recover"
    assert any("contradictory" in trigger for trigger in decision["triggers"])


def test_stalled_progress_recovers():
    metrics = phases.measure({"hypotheses": [{"score": 0.6}], "uncertainty": 0.2},
                             progress=[0.9, 0.9, 0.9, 0.9])
    decision = phases.decide(metrics)
    assert decision["regime"] == "recover"
    assert any("without progress" in trigger for trigger in decision["triggers"])


def test_a_spent_budget_compresses():
    metrics = phases.measure({"hypotheses": [{"score": 0.6}], "uncertainty": 0.2},
                             budget=10.0, spend=9.5)
    decision = phases.decide(metrics)
    assert decision["regime"] == "compress"
    assert any("budget" in trigger for trigger in decision["triggers"])


def test_the_controller_records_every_transition():
    controller = phases.PhaseController("explore", budget=10.0)
    first = controller.step({"hypotheses": [], "uncertainty": 0.9})
    assert first["from"] == "explore" and first["to"] == "explore" and first["changed"] is False
    second = controller.step({"hypotheses": [{"score": 0.9}, {"score": 0.1}],
                              "uncertainty": 0.1, "testable": True})
    assert second["changed"] is True and second["to"] == "execute"
    assert controller.state()["regime"] == "execute"
    assert controller.state()["transitions"] == 1


def test_regimes_are_the_five_stated_ones():
    assert phases.REGIMES == ("explore", "converge", "execute", "recover", "compress")
    assert set(phases.THRESHOLDS) >= {"budget_spent", "contradictions", "stagnation", "certainty"}
