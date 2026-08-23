"""
Build the PLL ML surrogate: generate a model-labelled dataset and train the regressor.

    python scripts/build_pll_ml.py [n_samples]

Writes:
    data/pll_dataset.csv          the training rows (features + worst-case labels)
    models/pll_surrogate.joblib   the trained multi-output random forest
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controlbench.pll import ml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / "data" / "pll_dataset.csv"
MODEL_PATH = ROOT / "models" / "pll_surrogate.joblib"


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    print(f"Generating {n} model-labelled PLL designs across the real device library...")
    X, Y = ml.make_dataset(n_samples=n, seed=0)
    print(f"  got {len(X)} valid samples.")

    header = ",".join(ml.FEATURES + ml.LABELS)
    np.savetxt(DATA_CSV, np.hstack([X, Y]), delimiter=",", header=header, comments="")
    print(f"  wrote {DATA_CSV}")

    print("Training random-forest surrogate...")
    model, r2 = ml.train(X, Y)
    ml.save(model, MODEL_PATH)
    print(f"  wrote {MODEL_PATH}")
    print("  R^2 (held-out):")
    for label, score in r2.items():
        print(f"    {label:32s} {score:6.3f}")


if __name__ == "__main__":
    main()
