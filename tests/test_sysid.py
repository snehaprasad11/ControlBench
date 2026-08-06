"""Tests for the system-identification module."""

import numpy as np
import control as ct
import pytest

from controlbench.sysid import (
    identify_plant, arx_fit, arx_simulate, arx_to_continuous, fit_percent,
)


def _simulate_plant(G, u, Ts):
    # Zero-order-hold discretisation, then exact discrete simulation, so the sampled
    # data is consistent with the ARX (ZOH) assumption the identifier makes.
    Gd = ct.sample_system(G, Ts, method="zoh")
    t = np.arange(len(u)) * Ts
    _, y = ct.forced_response(Gd, T=t, U=u)
    return np.asarray(y)


def test_fit_percent_perfect_and_bounds():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert fit_percent(y, y) == pytest.approx(100.0)
    assert fit_percent(y, np.full_like(y, y.mean())) == pytest.approx(0.0)


def test_identify_recovers_stable_second_order():
    # Data generated from a known pole-only plant -> pole-only model should fit well.
    G = ct.tf([2.0], [1.0, 3.0, 2.0])          # poles at -1, -2
    Ts = 0.05
    rng = np.random.default_rng(0)
    u = rng.standard_normal(900)
    y = _simulate_plant(G, u, Ts)

    res = identify_plant(u, y, Ts, na=2, nb=2)
    assert res.plant.is_stable
    assert res.plant.order == 2
    assert res.fit_percent > 90.0               # clean synthetic data -> high fit


def test_identified_dc_gain_matches():
    G = ct.tf([2.0], [1.0, 3.0, 2.0])           # DC gain = 2/2 = 1.0
    Ts = 0.05
    rng = np.random.default_rng(1)
    u = rng.standard_normal(900)
    y = _simulate_plant(G, u, Ts)

    res = identify_plant(u, y, Ts, na=2, nb=2)
    assert float(ct.dcgain(res.plant.tf)) == pytest.approx(1.0, abs=0.1)


def test_arx_to_continuous_is_stable_for_stable_discrete():
    # Discrete AR coefficients with roots inside the unit circle.
    a = np.array([-1.2, 0.35])                  # roots ~0.5, 0.7 (stable)
    b = np.array([0.15])
    plant = arx_to_continuous(a, b, Ts=0.1)
    assert plant.is_stable
