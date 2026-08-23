"""
PLL loop performance metrics — the datasheet numbers a designer argues about.

Every metric is *measured* from the transfer functions (not read off a closed-form
approximation), reusing the same python-control machinery ControlBench uses for
classical controllers:

  frequency domain (from the open loop L(s))
    - loop_bandwidth_hz   : gain-crossover frequency f_c (|L| = 1)  -> speed vs noise
    - phase_margin_deg    : phase margin at f_c                     -> stability
    - gain_margin_db      : gain margin                             -> robustness

  time / closed-loop domain (from H(s) = L/(1+L), the phase transfer)
    - lock_time_s         : settling time of the phase-step response (to a tolerance)
    - jitter_peaking_db   : peak of |H(jw)| in dB                   -> jitter amplification

A stability guard runs first: an unstable loop has meaningless time-domain numbers,
so lock time is reported as +inf and ``stable`` is False (ranking sends those to the
bottom, exactly like the classical-controller path).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import control as ct

from .model import PLLModel

_STABILITY_TOL = 1e-9


@dataclass(frozen=True)
class PLLMetrics:
    """Loop metrics for one PLL design, plus a stability flag."""

    loop_bandwidth_hz: float
    phase_margin_deg: float
    gain_margin_db: float
    lock_time_s: float
    jitter_peaking_db: float
    stable: bool

    def as_dict(self) -> dict:
        return asdict(self)


def evaluate(pll: PLLModel, lock_tolerance: float = 0.02) -> PLLMetrics:
    """Measure all loop metrics for a designed PLL.

    ``lock_tolerance`` is the settling band for lock time (0.02 = lock when the phase
    step response stays within +/-2% of its final value).
    """
    L = pll.open_loop()
    H = pll.closed_loop()

    stable = _is_stable(H)
    bw_hz, pm_deg, gm_db = _loop_margins(L)

    if not stable:
        return PLLMetrics(bw_hz, pm_deg, gm_db, float("inf"), float("inf"), False)

    lock = _lock_time(H, lock_tolerance)
    peaking = _jitter_peaking_db(H)
    return PLLMetrics(bw_hz, pm_deg, gm_db, lock, peaking, True)


# ---------------------------------------------------------------- internals

def _is_stable(H) -> bool:
    poles = ct.poles(H)
    return bool(poles.size == 0 or np.all(np.real(poles) < -_STABILITY_TOL))


def _loop_margins(L) -> tuple[float, float, float]:
    """Loop bandwidth (Hz, = gain-crossover), phase margin (deg), gain margin (dB)."""
    gm, pm, _wcg, wcp = ct.margin(L)
    bw_hz = float(wcp) / (2.0 * np.pi) if (wcp is not None and np.isfinite(wcp)) else float("nan")
    if not np.isfinite(gm) or gm <= 0:
        gm_db = float("inf")
    else:
        gm_db = float(20.0 * np.log10(gm))
    pm_deg = float(pm) if np.isfinite(pm) else float("inf")
    return bw_hz, pm_deg, gm_db


def _sim_horizon(H) -> float:
    """A step horizon long enough to capture lock, from the slowest stable pole."""
    poles = ct.poles(H)
    stable = poles[np.real(poles) < 0]
    if stable.size == 0:
        return 1e-3
    slowest = float(np.min(np.abs(np.real(stable))))
    return float(np.clip(12.0 / slowest, 1e-9, 1e3)) if slowest > 0 else 1e-3


def _lock_time(H, tol: float) -> float:
    """Settling time of the phase-step response within +/- tol of the final value."""
    tvec = np.linspace(0.0, _sim_horizon(H), 4000)
    try:
        t, y = ct.step_response(H, T=tvec)
    except Exception:
        return float("inf")
    y = np.asarray(y, float).ravel()
    yf = complex(ct.dcgain(H)).real
    if not np.isfinite(yf) or abs(yf) < 1e-12:
        yf = float(y[-1])
    if yf == 0.0:
        return float("inf")
    band = abs(tol * yf)
    outside = np.nonzero(np.abs(y - yf) > band)[0]
    return float(t[outside[-1]]) if outside.size else 0.0


def _jitter_peaking_db(H, n_points: int = 2000) -> float:
    """Peak of |H(jw)| in dB over frequency (0 dB = no peaking; type-II loops peak)."""
    poles = ct.poles(H)
    finite = poles[np.abs(poles) > 0]
    w0 = float(np.min(np.abs(finite))) if finite.size else 1.0
    w = np.logspace(np.log10(w0) - 2, np.log10(w0) + 3, n_points)
    mag = np.abs(np.asarray(ct.frequency_response(H, w).frdata).ravel())
    peak = float(np.max(mag))
    return float(20.0 * np.log10(peak)) if peak > 0 else float("-inf")
