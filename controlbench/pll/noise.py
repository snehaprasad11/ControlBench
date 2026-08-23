"""
Phase noise, integrated jitter and reference spurs — the headline specs on a real PLL
datasheet.

The loop dynamics (bandwidth, margin, lock, peaking) live in :mod:`.metrics`; this module
adds the *noise* view, which is what a synthesizer datasheet actually leads with. It is a
standard first-order model (the one behind ADIsimPLL / TI PLLatinum's noise tab):

  * **In-band noise** (offsets below the loop bandwidth) is set by the PLL/reference and
    scales with the divide ratio; it is low-pass shaped by the closed loop |H(jf)|^2.
  * **VCO noise** (offsets above the loop bandwidth) rolls off at -20 dB/decade and is
    high-pass shaped by |1 - H(jf)|^2 (the loop suppresses it inside the bandwidth).

The total is their sum; integrating it over an offset band gives the **RMS jitter**.

This is an estimate, not a substitute for measured phase noise: the VCO term uses a
representative -110 dBc/Hz-at-1 MHz profile scaled with carrier frequency, and the in-band
term is anchored to each device's datasheet figure. See the README "Limitations & scope".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import control as ct

from .devices import Device
from .model import PLLModel

# Default offset grid (Hz) and the classic 12 kHz - 20 MHz jitter integration band.
_F_LO, _F_HI = 1e2, 1e8
_JITTER_LO, _JITTER_HI = 12e3, 20e6


@dataclass
class PhaseNoise:
    offset_hz: list[float]
    total_dbc: list[float]        # total output phase noise L(f) [dBc/Hz]
    inband_dbc: list[float]       # PLL/reference contribution (loop-shaped)
    vco_dbc: list[float]          # VCO contribution (loop-shaped)
    rms_jitter_s: float           # integrated over the jitter band
    jitter_band_hz: tuple[float, float]


def _inband_floor_dbc(device: Device, n: float, f_pfd_hz: float, f_out_hz: float) -> float:
    """In-band phase-noise floor referred to the output (flat below the loop bandwidth)."""
    if device.phase_noise_offset_hz is None:
        # The datasheet figure is a normalized 1-Hz noise floor (FOM):
        #   floor = FOM + 10log10(f_pfd) + 20log10(N)
        return device.phase_noise_dbc_hz + 10 * np.log10(f_pfd_hz) + 20 * np.log10(n)
    # The datasheet figure is a measured in-band point at some carrier; scale to this
    # carrier at 20 dB/decade (phase noise adds 20log10 with frequency multiplication).
    return device.phase_noise_dbc_hz + 20 * np.log10(f_out_hz / device.phase_noise_ref_out_hz)


def _vco_noise_dbc(f: np.ndarray, f_out_hz: float) -> np.ndarray:
    """Representative free-running VCO phase noise: -120 dBc/Hz at 1 MHz offset for a
    1 GHz carrier (a typical integrated VCO), scaling 20 dB/decade with carrier and
    -20 dB/decade with offset."""
    pn_1mhz = -120.0 + 20.0 * np.log10(f_out_hz / 1e9)
    return pn_1mhz + 20.0 * np.log10(1e6 / f)


def phase_noise(pll: PLLModel, f_out_hz: float, f_pfd_hz: float,
                n_points: int = 240) -> PhaseNoise:
    """Model the output phase-noise profile and integrate it to an RMS jitter."""
    f = np.logspace(np.log10(_F_LO), np.log10(_F_HI), n_points)
    w = 2.0 * np.pi * f

    H = np.asarray(ct.frequency_response(pll.closed_loop(), w).frdata).ravel()
    H2 = np.abs(H) ** 2                 # closed-loop (low-pass) shaping for PLL/ref noise
    E2 = np.abs(1.0 - H) ** 2           # error (high-pass) shaping for VCO noise

    floor_lin = 10.0 ** (_inband_floor_dbc(pll.device, pll.n, f_pfd_hz, f_out_hz) / 10.0)
    vco_lin = 10.0 ** (_vco_noise_dbc(f, f_out_hz) / 10.0)

    s_inband = floor_lin * H2
    s_vco = vco_lin * E2
    s_total = s_inband + s_vco

    total_db = 10.0 * np.log10(s_total)
    inband_db = 10.0 * np.log10(np.maximum(s_inband, 1e-30))
    vco_db = 10.0 * np.log10(np.maximum(s_vco, 1e-30))

    rms = _integrated_jitter_s(f, s_total, f_out_hz, _JITTER_LO, _JITTER_HI)
    return PhaseNoise(
        offset_hz=[float(v) for v in f],
        total_dbc=[float(v) for v in total_db],
        inband_dbc=[float(v) for v in inband_db],
        vco_dbc=[float(v) for v in vco_db],
        rms_jitter_s=float(rms),
        jitter_band_hz=(_JITTER_LO, _JITTER_HI),
    )


def _integrated_jitter_s(f: np.ndarray, s_ssb: np.ndarray, f_out_hz: float,
                         f_lo: float, f_hi: float) -> float:
    """RMS jitter (seconds) from single-sideband phase noise over [f_lo, f_hi].

    phase variance = 2 * integral(L(f) df); jitter = sqrt(variance) / (2*pi*f_out).
    """
    m = (f >= f_lo) & (f <= f_hi)
    if np.count_nonzero(m) < 2:
        return 0.0
    phase_var_rad2 = 2.0 * np.trapezoid(s_ssb[m], f[m])
    return float(np.sqrt(max(phase_var_rad2, 0.0)) / (2.0 * np.pi * f_out_hz))


def reference_spur_dbc(pll: PLLModel, f_pfd_hz: float, base_leakage_dbc: float = -40.0) -> float:
    """First-order reference-spur estimate (dBc) at the comparison frequency.

    Ripple on the tune line at f_pfd creates a spur; the loop filter attenuates it beyond
    the loop bandwidth. We take a representative charge-pump leakage floor and add the
    closed-loop attenuation at f_pfd. This is an order-of-magnitude estimate, not a
    substitute for a spur measurement.
    """
    w = np.array([2.0 * np.pi * f_pfd_hz])
    H = np.asarray(ct.frequency_response(pll.closed_loop(), w).frdata).ravel()[0]
    atten_db = 20.0 * np.log10(max(abs(H), 1e-12))
    return float(base_leakage_dbc + atten_db)
