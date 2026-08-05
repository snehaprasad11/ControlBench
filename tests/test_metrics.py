"""Tests for the Phase 3 metrics (evaluate)."""

import control as ct
import pytest

from controlbench.analysis import PlantModel, evaluate, Metrics
from controlbench.controllers import design_p, design_pi, Controller

ZN_PLANT = PlantModel([1], [1, 3, 3, 1])   # 1/(s+1)^3, Ku = 8


def test_stable_controller_gives_finite_metrics():
    m = evaluate(ZN_PLANT, design_p(ZN_PLANT))
    assert m.stable
    for v in (m.rise_time, m.settling_time, m.overshoot, m.steady_state_error):
        assert v != float("inf")


def test_unstable_controller_flagged_and_infinite():
    # Kp = 1000 >> Ku = 8  ->  closed loop is unstable
    huge = Controller("P", ct.tf([1000], [1]), {"Kp": 1000}, "manual")
    m = evaluate(ZN_PLANT, huge)
    assert not m.stable
    assert m.settling_time == float("inf")
    assert m.overshoot == float("inf")


def test_proportional_steady_state_error():
    # P with Kp = 0.5*Ku = 4 on a plant with G(0)=1: ss error = 1/(1+Kp) = 0.2
    m = evaluate(ZN_PLANT, design_p(ZN_PLANT))
    assert m.steady_state_error == pytest.approx(0.2, abs=1e-3)


def test_integral_action_removes_steady_state_error():
    m = evaluate(ZN_PLANT, design_pi(ZN_PLANT))
    assert m.steady_state_error == pytest.approx(0.0, abs=1e-6)


def test_metrics_as_dict_roundtrip():
    m = evaluate(ZN_PLANT, design_p(ZN_PLANT))
    d = m.as_dict()
    assert set(d) == {
        "rise_time", "settling_time", "overshoot",
        "steady_state_error", "gain_margin_db", "phase_margin_deg", "stable",
    }
