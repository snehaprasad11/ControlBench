"""
Performance metrics for a closed loop.

Given a plant and a controller, `evaluate` closes the loop and measures the six
metrics ControlBench ranks on:

  time domain (from the closed-loop step response)
    - rise_time            : 10% -> 90% of final value (s)
    - settling_time        : time to stay within +/-2% of final value (s)
    - overshoot            : peak excursion beyond final value (%)
    - steady_state_error   : |1 - T(0)| for a unit step reference

  frequency domain (from the open-loop L = C*G)
    - gain_margin_db       : extra gain before instability (dB)
    - phase_margin_deg     : extra phase lag before instability (deg)

A stability guard runs first: if the closed loop has any pole in the right-half
plane, the time-domain metrics are meaningless, so they are reported as +inf and
`stable` is set False. Ranking (Phase 3) uses that flag to send unstable designs
to the bottom instead of crashing on inf/nan.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import control as ct

from ..controllers.base import Controller, open_loop, closed_loop

_STABILITY_TOL = 1e-9


@dataclass(frozen=True)
class Metrics:
    """The six performance metrics for one closed loop, plus a stability flag."""

    rise_time: float
    settling_time: float
    overshoot: float
    steady_state_error: float
    gain_margin_db: float
    phase_margin_deg: float
    stable: bool

    def as_dict(self) -> dict:
        return asdict(self)


def evaluate(plant, controller: Controller) -> Metrics:
    """Close the loop for `controller` on `plant` and measure all six metrics."""
    T = closed_loop(plant, controller)
    L = open_loop(plant, controller)

    stable = _is_stable(T)
    gain_margin_db, phase_margin_deg = _margins_db(L)

    if not stable:
        inf = float("inf")
        return Metrics(inf, inf, inf, inf, gain_margin_db, phase_margin_deg, False)

    rise, settling, overshoot = _step_metrics(T)
    ss_error = _steady_state_error(T)

    return Metrics(rise, settling, overshoot, ss_error,
                   gain_margin_db, phase_margin_deg, True)


# ---------------------------------------------------------------- internals

def _is_stable(T) -> bool:
    """Closed-loop stable iff every pole is strictly in the left-half plane."""
    poles = ct.poles(T)
    return bool(poles.size == 0 or np.all(np.real(poles) < -_STABILITY_TOL))


def _margins_db(L) -> tuple[float, float]:
    """Gain margin (dB) and phase margin (deg) of the open loop L(s)."""
    gm, pm, _wcg, _wcp = ct.margin(L)
    # gm is a linear ratio; convert to dB. An infinite/undefined gm means the phase
    # never reaches -180 deg -> effectively infinite robustness.
    if not np.isfinite(gm) or gm <= 0:
        gm_db = float("inf")
    else:
        gm_db = float(20.0 * np.log10(gm))
    pm_deg = float(pm) if np.isfinite(pm) else float("inf")
    return gm_db, pm_deg


def _sim_horizon(T) -> float:
    """A step-response horizon long enough to capture settling, from the slowest pole."""
    poles = ct.poles(T)
    stable = poles[np.real(poles) < 0]
    if stable.size == 0:
        return 50.0
    slowest = float(np.min(np.abs(np.real(stable))))
    if slowest <= 0:
        return 1000.0
    return float(np.clip(10.0 / slowest, 5.0, 1e4))


def _step_metrics(T) -> tuple[float, float, float]:
    """
    Rise time, settling time and overshoot from the closed-loop step response.

    control.step_info picks its own (sometimes too-short) time vector and can then
    raise on slow plants, so we supply an adequate horizon and fall back to a manual
    computation if it still fails. Returns (rise, settling, overshoot).
    """
    tvec = np.linspace(0.0, _sim_horizon(T), 3000)
    try:
        info = ct.step_info(T, T=tvec)
        rise = _finite(info.get("RiseTime"))
        settling = _finite(info.get("SettlingTime"))
        overshoot = _finite(info.get("Overshoot"), default=0.0)
        if all(np.isfinite(v) for v in (rise, settling, overshoot)):
            return rise, settling, overshoot
    except (IndexError, ValueError):
        pass
    return _manual_step_metrics(T, tvec)


def _manual_step_metrics(T, tvec) -> tuple[float, float, float]:
    """Compute step metrics directly from the response (robust fallback)."""
    t, y = ct.step_response(T, T=tvec)
    y = np.asarray(y, float).ravel()
    dc = complex(ct.dcgain(T)).real
    yf = dc if (np.isfinite(dc) and abs(dc) > 1e-9) else float(y[-1])
    if yf == 0.0:
        return float("inf"), float("inf"), float("inf")

    overshoot = max(0.0, (np.max(y) - yf) / abs(yf) * 100.0)
    band = 0.02 * abs(yf)                      # +/-2% settling band
    outside = np.nonzero(np.abs(y - yf) > band)[0]
    settling = float(t[outside[-1]]) if outside.size else 0.0
    try:                                       # 10% -> 90% rise time
        i10 = np.nonzero(y >= 0.1 * yf)[0][0]
        i90 = np.nonzero(y >= 0.9 * yf)[0][0]
        rise = float(t[i90] - t[i10])
    except IndexError:
        rise = float("inf")
    return rise, settling, overshoot


def _steady_state_error(T) -> float:
    """|1 - T(0)| for a unit-step reference; 0 when the loop has an integrator."""
    dc = ct.dcgain(T)
    dc = complex(dc)
    if not np.isfinite(dc.real):
        return float("inf")
    return float(abs(1.0 - dc.real))


def _finite(value, default: float = float("inf")) -> float:
    """Coerce None/NaN into a sensible finite-or-inf value."""
    if value is None:
        return default
    v = float(value)
    return v if np.isfinite(v) else default
