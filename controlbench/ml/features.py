"""
Feature extraction — turn a (variable-size) transfer function into a fixed-length
numeric vector the ML models can consume.

Plants have different orders, so we standardise on a maximum order and pad. Each
plant becomes nine features: its structural descriptors (order, damping ratio,
natural frequency, DC gain) plus the monic denominator coefficients and a compact
numerator representation.
"""

from __future__ import annotations

import numpy as np
import control as ct

MAX_ORDER = 3

# Feature values are clipped to this magnitude. The models are trained only on
# strictly-stable plants (finite features), but a user may query a marginally
# stable / integrator plant whose DC gain is infinite -- clipping keeps such
# out-of-distribution inputs from crashing the models with inf/NaN.
_FEATURE_CAP = 1e6

FEATURE_NAMES = [
    "order",
    "damping_ratio",
    "natural_frequency",
    "dc_gain",
    "den_a1", "den_a2", "den_a3",   # monic denominator coefficients (padded)
    "num_s", "num_1",               # numerator: s-coefficient and constant term
]


def plant_features(plant) -> dict:
    """Extract the fixed-length feature dict for a plant."""
    den = list(plant.den)
    num = list(plant.num)

    # Make the denominator monic (leading coefficient 1) and scale the numerator
    # by the same factor, so the transfer function is unchanged but coefficients
    # are comparable across plants.
    lead = den[0]
    den_monic = [c / lead for c in den]
    num_scaled = [c / lead for c in num]

    a = den_monic[1:]                          # a1 .. a_n
    a = a + [0.0] * (MAX_ORDER - len(a))       # pad to MAX_ORDER

    num_const = num_scaled[-1]                 # constant term
    num_s = num_scaled[-2] if len(num_scaled) >= 2 else 0.0

    raw = {
        "order": float(plant.order),
        "damping_ratio": float(plant.damping_ratio),
        "natural_frequency": float(plant.natural_frequency),
        "dc_gain": float(ct.dcgain(plant.tf)),
        "den_a1": float(a[0]), "den_a2": float(a[1]), "den_a3": float(a[2]),
        "num_s": float(num_s), "num_1": float(num_const),
    }
    # Guarantee every feature is finite (see _FEATURE_CAP note above).
    return {k: float(np.nan_to_num(v, nan=0.0, posinf=_FEATURE_CAP, neginf=-_FEATURE_CAP))
            for k, v in raw.items()}
