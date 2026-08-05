"""
Controller container and closed-loop helpers.

Every controller in ControlBench is represented the same way: a transfer function
C(s) plus the parameters and method used to design it. That common shape is what lets
Phase 3 loop over five very different controllers and score them identically.

We use the standard unity-feedback configuration:

    r --->(+)---> C(s) ---> G(s) ---+---> y
           ^-                       |
           |________________________|

    open loop     L(s) = C(s) G(s)
    closed loop   T(s) = L(s) / (1 + L(s))
"""

from __future__ import annotations

from dataclasses import dataclass, field

import control as ct


@dataclass(frozen=True)
class Controller:
    """A designed controller: its transfer function plus how it was built."""

    name: str                        # e.g. "PID"
    tf: ct.TransferFunction          # the controller C(s)
    params: dict = field(default_factory=dict)   # e.g. {"Kp": .., "Ki": .., "Kd": ..}
    method: str = ""                 # e.g. "Ziegler-Nichols" / "loop-shaping" / "phase-lead"

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        p = ", ".join(f"{k}={v:.4g}" for k, v in self.params.items())
        return f"Controller({self.name}: {p} | {self.method})"


def open_loop(plant, controller: Controller) -> ct.TransferFunction:
    """Open-loop transfer function L(s) = C(s) G(s)."""
    return ct.series(controller.tf, plant.tf)


def closed_loop(plant, controller: Controller) -> ct.TransferFunction:
    """Closed-loop transfer function T(s) = L / (1 + L) with unity feedback."""
    return ct.feedback(open_loop(plant, controller), 1)
