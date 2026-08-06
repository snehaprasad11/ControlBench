"""
System identification — fit a continuous transfer function to measured input/output data.

This is what lets ControlBench work on a *real* physical system: given sampled input
u[k] and output y[k], we

  1. fit a discrete ARX model  A(q) y = B(q) u  by linear least squares,
  2. map its poles to continuous time (s = ln(z) / Ts) and match the DC gain,

producing a `PlantModel` G(s) that the rest of ControlBench can analyse and control.

The continuous model is pole-only (numerator is a DC-matched constant): robust, always
real-coefficient, and a good fit for the well-damped processes these datasets contain.
Identification from noisy real data is approximate -- always check the reported fit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import control as ct

from .analysis import PlantModel


@dataclass
class SysIDResult:
    """Outcome of identifying a plant from data."""

    plant: PlantModel          # identified continuous G(s)
    a: np.ndarray              # discrete AR coefficients [a1..a_na]
    b: np.ndarray              # discrete input coefficients [b1..b_nb]
    Ts: float                  # sampling interval (s)
    nk: int                    # input delay (samples)
    fit_percent: float         # free-run simulation fit (100 = perfect)
    y_sim: np.ndarray          # simulated (detrended) output
    u_mean: float
    y_mean: float


def arx_fit(u, y, na: int, nb: int, nk: int) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares ARX fit: returns (a, b) for A(q)y = B(q)u."""
    u = np.asarray(u, float); y = np.asarray(y, float)
    n = len(y)
    p = max(na, nb + nk - 1)
    rows, target = [], []
    for k in range(p, n):
        ry = [-y[k - 1 - i] for i in range(na)]
        ru = [u[k - nk - j] for j in range(nb)]
        rows.append(ry + ru)
        target.append(y[k])
    theta, *_ = np.linalg.lstsq(np.asarray(rows), np.asarray(target), rcond=None)
    return theta[:na], theta[na:]


def arx_simulate(u, y, a, b, nk: int) -> np.ndarray:
    """Free-run (infinite-horizon) simulation of an ARX model on input u."""
    u = np.asarray(u, float); y = np.asarray(y, float)
    na, nb = len(a), len(b)
    n = len(u)
    p = max(na, nb + nk - 1)
    yh = np.zeros(n)
    yh[:p] = y[:p]                      # seed with measured initial conditions
    for k in range(p, n):
        yh[k] = (sum(-a[i] * yh[k - 1 - i] for i in range(na))
                 + sum(b[j] * u[k - nk - j] for j in range(nb)))
    return yh


def arx_to_continuous(a, b, Ts: float) -> PlantModel:
    """
    Convert a discrete ARX model to a continuous, pole-only PlantModel.

    Poles are mapped by s = ln(z)/Ts; the numerator is a single gain chosen so the
    continuous DC gain equals the discrete model's DC gain H(1) = sum(b)/(1+sum(a)).
    """
    a = np.asarray(a, float); b = np.asarray(b, float)
    den_z = np.concatenate([[1.0], a])          # z^na + a1 z^(na-1) + ...
    z_poles = np.roots(den_z)
    s_poles = np.log(z_poles.astype(complex)) / Ts
    den_s = np.real(np.poly(s_poles))           # monic continuous denominator

    dc_gain = float(np.sum(b) / (1.0 + np.sum(a)))
    K = dc_gain * den_s[-1]                      # so K/den_s(0) == dc_gain
    return PlantModel([K], den_s.tolist())


def fit_percent(y, y_hat) -> float:
    """Normalised fit in percent (100 = perfect; matches the usual system-ID metric)."""
    y = np.asarray(y, float); y_hat = np.asarray(y_hat, float)
    denom = np.linalg.norm(y - y.mean())
    if denom == 0:
        return 0.0
    return float(100.0 * (1.0 - np.linalg.norm(y - y_hat) / denom))


def identify_plant(u, y, Ts: float, na: int = 2, nb: int = 1, nk: int = 1) -> SysIDResult:
    """
    Full pipeline: detrend, ARX-fit, free-run validate, convert to continuous G(s).

    Data is detrended (means removed) because ARX has no constant term, so the model
    describes deviations about the operating point -- exactly what a controller regulates.
    """
    u = np.asarray(u, float); y = np.asarray(y, float)
    u_mean, y_mean = float(u.mean()), float(y.mean())
    ud, yd = u - u_mean, y - y_mean

    a, b = arx_fit(ud, yd, na, nb, nk)
    plant = arx_to_continuous(a, b, Ts)

    # Validate the CONTINUOUS model we actually hand to ControlBench (not the
    # intermediate discrete ARX): simulate G(s) on the measured input and compare.
    t = np.arange(len(ud)) * Ts
    _, y_sim = ct.forced_response(plant.tf, T=t, U=ud)
    fit = fit_percent(yd, y_sim)

    return SysIDResult(plant, a, b, Ts, nk, fit, np.asarray(y_sim), u_mean, y_mean)
