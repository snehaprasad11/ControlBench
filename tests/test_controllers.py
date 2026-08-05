"""Tests for the Phase 2 controller designs."""

import numpy as np
import control as ct
import pytest

from controlbench.analysis import PlantModel
from controlbench.controllers import (
    design_p, design_pi, design_pid, design_lead, design_lag,
    design_all, closed_loop, open_loop,
)

# A plant with a finite ultimate gain (ZN applies) and one without (fallback).
ZN_PLANT = PlantModel([1], [1, 3, 3, 1])       # 1/(s+1)^3, Ku = 8
FALLBACK_PLANT = PlantModel([1], [1, 2, 1])    # 1/(s+1)^2, no ultimate gain


def test_ziegler_nichols_used_when_ultimate_gain_exists():
    # ZN P gain should be 0.5 * Ku = 0.5 * 8 = 4
    p = design_p(ZN_PLANT)
    assert p.method == "Ziegler-Nichols"
    assert p.params["Kp"] == pytest.approx(4.0, rel=1e-3)


def test_fallback_used_when_no_ultimate_gain():
    p = design_p(FALLBACK_PLANT)
    assert p.method == "loop-shaping"
    assert p.params["Kp"] > 0


def test_pid_has_all_three_gains_and_is_proper():
    c = design_pid(ZN_PLANT)
    assert set(c.params) == {"Kp", "Ki", "Kd"}
    # proper: numerator degree <= denominator degree
    num, den = ct.tfdata(c.tf)
    assert len(np.atleast_1d(num[0][0])) <= len(np.atleast_1d(den[0][0]))


def test_lead_is_phase_lead_pole_beyond_zero():
    c = design_lead(FALLBACK_PLANT)
    assert c.params["p"] > c.params["z"]     # lead: pole further out than zero
    assert 0 < c.params["alpha"] < 1


def test_lag_has_dc_gain_beta():
    c = design_lag(FALLBACK_PLANT, beta=10)
    dc = float(ct.dcgain(c.tf))
    assert dc == pytest.approx(10.0, rel=1e-6)   # lag DC gain == beta


def test_all_closed_loops_are_computable():
    controllers = design_all(ZN_PLANT)
    assert set(controllers) == {"P", "PI", "PID", "Lead", "Lag"}
    for c in controllers.values():
        T = closed_loop(ZN_PLANT, c)
        info = ct.step_info(T)
        assert np.isfinite(info["SettlingTime"])


def test_open_loop_is_controller_times_plant():
    c = design_p(ZN_PLANT)  # C = Kp (constant)
    L = open_loop(ZN_PLANT, c)
    # L(0) should equal Kp * G(0); G(0) = 1 here
    assert float(ct.dcgain(L)) == pytest.approx(c.params["Kp"], rel=1e-6)
