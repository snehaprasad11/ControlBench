"""
Phase 2 demo — design all five controllers for a plant and close the loop.

    python scripts/demo_phase2.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import control as ct

from controlbench.analysis import PlantModel
from controlbench.controllers import design_all, closed_loop


PLANTS = {
    "3rd-order  1/(s+1)^3   (ZN applies)": ([1], [1, 3, 3, 1]),
    "2nd-order  1/(s^2+2s+1) (loop-shaping)": ([1], [1, 2, 1]),
}


def main() -> None:
    for label, (num, den) in PLANTS.items():
        print("=" * 72)
        print(label)
        plant = PlantModel(num, den)
        controllers = design_all(plant)

        header = f"  {'controller':<10}{'method':<18}{'settling(s)':>12}{'overshoot(%)':>14}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for name, c in controllers.items():
            T = closed_loop(plant, c)
            info = ct.step_info(T)
            print(f"  {name:<10}{c.method:<18}"
                  f"{info['SettlingTime']:>12.3f}{info['Overshoot']:>14.2f}")


if __name__ == "__main__":
    main()
