"""
Tests for the PVT-corner robustness layer.

These encode the physical story LockBench is built on: raising loop gain (Kvco/Icp) eats
phase margin, so the worst-case corner is worse than nominal; and a robust search must
return designs that hold spec across *all* corners.
"""

import math

import pytest

from controlbench.pll import (
    get_device, design_pll, divider_for_output, evaluate,
    CornerSpec, generate_corners, apply_corner,
    PLLSpec, sweep_corners, robust_evaluate, explore_robust_design,
)


def test_corner_generation_counts():
    # Kvco + Icp enabled -> 4 box corners + nominal.
    corners = generate_corners(CornerSpec(kvco_tol=0.3, icp_tol=0.1, comp_tol=0.0))
    assert len(corners) == 5
    assert any(c.is_nominal for c in corners)
    # Adding component tolerance doubles the box (3 dims -> 8 + nominal).
    corners3 = generate_corners(CornerSpec(kvco_tol=0.3, icp_tol=0.1, comp_tol=0.05))
    assert len(corners3) == 9


def test_high_gain_corner_eats_phase_margin():
    """A high-Kvco/high-Icp corner should have less phase margin than nominal."""
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=1.0e9, f_pfd_hz=10e6)
    nominal = design_pll(dev, n=n, fc_hz=20e3, phase_margin_deg=55.0)

    results = sweep_corners(nominal, CornerSpec(kvco_tol=0.3, icp_tol=0.1))
    nominal_pm = next(r.metrics.phase_margin_deg for r in results if r.corner.is_nominal)
    worst_pm = min(r.metrics.phase_margin_deg for r in results)
    assert worst_pm < nominal_pm


def test_robust_report_flags_violation():
    """A design that only just meets PM at nominal should fail a tight PVT spec."""
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=1.0e9, f_pfd_hz=10e6)
    # Design at exactly 45 deg nominal; corners will push some below 45.
    nominal = design_pll(dev, n=n, fc_hz=30e3, phase_margin_deg=45.0)
    report = robust_evaluate(nominal, PLLSpec(min_phase_margin_deg=45.0),
                             CornerSpec(kvco_tol=0.3, icp_tol=0.1))
    assert not report.passes
    assert report.violations
    assert report.worst["min_phase_margin_deg"] < 45.0


def test_explore_finds_robust_design():
    """The explorer should return designs that pass at all corners, best-first."""
    dev = get_device("adf4351")
    f_pfd = 10e6
    n = divider_for_output(dev, f_out_hz=1.0e9, f_pfd_hz=f_pfd)
    spec = PLLSpec(min_phase_margin_deg=45.0, max_jitter_peaking_db=3.0)
    corner_spec = CornerSpec(kvco_tol=0.3, icp_tol=0.1)

    candidates = explore_robust_design(dev, n=n, spec=spec, corner_spec=corner_spec,
                                       f_pfd_hz=f_pfd)
    assert candidates
    best = candidates[0]
    assert best.report.passes
    assert best.report.worst["min_phase_margin_deg"] >= 45.0
    # Ranked by robustness margin: first is at least as robust as the last.
    assert best.robustness_margin_deg >= candidates[-1].robustness_margin_deg
