"""
The PLL as a control loop.

A charge-pump PLL is a negative-feedback system that forces an output clock's phase
to track a reference. In transfer-function form the forward path is

    phase error --> [charge pump: Icp/2pi] --> [loop filter: Z(s)] --> [VCO: Kvco/s] --> phase out

and the loop is closed through the feedback divider (1/N). So the **open-loop gain** is

                Icp * Kvco      Z(s)
    L(s) =    -------------  *  ----          (Kvco here is in rad/s/V)
                 2*pi * N        s

The 1/s is the VCO integrating frequency into phase; it plus the pole the loop filter
puts at the origin make this a **type-II** loop (two poles at s=0), which is why the
filter's zero is essential for stability.

Mapping onto ControlBench's plant/controller split:
  * the **plant** is fixed by the chip: charge pump, VCO (Kvco/s) and divider (1/N);
  * the **controller** is the **loop filter** Z(s) (its R, C values) plus the choice of Icp.

This module builds L(s) and the closed-loop phase transfer H(s) = L/(1+L); everything
downstream (:mod:`.metrics`) measures those with the same machinery ControlBench already
uses for classical controllers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import control as ct

from .devices import Device, TWO_PI


@dataclass(frozen=True)
class LoopFilter:
    """A passive charge-pump loop filter (the PLL's 'controller').

    Second order (``c_shunt == 0``):  Z(s) = (1 + s*R*C) / (s*C)
        - one pole at the origin, one zero at 1/(R*C).

    Third order (``c_shunt > 0``):    a shunt cap C_p is added at the charge-pump
    output to suppress ripple / reference spurs, adding a high-frequency pole:

                    1 + s*R*C_main
        Z(s) = --------------------------------------------------------
                s*(C_main+C_p) * (1 + s*R * C_main*C_p/(C_main+C_p))

        - pole at the origin, zero at 1/(R*C_main), extra pole at (C_main+C_p)/(R*C_main*C_p).
    """

    r: float            # series resistor R2 [ohm]
    c_main: float       # main / zero-forming cap [F]
    c_shunt: float = 0.0  # shunt pole cap [F]; 0 => second-order filter

    @property
    def order(self) -> int:
        return 3 if self.c_shunt > 0 else 2

    @property
    def zero_hz(self) -> float:
        """Frequency of the loop-filter zero (Hz) — the stabilising element."""
        return 1.0 / (TWO_PI * self.r * self.c_main)

    @property
    def pole3_hz(self) -> float:
        """Frequency of the third (ripple-suppression) pole (Hz), or inf if 2nd order."""
        if self.c_shunt <= 0:
            return float("inf")
        tau = self.r * (self.c_main * self.c_shunt) / (self.c_main + self.c_shunt)
        return 1.0 / (TWO_PI * tau)

    def impedance_tf(self) -> ct.TransferFunction:
        """The loop-filter transfer impedance Z(s) [ohm] as a python-control tf."""
        if self.c_shunt <= 0:
            # Z(s) = (R*C s + 1) / (C s)
            return ct.tf([self.r * self.c_main, 1.0], [self.c_main, 0.0])
        c1, c2, r = self.c_main, self.c_shunt, self.r
        ct_par = c1 * c2 / (c1 + c2)
        num = [r * c1, 1.0]
        den = [(c1 + c2) * r * ct_par, (c1 + c2), 0.0]
        return ct.tf(num, den)

    def summary(self) -> dict:
        return {
            "order": self.order,
            "r_ohm": self.r,
            "c_main_f": self.c_main,
            "c_shunt_f": self.c_shunt,
            "zero_hz": self.zero_hz,
            "pole3_hz": self.pole3_hz,
        }


@dataclass(frozen=True)
class PLLModel:
    """A concrete PLL: a real device, a chosen Icp, a divider N and a loop filter.

    Exposes the open-loop L(s) and closed-loop phase transfer H(s), from which
    :mod:`.metrics` reads loop bandwidth, phase/gain margin, lock time and jitter
    peaking.
    """

    device: Device
    icp_a: float            # chosen charge-pump current [A]
    n: float                # feedback divider ratio
    loop_filter: LoopFilter
    kvco_rad_per_v: float   # VCO gain [rad/s/V] (kept explicit so PVT corners can perturb it)

    @classmethod
    def build(cls, device: Device, icp_a: float, n: float, loop_filter: LoopFilter,
              kvco_rad_per_v: float | None = None) -> "PLLModel":
        """Convenience constructor defaulting Kvco to the device's datasheet value."""
        kv = kvco_rad_per_v if kvco_rad_per_v is not None else device.kvco_rad_per_v
        return cls(device=device, icp_a=icp_a, n=n, loop_filter=loop_filter,
                   kvco_rad_per_v=kv)

    @property
    def forward_gain(self) -> float:
        """The scalar loop gain constant  K = Icp*Kvco / (2*pi*N)  [1/(s*ohm)]."""
        return self.icp_a * self.kvco_rad_per_v / (TWO_PI * self.n)

    def open_loop(self) -> ct.TransferFunction:
        """Open-loop gain L(s) = (Icp*Kvco / 2*pi*N) * Z(s) / s."""
        vco_integrator = ct.tf([1.0], [1.0, 0.0])            # 1/s
        return self.forward_gain * self.loop_filter.impedance_tf() * vco_integrator

    def closed_loop(self) -> ct.TransferFunction:
        """Closed-loop phase transfer H(s) = L / (1 + L) (unity feedback)."""
        return ct.feedback(self.open_loop(), 1)

    def summary(self) -> dict:
        return {
            "device": self.device.name,
            "icp_ma": self.icp_a * 1e3,
            "n": self.n,
            "kvco_mhz_per_v": self.kvco_rad_per_v / (TWO_PI * 1e6),
            "loop_filter": self.loop_filter.summary(),
        }
