"""
Automatic design of the five classical controllers.

Tuning philosophy
-----------------
* P / PI / PID use **Ziegler-Nichols** (ultimate-gain method) when the plant has a
  finite ultimate gain Ku -- i.e. its open-loop phase actually crosses -180 deg.
  This is the tuning rule every controls course teaches.
* When no such point exists (typical for 1st- and 2nd-order plants, whose phase never
  reaches -180 deg), ZN is undefined, so we fall back to a simple **loop-shaping**
  rule: put the proportional gain crossover near the plant's natural frequency.
* Lead / Lag are designed with the classical **phase-lead** and **lag** networks
  using sensible default targets (added phase for lead, gain ratio for lag).

None of these are claimed to be optimal -- they are standard, reproducible designs.
Phase 3 then measures and ranks them, which is the whole point of a comparator.
"""

from __future__ import annotations

import numpy as np
import control as ct

from .base import Controller

# Laplace variable, reused across designs
_S = ct.tf("s")

# Derivative-filter coefficient for a realizable (proper) PID: Kd*s -> Kd*N*s/(s+N).
_DERIV_FILTER_N = 20.0


# ----------------------------------------------------------------- utilities

def _ultimate(plant) -> tuple[float, float] | None:
    """
    Return (Ku, Tu) from the ultimate-gain method, or None if it does not apply.

    Ku (ultimate gain)  = linear gain margin of the plant.
    Tu (ultimate period) = 2*pi / w, where w is the frequency at which the open-loop
                           phase crosses -180 deg (control's gain-margin crossover).
    """
    gm, _pm, wcg, _wcp = ct.margin(plant.tf)
    if not np.isfinite(gm) or gm <= 0 or not np.isfinite(wcg) or wcg <= 0:
        return None
    return float(gm), float(2.0 * np.pi / wcg)


def _design_crossover(plant) -> float:
    """A sensible design frequency: the dominant natural frequency (fallback 1.0)."""
    wc = plant.natural_frequency
    return wc if wc and wc > 1e-6 else 1.0


def _gain_at(plant, w: float) -> float:
    """|G(jw)| -- the plant's magnitude response at frequency w."""
    mag, _phase, _omega = ct.frequency_response(plant.tf, [w])
    return float(np.asarray(mag).ravel()[0])


# ------------------------------------------------------------------- designs

def design_p(plant) -> Controller:
    """Proportional controller  C(s) = Kp."""
    zn = _ultimate(plant)
    if zn:
        Ku, _Tu = zn
        Kp = 0.5 * Ku                     # ZN table: P -> 0.5 Ku
        method = "Ziegler-Nichols"
    else:
        wc = _design_crossover(plant)
        Kp = 1.0 / _gain_at(plant, wc)    # place gain crossover near wc
        method = "loop-shaping"
    return Controller("P", ct.tf([Kp], [1]), {"Kp": Kp}, method)


def design_pi(plant) -> Controller:
    """Proportional-Integral controller  C(s) = Kp + Ki/s."""
    zn = _ultimate(plant)
    if zn:
        Ku, Tu = zn
        Kp = 0.45 * Ku                    # ZN table: PI -> 0.45 Ku, Ti = Tu/1.2
        Ti = Tu / 1.2
        method = "Ziegler-Nichols"
    else:
        wc = _design_crossover(plant)
        Kp = 0.9 / _gain_at(plant, wc)
        Ti = 5.0 / wc                     # integral zero a decade below crossover
        method = "loop-shaping"
    Ki = Kp / Ti
    C = Kp + Ki / _S                      # = (Kp s + Ki) / s
    return Controller("PI", C, {"Kp": Kp, "Ki": Ki}, method)


def design_pid(plant) -> Controller:
    """
    Proportional-Integral-Derivative controller.

    Uses a filtered derivative so C(s) is proper (physically realizable):
        C(s) = Kp + Ki/s + Kd * N s / (s + N)
    """
    zn = _ultimate(plant)
    if zn:
        Ku, Tu = zn
        Kp = 0.6 * Ku                     # ZN table: PID -> 0.6 Ku, Ti = Tu/2, Td = Tu/8
        Ti, Td = Tu / 2.0, Tu / 8.0
        method = "Ziegler-Nichols"
    else:
        wc = _design_crossover(plant)
        Kp = 1.0 / _gain_at(plant, wc)
        Ti, Td = 5.0 / wc, 1.0 / (2.0 * wc)
        method = "loop-shaping"
    Ki, Kd = Kp / Ti, Kp * Td
    N = _DERIV_FILTER_N
    C = Kp + Ki / _S + Kd * N * _S / (_S + N)
    return Controller("PID", C, {"Kp": Kp, "Ki": Ki, "Kd": Kd}, method)


def design_lead(plant, added_phase_deg: float = 40.0) -> Controller:
    """
    Phase-lead compensator  C(s) = (s + z) / (s + p),  z < p.

    A lead network adds phase (up to `added_phase_deg`) around the design frequency,
    which speeds up the response and improves stability margins. The maximum phase
    boost occurs at wm = sqrt(z*p), set here to the plant's natural frequency.
    """
    phi = np.radians(np.clip(added_phase_deg, 1.0, 85.0))
    alpha = (1.0 - np.sin(phi)) / (1.0 + np.sin(phi))     # 0 < alpha < 1
    wm = _design_crossover(plant)
    z = wm * np.sqrt(alpha)              # zero
    p = wm / np.sqrt(alpha)              # pole (p > z -> lead)
    C = (_S + z) / (_S + p)
    return Controller("Lead", C, {"z": float(z), "p": float(p), "alpha": float(alpha)},
                      "phase-lead")


def design_lag(plant, beta: float = 10.0) -> Controller:
    """
    Lag compensator  C(s) = (s + z) / (s + z/beta),  beta > 1.

    A lag network has a DC gain of `beta`, which reduces steady-state error, at the
    cost of a slightly slower response. The zero is placed a decade below the design
    frequency so the added phase lag does not hurt stability near crossover.
    """
    beta = max(float(beta), 1.001)
    wc = _design_crossover(plant)
    z = wc / 10.0                        # zero a decade below crossover
    p = z / beta                         # pole near the origin
    C = (_S + z) / (_S + p)
    return Controller("Lag", C, {"z": float(z), "p": float(p), "beta": beta}, "lag")


def design_all(plant) -> dict[str, Controller]:
    """Design all five classical controllers for a plant, keyed by name."""
    return {
        c.name: c
        for c in (
            design_p(plant),
            design_pi(plant),
            design_pid(plant),
            design_lead(plant),
            design_lag(plant),
        )
    }
