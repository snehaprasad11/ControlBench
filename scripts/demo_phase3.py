"""
Phase 3 demo — full comparison leaderboard for a plant.

    python scripts/demo_phase3.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controlbench.analysis import PlantModel
from controlbench.compare import compare_controllers


def fmt(x, unit=""):
    if x == float("inf"):
        return "  inf"
    return f"{x:6.2f}{unit}"


def show(label, num, den):
    print("=" * 84)
    print(label)
    plant = PlantModel(num, den)
    ranked, controllers, _metrics = compare_controllers(plant)

    hdr = (f"  {'#':<2}{'controller':<11}{'score':>7}"
           f"{'rise':>8}{'settle':>9}{'over%':>8}{'ss_err':>9}{'GM(dB)':>9}{'PM(deg)':>9}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for i, r in enumerate(ranked, 1):
        m = r.metrics
        print(f"  {i:<2}{r.name:<11}{r.score:>7.3f}"
              f"{fmt(m.rise_time):>8}{fmt(m.settling_time):>9}{fmt(m.overshoot):>8}"
              f"{fmt(m.steady_state_error):>9}{fmt(m.gain_margin_db):>9}{fmt(m.phase_margin_deg):>9}")
    best = ranked[0]
    print(f"\n  -> Recommended: {best.name}  (method: {controllers[best.name].method}, "
          f"score {best.score:.3f})")


def main():
    show("Plant A:  1/(s+1)^3", [1], [1, 3, 3, 1])
    show("Plant B:  1/(s^2 + 2s + 1)", [1], [1, 2, 1])
    show("Plant C:  1/(s(s+1))   (has an integrator)", [1], [1, 1, 0])


if __name__ == "__main__":
    main()
