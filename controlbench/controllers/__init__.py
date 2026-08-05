"""Classical controller designs and closed-loop helpers."""

from .base import Controller, open_loop, closed_loop
from .classical import (
    design_p,
    design_pi,
    design_pid,
    design_lead,
    design_lag,
    design_all,
)

__all__ = [
    "Controller",
    "open_loop",
    "closed_loop",
    "design_p",
    "design_pi",
    "design_pid",
    "design_lead",
    "design_lag",
    "design_all",
]
