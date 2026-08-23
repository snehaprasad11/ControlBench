"""
PVT-robust evaluation and design-space exploration — the heart of LockBench.

A textbook designs one loop filter at nominal. A chip must hold spec across every PVT
corner. This module:

  * sweeps a fixed design across all corners (:func:`sweep_corners`);
  * reduces that to a worst-case summary and a pass/fail against a spec
    (:func:`robust_evaluate`);
  * searches the design space for a filter that stays in spec across *all* corners and
    ranks the survivors (:func:`explore_robust_design`).

The spec is expressed in the language a designer uses (minimum phase margin, maximum lock
time, maximum jitter peaking, an allowed bandwidth window), so a violation reads like a
datasheet failure, not an abstract number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .devices import Device
from .model import PLLModel
from .design import design_pll, divider_for_output
from .metrics import PLLMetrics, evaluate
from .corners import CornerSpec, Corner, generate_corners, apply_corner


@dataclass(frozen=True)
class PLLSpec:
    """Design targets a PLL must meet at every corner."""

    min_phase_margin_deg: float = 45.0
    max_lock_time_s: float | None = None
    max_jitter_peaking_db: float | None = None
    min_bandwidth_hz: float | None = None
    max_bandwidth_hz: float | None = None


@dataclass
class CornerResult:
    corner: Corner
    metrics: PLLMetrics


@dataclass
class RobustReport:
    """Result of evaluating one design across PVT."""

    nominal: PLLMetrics
    corners: list[CornerResult]
    worst: dict
    passes: bool
    violations: list[str] = field(default_factory=list)


def sweep_corners(nominal: PLLModel, corner_spec: CornerSpec,
                  lock_tolerance: float = 0.02) -> list[CornerResult]:
    """Evaluate one fixed design at every PVT corner."""
    results = []
    for corner in generate_corners(corner_spec):
        pll = apply_corner(nominal, corner)
        results.append(CornerResult(corner=corner, metrics=evaluate(pll, lock_tolerance)))
    return results


def _worst_case(results: list[CornerResult]) -> dict:
    """Reduce per-corner metrics to the worst value of each (worst = least robust)."""
    pms = [r.metrics.phase_margin_deg for r in results]
    gms = [r.metrics.gain_margin_db for r in results]
    locks = [r.metrics.lock_time_s for r in results]
    peaks = [r.metrics.jitter_peaking_db for r in results]
    bws = [r.metrics.loop_bandwidth_hz for r in results if np.isfinite(r.metrics.loop_bandwidth_hz)]
    all_stable = all(r.metrics.stable for r in results)
    return {
        "all_stable": all_stable,
        "min_phase_margin_deg": float(np.min(pms)) if pms else float("nan"),
        "min_gain_margin_db": float(np.min(gms)) if gms else float("nan"),
        "max_lock_time_s": float(np.max(locks)) if locks else float("inf"),
        "max_jitter_peaking_db": float(np.max(peaks)) if peaks else float("inf"),
        "min_bandwidth_hz": float(np.min(bws)) if bws else float("nan"),
        "max_bandwidth_hz": float(np.max(bws)) if bws else float("nan"),
    }


def _check_spec(worst: dict, spec: PLLSpec) -> list[str]:
    """Return a list of human-readable spec violations (empty => passes)."""
    v = []
    if not worst["all_stable"]:
        v.append("Loop is unstable at one or more corners.")
    if worst["min_phase_margin_deg"] < spec.min_phase_margin_deg:
        v.append(f"Worst-case phase margin {worst['min_phase_margin_deg']:.1f} deg "
                 f"< required {spec.min_phase_margin_deg:.1f} deg.")
    if spec.max_lock_time_s is not None and worst["max_lock_time_s"] > spec.max_lock_time_s:
        v.append(f"Worst-case lock time {worst['max_lock_time_s']*1e6:.1f} us "
                 f"> allowed {spec.max_lock_time_s*1e6:.1f} us.")
    if spec.max_jitter_peaking_db is not None and worst["max_jitter_peaking_db"] > spec.max_jitter_peaking_db:
        v.append(f"Worst-case jitter peaking {worst['max_jitter_peaking_db']:.2f} dB "
                 f"> allowed {spec.max_jitter_peaking_db:.2f} dB.")
    if spec.min_bandwidth_hz is not None and worst["min_bandwidth_hz"] < spec.min_bandwidth_hz:
        v.append(f"Worst-case bandwidth {worst['min_bandwidth_hz']/1e3:.1f} kHz "
                 f"< required {spec.min_bandwidth_hz/1e3:.1f} kHz.")
    if spec.max_bandwidth_hz is not None and worst["max_bandwidth_hz"] > spec.max_bandwidth_hz:
        v.append(f"Worst-case bandwidth {worst['max_bandwidth_hz']/1e3:.1f} kHz "
                 f"> allowed {spec.max_bandwidth_hz/1e3:.1f} kHz.")
    return v


def robust_evaluate(nominal: PLLModel, spec: PLLSpec, corner_spec: CornerSpec,
                    lock_tolerance: float = 0.02) -> RobustReport:
    """Evaluate a design across PVT and check it against the spec."""
    results = sweep_corners(nominal, corner_spec, lock_tolerance)
    nominal_metrics = next(r.metrics for r in results if r.corner.is_nominal)
    worst = _worst_case(results)
    violations = _check_spec(worst, spec)
    return RobustReport(nominal=nominal_metrics, corners=results, worst=worst,
                        passes=len(violations) == 0, violations=violations)


@dataclass
class DesignCandidate:
    """One explored design and how it fared across PVT."""

    fc_hz: float
    phase_margin_deg: float
    icp_a: float
    pll: PLLModel
    report: RobustReport
    robustness_margin_deg: float   # worst-case PM minus the required minimum


def explore_robust_design(device: Device, n: float, spec: PLLSpec,
                          corner_spec: CornerSpec,
                          fc_grid: list[float] | None = None,
                          pm_grid: list[float] | None = None,
                          icp_grid: list[float] | None = None,
                          f_pfd_hz: float | None = None) -> list[DesignCandidate]:
    """Search (loop bandwidth, phase margin, Icp) for corner-robust designs.

    Returns every candidate that passes the spec at all corners, ranked best-first by
    robustness margin then by lock time. If none pass, returns the closest few so the UI
    can still show "here is how far off you are."
    """
    # Default grids: bandwidth spanning a decade below the PFD/10 guideline; a spread of
    # phase-margin targets; and the device's own charge-pump current options.
    if fc_grid is None:
        top = (f_pfd_hz / 10.0) if f_pfd_hz else 1e5
        fc_grid = list(np.logspace(np.log10(top / 20.0), np.log10(top), 6))
    if pm_grid is None:
        pm_grid = [45.0, 50.0, 55.0, 60.0]
    if icp_grid is None:
        # Subsample the device's charge-pump options to keep the search responsive:
        # at most ~5 currents spread across the available range.
        opts = list(device.icp_options_a)
        step = max(1, len(opts) // 5)
        icp_grid = opts[::step]

    passing: list[DesignCandidate] = []
    near: list[DesignCandidate] = []
    for icp in icp_grid:
        for pm in pm_grid:
            for fc in fc_grid:
                try:
                    pll = design_pll(device, n=n, fc_hz=fc, phase_margin_deg=pm, icp_a=icp)
                    report = robust_evaluate(pll, spec, corner_spec)
                except Exception:
                    continue
                margin = report.worst["min_phase_margin_deg"] - spec.min_phase_margin_deg
                cand = DesignCandidate(fc_hz=fc, phase_margin_deg=pm, icp_a=icp,
                                       pll=pll, report=report, robustness_margin_deg=margin)
                (passing if report.passes else near).append(cand)

    if passing:
        # Best = most PVT headroom, then fastest lock.
        passing.sort(key=lambda c: (-c.robustness_margin_deg, c.report.worst["max_lock_time_s"]))
        return passing
    # Nothing passes: surface the closest attempts (largest, i.e. least-negative, margin).
    near.sort(key=lambda c: -c.robustness_margin_deg)
    return near[:5]
