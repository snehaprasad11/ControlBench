"""
Loop-filter design.

Given a real device (Icp, Kvco, N) and two targets a designer actually specifies —
a **loop bandwidth** f_c and a **phase margin** phi — synthesise the passive loop
filter (R, C_main, C_shunt) that hits them.

We use the standard third-order passive design (the method behind TI's PLLatinum and
ADI's ADIsimPLL tools), which places the filter's zero and high-frequency pole
symmetrically about the crossover so that the phase margin is *maximised at f_c*:

    T1 = (sec(phi) - tan(phi)) / w_c          # high-frequency pole time constant
    T2 = 1 / (w_c^2 * T1)                      # zero time constant  (T2 > T1)

    C_shunt = (T1/T2) * (K / w_c^2) * sqrt( (1 + (w_c*T2)^2) / (1 + (w_c*T1)^2) )
    C_main  = C_shunt * (T2/T1 - 1)
    R       = T2 / C_main

with K = Icp*Kvco/(2*pi*N) the loop's forward-gain constant. The formulas are exact
for the linear model; we still *measure* the achieved margin/bandwidth numerically in
:mod:`.metrics` rather than trusting the closed form (see the design self-check test).
"""

from __future__ import annotations

import math

from .devices import Device, TWO_PI
from .model import LoopFilter, PLLModel


def _forward_gain(icp_a: float, kvco_rad_per_v: float, n: float) -> float:
    return icp_a * kvco_rad_per_v / (TWO_PI * n)


def design_loop_filter(icp_a: float, kvco_rad_per_v: float, n: float,
                       fc_hz: float, phase_margin_deg: float) -> LoopFilter:
    """Synthesise a 3rd-order passive loop filter for a target f_c and phase margin.

    Parameters are in SI (Icp in A, Kvco in rad/s/V, fc in Hz, margin in degrees).
    Returns the :class:`~controlbench.pll.model.LoopFilter` (R, C_main, C_shunt).
    """
    if not (0.0 < phase_margin_deg < 90.0):
        raise ValueError("phase_margin_deg must be strictly between 0 and 90 degrees.")
    if fc_hz <= 0:
        raise ValueError("fc_hz (loop bandwidth) must be positive.")

    wc = TWO_PI * fc_hz
    phi = math.radians(phase_margin_deg)
    k = _forward_gain(icp_a, kvco_rad_per_v, n)

    t1 = (1.0 / math.cos(phi) - math.tan(phi)) / wc
    t2 = 1.0 / (wc * wc * t1)

    c_shunt = (t1 / t2) * (k / (wc * wc)) * math.sqrt(
        (1.0 + (wc * t2) ** 2) / (1.0 + (wc * t1) ** 2)
    )
    c_main = c_shunt * (t2 / t1 - 1.0)
    r = t2 / c_main
    return LoopFilter(r=r, c_main=c_main, c_shunt=c_shunt)


def design_pll(device: Device, n: float, fc_hz: float, phase_margin_deg: float,
               icp_a: float | None = None,
               kvco_rad_per_v: float | None = None) -> PLLModel:
    """Design a full PLL loop for a device against (loop bandwidth, phase margin).

    ``icp_a`` and ``kvco_rad_per_v`` default to the device's datasheet values; they are
    exposed so the PVT-corner engine can design at, or perturb to, other operating points.
    """
    icp = icp_a if icp_a is not None else device.icp_default_a
    kv = kvco_rad_per_v if kvco_rad_per_v is not None else device.kvco_rad_per_v
    lf = design_loop_filter(icp, kv, n, fc_hz, phase_margin_deg)
    return PLLModel(device=device, icp_a=icp, n=n, loop_filter=lf, kvco_rad_per_v=kv)


def divider_for_output(device: Device, f_out_hz: float, f_pfd_hz: float) -> float:
    """Feedback divider N tying an output frequency to the phase-detector frequency.

    For an integer-N loop N = f_vco / f_pfd. This is a convenience for the API/UI so a
    user can think in "output frequency" instead of raw divider counts.
    """
    if f_pfd_hz <= 0:
        raise ValueError("f_pfd_hz must be positive.")
    return f_out_hz / f_pfd_hz
