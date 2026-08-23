"""
The real-device library.

LockBench is anchored on *real* commercial charge-pump PLL / synthesizer ICs. Their
datasheet parameters live in ``data/pll_devices.json`` (each field cited to the
manufacturer datasheet). This module loads that file into typed ``Device`` records
and is the single source of truth the rest of the engine designs against.

Nothing here invents data: a ``Device`` is just a validated view onto the JSON, so
that a design or a prediction can always be traced back to a published spec.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# data/pll_devices.json lives at the repo root, two parents up from this file.
_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "pll_devices.json"

# Two-pi, and Hz -> rad/s helper for VCO gain conversions.
TWO_PI = 6.283185307179586


@dataclass(frozen=True)
class Device:
    """One real PLL IC, as published on its datasheet.

    Frequencies are in Hz, currents in Amps, ``kvco`` in Hz/V. The charge-pump
    gain the loop actually sees is ``Icp / (2*pi)`` [A/rad]; the VCO gain the loop
    sees is ``2*pi*kvco`` [rad/s/V]. Those conversions are done in :mod:`.model`,
    so this record stays in the datasheet's own units.
    """

    id: str
    name: str
    vendor: str
    category: str
    vco_min_hz: float
    vco_max_hz: float
    rf_out_min_hz: float
    rf_out_max_hz: float
    kvco_hz_per_v: float            # datasheet Kvco, converted MHz/V -> Hz/V on load
    icp_options_a: tuple[float, ...]  # selectable charge-pump currents, Amps
    icp_default_a: float
    pfd_max_hz: float
    n_min: int
    n_max: int
    datasheet: str
    source_notes: str

    @property
    def kvco_rad_per_v(self) -> float:
        """VCO gain in rad/s per volt (what the loop transfer function uses)."""
        return TWO_PI * self.kvco_hz_per_v

    def summary(self) -> dict:
        """A JSON-friendly snapshot for the API / UI (units the user reads)."""
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "category": self.category,
            "vco_min_hz": self.vco_min_hz,
            "vco_max_hz": self.vco_max_hz,
            "rf_out_min_hz": self.rf_out_min_hz,
            "rf_out_max_hz": self.rf_out_max_hz,
            "kvco_mhz_per_v": self.kvco_hz_per_v / 1e6,
            "icp_options_ma": [i * 1e3 for i in self.icp_options_a],
            "icp_default_ma": self.icp_default_a * 1e3,
            "pfd_max_hz": self.pfd_max_hz,
            "n_min": self.n_min,
            "n_max": self.n_max,
            "datasheet": self.datasheet,
            "source_notes": self.source_notes,
        }


def _from_json(d: dict) -> Device:
    return Device(
        id=d["id"],
        name=d["name"],
        vendor=d["vendor"],
        category=d["category"],
        vco_min_hz=float(d["vco_min_hz"]),
        vco_max_hz=float(d["vco_max_hz"]),
        rf_out_min_hz=float(d["rf_out_min_hz"]),
        rf_out_max_hz=float(d["rf_out_max_hz"]),
        kvco_hz_per_v=float(d["kvco_mhz_per_v"]) * 1e6,
        icp_options_a=tuple(float(i) * 1e-3 for i in d["icp_options_ma"]),
        icp_default_a=float(d["icp_default_ma"]) * 1e-3,
        pfd_max_hz=float(d["pfd_max_hz"]),
        n_min=int(d["n_min"]),
        n_max=int(d["n_max"]),
        datasheet=d["datasheet"],
        source_notes=d["source_notes"],
    )


@lru_cache(maxsize=1)
def load_devices(path: Path | None = None) -> tuple[Device, ...]:
    """Load and cache the real-device library from ``data/pll_devices.json``."""
    p = path or _DATA_FILE
    raw = json.loads(Path(p).read_text(encoding="utf-8"))
    return tuple(_from_json(d) for d in raw["devices"])


def get_device(device_id: str) -> Device:
    """Look up one device by its id (e.g. ``"adf4351"``)."""
    for dev in load_devices():
        if dev.id == device_id:
            return dev
    known = ", ".join(d.id for d in load_devices())
    raise KeyError(f"Unknown device id {device_id!r}. Known devices: {known}.")
