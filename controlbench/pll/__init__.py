"""
LockBench PLL engine.

Charge-pump PLL loop design and analysis on top of the ControlBench LTI core:

    devices  -> real commercial PLL ICs (datasheet-anchored)
    model    -> PLLModel / LoopFilter: build open-loop L(s) and closed-loop H(s)
    design   -> synthesise a loop filter for a target bandwidth + phase margin
    metrics  -> loop bandwidth, phase/gain margin, lock time, jitter peaking
"""

from .devices import Device, load_devices, get_device
from .model import LoopFilter, PLLModel
from .design import design_loop_filter, design_pll, divider_for_output
from .metrics import PLLMetrics, evaluate

__all__ = [
    "Device", "load_devices", "get_device",
    "LoopFilter", "PLLModel",
    "design_loop_filter", "design_pll", "divider_for_output",
    "PLLMetrics", "evaluate",
]
