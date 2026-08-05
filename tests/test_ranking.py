"""Tests for the Phase 3 ranking engine."""

import pytest

from controlbench.analysis import Metrics
from controlbench.ranking import rank, recommend, DEFAULT_WEIGHTS


def _m(rise, settle, over, ss, gm, pm, stable=True):
    return Metrics(rise, settle, over, ss, gm, pm, stable)


# A clearly-best, a middling, and an unstable controller.
FIELD = {
    "Good":     _m(0.5, 2.0, 2.0, 0.00, 20.0, 70.0),
    "Middling": _m(1.0, 5.0, 20.0, 0.10, 10.0, 40.0),
    "Unstable": _m(float("inf"), float("inf"), float("inf"), float("inf"), -5.0, -10.0, stable=False),
}


def test_best_controller_ranks_first():
    ranked = rank(FIELD)
    assert ranked[0].name == "Good"
    assert recommend(FIELD).name == "Good"


def test_unstable_is_last_with_zero_score():
    ranked = rank(FIELD)
    assert ranked[-1].name == "Unstable"
    assert ranked[-1].score == 0.0


def test_scores_are_within_unit_interval():
    for r in rank(FIELD):
        assert 0.0 <= r.score <= 1.0


def test_weights_need_not_sum_to_one():
    # Doubling every weight must not change the ranking or push scores out of range.
    doubled = {k: 2 * v for k, v in DEFAULT_WEIGHTS.items()}
    a = rank(FIELD)
    b = rank(FIELD, weights=doubled)
    assert [r.name for r in a] == [r.name for r in b]
    assert a[0].score == pytest.approx(b[0].score)


def test_weighting_can_change_the_winner():
    # Two controllers: one great on overshoot, one great on settling time.
    field = {
        "LowOvershoot":  _m(1.0, 8.0, 1.0, 0.0, 15.0, 60.0),
        "FastSettling":  _m(1.0, 2.0, 25.0, 0.0, 15.0, 60.0),
    }
    overshoot_focus = {"overshoot": 1.0, "settling_time": 0.0}
    settling_focus = {"overshoot": 0.0, "settling_time": 1.0}
    assert recommend(field, overshoot_focus).name == "LowOvershoot"
    assert recommend(field, settling_focus).name == "FastSettling"


def test_all_unstable_field_still_ranks():
    field = {"A": _m(*[float("inf")] * 4, -1.0, -1.0, stable=False)}
    ranked = rank(field)
    assert ranked[0].score == 0.0
