"""
Synthetic dataset generation.

We build thousands of random *stable* plants, run the full ControlBench comparison
on each, and record (features -> best controller + its settling time and overshoot).
That labelled table is what the ML models learn from. Because every row is produced
by the exact simulator, the model has clean ground truth to imitate.

Stable plants are built by *placing poles* in the left-half plane (real poles and
complex-conjugate pairs) and expanding to a polynomial -- this guarantees stability
by construction and gives a realistic spread of damping ratios and natural frequencies.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..analysis import PlantModel
from ..compare import compare_controllers
from .features import FEATURE_NAMES, plant_features

TARGET_NAMES = ["best_controller", "best_settling_time", "best_overshoot", "best_score"]


def random_stable_plant(rng: np.random.Generator, max_order: int = 3) -> PlantModel:
    """Draw a random stable plant of order 1..max_order by placing LHP poles."""
    order = int(rng.integers(1, max_order + 1))

    poles: list[complex] = []
    remaining = order
    while remaining > 0:
        if remaining >= 2 and rng.random() < 0.5:
            # complex-conjugate pair from a natural frequency and damping ratio
            wn = rng.uniform(0.3, 5.0)
            zeta = rng.uniform(0.1, 0.99)
            re = -zeta * wn
            im = wn * np.sqrt(1.0 - zeta**2)
            poles += [complex(re, im), complex(re, -im)]
            remaining -= 2
        else:
            poles.append(complex(-rng.uniform(0.2, 5.0), 0.0))
            remaining -= 1

    den = np.real(np.poly(poles))              # monic polynomial from roots

    # Numerator: usually a plain gain; sometimes a single (stable) zero.
    if order >= 2 and rng.random() < 0.3:
        z = -rng.uniform(0.2, 5.0)
        num = np.real(np.poly([z])) * rng.uniform(0.5, 2.0)
    else:
        num = np.array([rng.uniform(0.5, 2.0)])

    return PlantModel(num.tolist(), den.tolist())


def generate_dataset(
    n: int,
    seed: int = 0,
    weights: dict[str, float] | None = None,
    max_order: int = 3,
) -> pd.DataFrame:
    """
    Generate `n` labelled rows: plant features plus the winning controller and its
    settling time, overshoot and composite score. Degenerate plants (where even the
    best controller fails to stabilise) are skipped and redrawn.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict] = []

    while len(rows) < n:
        plant = random_stable_plant(rng, max_order)
        try:
            ranked, _controllers, _metrics = compare_controllers(plant, weights)
        except Exception:
            continue                            # numerically pathological draw; skip
        best = ranked[0]
        if not best.metrics.stable:
            continue                            # no controller stabilised it; skip

        row = plant_features(plant)
        row["best_controller"] = best.name
        row["best_settling_time"] = best.metrics.settling_time
        row["best_overshoot"] = best.metrics.overshoot
        row["best_score"] = best.score
        rows.append(row)

    return pd.DataFrame(rows, columns=FEATURE_NAMES + TARGET_NAMES)


def save_dataset(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_dataset(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)
