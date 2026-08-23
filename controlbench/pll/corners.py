"""
PVT (Process / Voltage / Temperature) corners.

On silicon, a loop filter is designed once (fixed R, C) but the *chip* parameters it
works with drift with process, supply voltage and temperature. The two that dominate a
charge-pump PLL are:

  * **Kvco** — the VCO gain swings widely (band-to-band + PVT), commonly +/-25-30%;
  * **Icp**  — the charge-pump current drifts with supply/temperature, ~ +/-10%.

Optionally the passive components themselves have tolerance (R, C +/- a few %). As Kvco or
Icp rise, the loop gain rises, pushing the crossover up and *eating phase margin*; as they
fall, the loop slows down. A design is only trustworthy if it stays in spec across the
whole box of variation — which is what :mod:`.robust` checks using the corners built here.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from .model import LoopFilter, PLLModel


@dataclass(frozen=True)
class CornerSpec:
    """Fractional variation of each perturbed parameter (0.30 = +/-30%)."""

    kvco_tol: float = 0.30
    icp_tol: float = 0.10
    comp_tol: float = 0.0        # R and C tolerance; 0 => ideal components

    def enabled(self) -> dict[str, float]:
        """The dimensions that actually vary (tol > 0), mapped to their tolerance."""
        dims = {"kvco": self.kvco_tol, "icp": self.icp_tol, "comp": self.comp_tol}
        return {k: v for k, v in dims.items() if v > 0}


@dataclass(frozen=True)
class Corner:
    """One operating corner: multipliers applied to the nominal design."""

    name: str
    kvco_mult: float = 1.0
    icp_mult: float = 1.0
    r_mult: float = 1.0
    c_mult: float = 1.0

    @property
    def is_nominal(self) -> bool:
        return (self.kvco_mult == 1.0 and self.icp_mult == 1.0
                and self.r_mult == 1.0 and self.c_mult == 1.0)


def generate_corners(spec: CornerSpec) -> list[Corner]:
    """Nominal plus every extreme combination of the enabled variation dimensions.

    With Kvco and Icp enabled that is the 4 box corners + nominal (5 total); enabling
    component tolerance adds the R/C extremes, doubling the box per extra dimension.
    """
    enabled = spec.enabled()
    corners = [Corner(name="TT (nominal)")]
    if not enabled:
        return corners

    # Each enabled dimension contributes a low/high pair of signed multipliers.
    axes: list[tuple[str, list[tuple[str, float]]]] = []
    for dim, tol in enabled.items():
        axes.append((dim, [("-", 1.0 - tol), ("+", 1.0 + tol)]))

    for combo in itertools.product(*[opts for _dim, opts in axes]):
        kvco = icp = r = c = 1.0
        label_parts = []
        for (dim, _opts), (sign, mult) in zip(axes, combo):
            label_parts.append(f"{dim}{sign}")
            if dim == "kvco":
                kvco = mult
            elif dim == "icp":
                icp = mult
            elif dim == "comp":
                # Worst-case component drift: push R and C the same signed way, which
                # moves the zero/pole together (a conservative single-knob model).
                r = c = mult
        corners.append(Corner(name=", ".join(label_parts),
                              kvco_mult=kvco, icp_mult=icp, r_mult=r, c_mult=c))
    return corners


def apply_corner(nominal: PLLModel, corner: Corner) -> PLLModel:
    """Rebuild a PLL at a corner: perturb Kvco, Icp and (optionally) the components."""
    lf = nominal.loop_filter
    perturbed_lf = LoopFilter(
        r=lf.r * corner.r_mult,
        c_main=lf.c_main * corner.c_mult,
        c_shunt=lf.c_shunt * corner.c_mult,
    )
    return PLLModel(
        device=nominal.device,
        icp_a=nominal.icp_a * corner.icp_mult,
        n=nominal.n,
        loop_filter=perturbed_lf,
        kvco_rad_per_v=nominal.kvco_rad_per_v * corner.kvco_mult,
    )
