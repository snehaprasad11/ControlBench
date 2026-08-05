"""
Phase 1 demo — run the analysis engine on a few classic plants.

    python scripts/demo_phase1.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controlbench.analysis import PlantModel, InvalidPlantError


EXAMPLES = {
    "Underdamped 2nd-order  1/(s^2+2s+1)": ([1], [1, 2, 1]),
    "Oscillatory  1/(s^2+0.4s+1)":          ([1], [1, 0.4, 1]),
    "First-order lag  1/(s+2)":             ([1], [1, 2]),
    "Unstable  1/(s^2-s+1)":                ([1], [1, -1, 1]),
    "With a zero  (s+3)/(s^2+3s+2)":        ([1, 3], [1, 3, 2]),
}


def fmt_complex(z) -> str:
    return f"{z.real:+.3f}{z.imag:+.3f}j"


def main() -> None:
    for label, (num, den) in EXAMPLES.items():
        print("=" * 68)
        print(label)
        plant = PlantModel(num, den)
        s = plant.summary()
        print(f"  order            : {s['order']}")
        print(f"  poles            : {', '.join(fmt_complex(p) for p in s['poles'])}")
        print(f"  zeros            : {', '.join(fmt_complex(z) for z in s['zeros']) or '(none)'}")
        print(f"  stable           : {s['is_stable']}")
        print(f"  natural freq wn  : {s['natural_frequency']:.3f} rad/s")
        print(f"  damping ratio z  : {s['damping_ratio']:.3f}")

    # Show validation catching a bad (improper) model
    print("=" * 68)
    print("Validation check — improper TF  s^2/(s+1):")
    try:
        PlantModel([1, 0, 0], [1, 1])
    except InvalidPlantError as e:
        print(f"  rejected as expected -> {e}")


if __name__ == "__main__":
    main()
