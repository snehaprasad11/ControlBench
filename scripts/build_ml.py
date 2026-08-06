"""
Build the ML artifacts: generate the dataset, train the models, save both.

    python scripts/build_ml.py [n_samples]

Writes:
    data/dataset.csv
    models/*.joblib
and prints held-out test scores.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controlbench.ml import (
    generate_dataset, save_dataset, load_dataset, train_models, save_models,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    csv = ROOT / "data" / "dataset.csv"

    # Reuse an existing dataset if present (retraining is seconds); pass "regen" to
    # force fresh generation, e.g.  python scripts/build_ml.py 2000 regen
    regen = "regen" in sys.argv[2:]
    if csv.exists() and not regen:
        print(f"[1/3] Loading existing dataset {csv} ...")
        df = load_dataset(csv)
        print(f"      {len(df)} rows (pass 'regen' to rebuild)")
    else:
        print(f"[1/3] Generating {n} labelled plants (full simulation per plant)...")
        t0 = time.time()
        df = generate_dataset(n, seed=42)
        print(f"      done in {time.time() - t0:.1f}s")
        save_dataset(df, csv)
        print(f"      saved data/dataset.csv ({len(df)} rows)")

    print("      controller class balance:")
    print(df["best_controller"].value_counts().to_string())

    print("[2/3] Training classifier + two regressors...")
    t1 = time.time()
    models = train_models(df, seed=42)
    print(f"      trained in {time.time() - t1:.1f}s")

    print("[3/3] Held-out test scores:")
    for k, v in models["scores"].items():
        print(f"      {k:22} {v:.4f}" if isinstance(v, float) else f"      {k:22} {v}")

    save_models(models, ROOT / "models")
    print("      saved models/*.joblib")
    print("DONE")


if __name__ == "__main__":
    main()
