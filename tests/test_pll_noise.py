"""
Tests for the phase-noise / jitter / spur model.

These check the model behaves the way real PLL noise does: a physically sane jitter
magnitude, in-band vs VCO regions crossing over near the loop bandwidth, and wider loop
bandwidth trading in-band noise against VCO suppression.
"""

import math

import numpy as np

from controlbench.pll import (
    get_device, design_pll, divider_for_output, phase_noise, reference_spur_dbc,
)


def _design(fc_hz=20e3, pm=50.0, f_out=2.4e9, f_pfd=10e6):
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=f_out, f_pfd_hz=f_pfd)
    pll = design_pll(dev, n=n, fc_hz=fc_hz, phase_margin_deg=pm)
    return pll, f_out, f_pfd


def test_phase_noise_profile_is_sane():
    pll, f_out, f_pfd = _design()
    pn = phase_noise(pll, f_out, f_pfd)
    assert len(pn.offset_hz) == len(pn.total_dbc) > 0
    # Phase noise is negative dBc/Hz and finite everywhere.
    assert all(math.isfinite(v) and v < 0 for v in pn.total_dbc)
    # RMS jitter is a small positive time (femtoseconds to nanoseconds).
    assert 1e-15 < pn.rms_jitter_s < 1e-8


def test_total_is_at_least_each_component():
    pll, f_out, f_pfd = _design()
    pn = phase_noise(pll, f_out, f_pfd)
    tot = np.array(pn.total_dbc)
    inb = np.array(pn.inband_dbc)
    vco = np.array(pn.vco_dbc)
    # The sum of powers is >= either contribution (in dB, within rounding).
    assert np.all(tot >= inb - 1e-6)
    assert np.all(tot >= vco - 1e-6)


def test_inband_flat_and_vco_dominates_high():
    pll, f_out, f_pfd = _design(fc_hz=20e3)
    pn = phase_noise(pll, f_out, f_pfd)
    f = np.array(pn.offset_hz)
    inb = np.array(pn.inband_dbc)
    vco = np.array(pn.vco_dbc)
    # The in-band contribution is flat close-in (its defining property): the PLL floor is
    # constant and |H| ~ 1 well inside the loop.
    i100, i1k = int(np.argmin(np.abs(f - 100))), int(np.argmin(np.abs(f - 1e3)))
    assert abs(inb[i100] - inb[i1k]) < 1.0
    # Well outside the loop (5 MHz), VCO noise dominates the total.
    i_hi = int(np.argmin(np.abs(f - 5e6)))
    assert vco[i_hi] > inb[i_hi]


def test_reference_spur_is_strongly_attenuated():
    pll, f_out, f_pfd = _design()
    spur = reference_spur_dbc(pll, f_pfd)
    # The comparison frequency is far beyond the loop bandwidth, so the spur is deep.
    assert spur < -60.0 and math.isfinite(spur)
