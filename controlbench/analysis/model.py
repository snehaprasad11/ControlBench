"""
PlantModel — a validated wrapper around a continuous-time transfer function G(s).

A transfer function is  G(s) = num(s) / den(s)  where num and den are polynomials
in the Laplace variable s, given as coefficient lists in *descending* powers.
For example  [1]  and  [1, 2, 1]  represent

              1
    G(s) = -----------
           s^2 + 2s + 1

This class validates the model, then exposes the quantities every downstream part
of ControlBench needs: poles, zeros, order, open-loop stability, and the damping
ratio / natural frequency of the dominant pole pair.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import control as ct


class InvalidPlantError(ValueError):
    """Raised when the supplied coefficients do not describe a usable plant."""


@dataclass(frozen=True)
class PlantModel:
    """A continuous-time SISO plant described by a transfer function G(s)."""

    num: tuple[float, ...]
    den: tuple[float, ...]

    # ------------------------------------------------------------------ build
    def __init__(self, num, den):
        num = _clean(num, "numerator")
        den = _clean(den, "denominator")

        # A denominator of all zeros (or empty) has no meaning: G would be 1/0.
        if not den or np.allclose(den, 0.0):
            raise InvalidPlantError("Denominator must have at least one non-zero coefficient.")

        # Strip leading zeros so the true polynomial degree is correct
        # (e.g. [0, 1, 2] is really the first-order polynomial [1, 2]).
        num = _strip_leading_zeros(num) or (0.0,)
        den = _strip_leading_zeros(den)

        # Properness: a physical (causal) system cannot have a numerator of higher
        # degree than its denominator. deg = len(coeffs) - 1.
        if (len(num) - 1) > (len(den) - 1):
            raise InvalidPlantError(
                f"Improper transfer function: numerator degree {len(num) - 1} "
                f"exceeds denominator degree {len(den) - 1}. "
                "A physical system must have deg(num) <= deg(den)."
            )

        # dataclass is frozen, so set fields via object.__setattr__
        object.__setattr__(self, "num", tuple(float(c) for c in num))
        object.__setattr__(self, "den", tuple(float(c) for c in den))

    # ------------------------------------------------------------- transfer fn
    @property
    def tf(self) -> ct.TransferFunction:
        """The underlying python-control TransferFunction object."""
        return ct.tf(list(self.num), list(self.den))

    # --------------------------------------------------------------- structure
    @property
    def order(self) -> int:
        """System order = degree of the denominator = number of poles."""
        return len(self.den) - 1

    @property
    def poles(self) -> np.ndarray:
        """Poles = roots of the denominator. They govern stability and speed."""
        return ct.poles(self.tf)

    @property
    def zeros(self) -> np.ndarray:
        """Zeros = roots of the numerator. They shape the transient response."""
        return ct.zeros(self.tf)

    # --------------------------------------------------------------- stability
    @property
    def is_stable(self) -> bool:
        """Open-loop stable iff every pole has a strictly negative real part."""
        p = self.poles
        return bool(p.size == 0 or np.all(np.real(p) < 0))

    # --------------------------------------------- dominant-pole descriptors
    @property
    def natural_frequency(self) -> float:
        """
        Natural frequency w_n (rad/s) of the dominant (slowest) pole pair.

        The dominant poles are the ones closest to the imaginary axis; they
        dominate how the response looks. w_n is the distance of that pole from
        the origin in the s-plane.
        """
        return _dominant(self.poles)[0]

    @property
    def damping_ratio(self) -> float:
        """
        Damping ratio zeta of the dominant pole pair (dimensionless).

        zeta < 1  -> underdamped (oscillatory)
        zeta = 1  -> critically damped
        zeta > 1  -> overdamped (no oscillation)
        """
        return _dominant(self.poles)[1]

    # ----------------------------------------------------------------- summary
    def summary(self) -> dict:
        """A plain-dict snapshot of the plant, handy for logs, the UI and the ML features."""
        return {
            "num": list(self.num),
            "den": list(self.den),
            "order": self.order,
            "poles": [complex(p) for p in self.poles],
            "zeros": [complex(z) for z in self.zeros],
            "is_stable": self.is_stable,
            "natural_frequency": self.natural_frequency,
            "damping_ratio": self.damping_ratio,
        }

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"PlantModel(num={list(self.num)}, den={list(self.den)}, order={self.order})"


# ---------------------------------------------------------------- helpers

def _clean(coeffs, name: str) -> list[float]:
    """Coerce an input into a flat list of finite floats, or raise."""
    arr = np.atleast_1d(np.asarray(coeffs, dtype=float)).ravel()
    if arr.size == 0:
        raise InvalidPlantError(f"The {name} must contain at least one coefficient.")
    if not np.all(np.isfinite(arr)):
        raise InvalidPlantError(f"The {name} contains non-finite values (inf/NaN).")
    return arr.tolist()


def _strip_leading_zeros(coeffs: list[float]) -> list[float]:
    """Drop leading zeros so the polynomial degree is not overstated."""
    out = list(coeffs)
    while len(out) > 1 and out[0] == 0.0:
        out.pop(0)
    return out


def _dominant(poles: np.ndarray) -> tuple[float, float]:
    """
    Return (natural_frequency, damping_ratio) for the dominant pole(s).

    For a pole p = -sigma +/- j*wd:
        w_n  = |p|                     (distance from origin)
        zeta = -real(p) / |p|          (cosine of the angle from the negative real axis)
    We pick the pole with the largest real part (closest to instability / slowest decay)
    as the dominant one.
    """
    if poles.size == 0:
        return 0.0, 0.0
    dominant = poles[np.argmax(np.real(poles))]
    wn = float(np.abs(dominant))
    if wn == 0.0:
        return 0.0, 0.0
    zeta = float(-np.real(dominant) / wn)
    return wn, zeta
