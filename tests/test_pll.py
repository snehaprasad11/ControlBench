"""
Tests for the PLL engine.

The important one is `test_design_hits_targets`: it designs a loop filter for a target
bandwidth and phase margin, then *measures* the achieved values from the transfer
function. That closes the loop on the Banerjee formulas — if the math were wrong, the
measured margin/bandwidth would drift from the target and the test would fail. This is
what lets LockBench claim its designs are correct, not just plausible.
"""

import math

import numpy as np
import pytest

from controlbench.pll import (
    load_devices, get_device,
    LoopFilter, PLLModel,
    design_loop_filter, design_pll, divider_for_output,
    evaluate,
)


# ------------------------------------------------------------------ device library

def test_device_library_loads_real_parts():
    devs = load_devices()
    ids = {d.id for d in devs}
    assert {"adf4351", "lmx2594", "adf5355"} <= ids
    adf = get_device("adf4351")
    assert adf.vendor == "Analog Devices"
    assert adf.kvco_hz_per_v == pytest.approx(40e6)          # 40 MHz/V
    assert adf.icp_default_a == pytest.approx(2.5e-3)         # 2.5 mA
    assert abs(adf.kvco_rad_per_v - 2 * math.pi * 40e6) < 1.0


def test_unknown_device_raises():
    with pytest.raises(KeyError):
        get_device("does_not_exist")


# ------------------------------------------------------------------ loop filter

def test_loop_filter_zero_and_pole_frequencies():
    lf = LoopFilter(r=1e3, c_main=1e-9, c_shunt=1e-10)
    assert lf.order == 3
    assert lf.zero_hz == pytest.approx(1.0 / (2 * math.pi * 1e3 * 1e-9), rel=1e-9)
    assert math.isfinite(lf.pole3_hz) and lf.pole3_hz > lf.zero_hz

    lf2 = LoopFilter(r=1e3, c_main=1e-9)
    assert lf2.order == 2
    assert lf2.pole3_hz == float("inf")


def test_type_two_loop_has_two_poles_at_origin():
    """A type-II loop's open loop must have a double pole at s = 0."""
    dev = get_device("adf4351")
    lf = LoopFilter(r=1e3, c_main=1e-9, c_shunt=1e-10)
    pll = PLLModel.build(dev, icp_a=2.5e-3, n=100, loop_filter=lf)
    poles = pll.open_loop().poles()
    at_origin = np.sum(np.abs(poles) < 1e-6)
    assert at_origin == 2


# ------------------------------------------------------------------ design self-check

@pytest.mark.parametrize("fc_hz,pm_deg", [(10e3, 45.0), (30e3, 50.0), (50e3, 60.0)])
def test_design_hits_targets(fc_hz, pm_deg):
    """Design for (bandwidth, phase margin), then measure them back."""
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=1.0e9, f_pfd_hz=10e6)
    pll = design_pll(dev, n=n, fc_hz=fc_hz, phase_margin_deg=pm_deg)
    m = evaluate(pll)

    assert m.stable
    assert m.loop_bandwidth_hz == pytest.approx(fc_hz, rel=0.20)   # within 20%
    assert m.phase_margin_deg == pytest.approx(pm_deg, abs=6.0)    # within 6 deg


def test_designed_loop_is_stable_and_locks():
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=2.4e9, f_pfd_hz=25e6)
    pll = design_pll(dev, n=n, fc_hz=25e3, phase_margin_deg=50.0)
    m = evaluate(pll)
    assert m.stable
    assert m.lock_time_s > 0 and math.isfinite(m.lock_time_s)
    assert math.isfinite(m.jitter_peaking_db)
    # A ~50-degree phase margin should keep jitter peaking modest (well under ~6 dB).
    assert m.jitter_peaking_db < 6.0


def test_higher_bandwidth_locks_faster():
    """Physical sanity: a wider loop bandwidth should lock faster."""
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=1.0e9, f_pfd_hz=10e6)
    slow = evaluate(design_pll(dev, n=n, fc_hz=10e3, phase_margin_deg=50.0))
    fast = evaluate(design_pll(dev, n=n, fc_hz=40e3, phase_margin_deg=50.0))
    assert fast.lock_time_s < slow.lock_time_s


def test_low_phase_margin_peaks_more():
    """Physical sanity: less phase margin => more jitter peaking."""
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=1.0e9, f_pfd_hz=10e6)
    tight = evaluate(design_pll(dev, n=n, fc_hz=20e3, phase_margin_deg=35.0))
    relaxed = evaluate(design_pll(dev, n=n, fc_hz=20e3, phase_margin_deg=60.0))
    assert tight.jitter_peaking_db > relaxed.jitter_peaking_db
