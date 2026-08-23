"""
Generate the figures used in the README (and mirrored in the ML notebook).

    python scripts/make_figures.py     ->  docs/img/*.png

Every figure is produced from the LockBench engine on a real device, so the README
shows the tool's actual output, not a mock-up.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import control as ct

from controlbench.pll import (
    get_device, divider_for_output, design_pll, evaluate,
    CornerSpec, sweep_corners, phase_noise,
)
from controlbench.pll import ml

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

NAVY, BLUE, ACCENT, GOOD, BAD = "#0f2a43", "#1f6feb", "#e8873b", "#1a9e6a", "#d64545"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c8d3e0",
                     "axes.grid": True, "grid.color": "#e6edf5", "figure.dpi": 130})


def _adf4351_design():
    dev = get_device("adf4351")
    n = divider_for_output(dev, f_out_hz=2.4e9, f_pfd_hz=10e6)
    pll = design_pll(dev, n=n, fc_hz=20e3, phase_margin_deg=50.0)
    return dev, n, pll


def fig_bode():
    _dev, _n, pll = _adf4351_design()
    m = evaluate(pll)
    f = np.logspace(1, 7, 800)
    w = 2 * np.pi * f
    L = np.asarray(ct.frequency_response(pll.open_loop(), w).frdata).ravel()
    mag = 20 * np.log10(np.abs(L))
    ph = np.degrees(np.unwrap(np.angle(L)))

    fig, ax1 = plt.subplots(figsize=(7, 3.6))
    ax1.semilogx(f, mag, color=BLUE, lw=2, label="|L| (dB)")
    ax1.axhline(0, color="#8090a4", ls=":", lw=1)
    ax1.axvline(m.loop_bandwidth_hz, color="#5a6b80", ls="--", lw=1)
    ax1.set_xlabel("frequency (Hz)"); ax1.set_ylabel("|L| (dB)", color=BLUE)
    ax2 = ax1.twinx(); ax2.grid(False)
    ax2.semilogx(f, ph, color=ACCENT, lw=2, label="∠L (°)")
    ax2.set_ylabel("∠L (°)", color=ACCENT)
    ax1.set_title(f"ADF4351 open-loop Bode — f_c ≈ {m.loop_bandwidth_hz/1e3:.0f} kHz, "
                  f"PM = {m.phase_margin_deg:.0f}°", color=NAVY)
    fig.tight_layout(); fig.savefig(IMG / "bode.png"); plt.close(fig)


def fig_pvt():
    _dev, _n, pll = _adf4351_design()
    results = sweep_corners(pll, CornerSpec(kvco_tol=0.30, icp_tol=0.10))
    names = [r.corner.name.replace(", ", "\n") for r in results]
    pms = [r.metrics.phase_margin_deg for r in results]
    locks = [r.metrics.lock_time_s * 1e6 for r in results]
    colors = [GOOD if p >= 45 else BAD for p in pms]

    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 3.4))
    a.bar(range(len(pms)), pms, color=colors)
    a.axhline(45, color=BAD, ls="--", lw=1, label="spec: PM ≥ 45°")
    a.set_xticks(range(len(names))); a.set_xticklabels(names, fontsize=7)
    a.set_ylabel("phase margin (°)"); a.set_ylim(0, max(pms) + 8); a.legend(fontsize=8)
    a.set_title("Phase margin across PVT", color=NAVY)
    b.bar(range(len(locks)), locks, color=BLUE)
    b.set_xticks(range(len(names))); b.set_xticklabels(names, fontsize=7)
    b.set_ylabel("lock time (µs)")
    b.set_title("Lock time across PVT", color=NAVY)
    fig.tight_layout(); fig.savefig(IMG / "pvt_corners.png"); plt.close(fig)


def fig_phase_noise():
    dev, _n, pll = _adf4351_design()
    pn = phase_noise(pll, 2.4e9, 10e6)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.semilogx(pn.offset_hz, pn.inband_dbc, color=BLUE, lw=1.2, ls=":", label="PLL / ref")
    ax.semilogx(pn.offset_hz, pn.vco_dbc, color=ACCENT, lw=1.2, ls=":", label="VCO")
    ax.semilogx(pn.offset_hz, pn.total_dbc, color="#0b8fa8", lw=2.4, label="total")
    ax.set_xlabel("offset frequency (Hz)"); ax.set_ylabel("ℒ(f) (dBc/Hz)")
    ax.set_ylim(-160, -60); ax.legend(fontsize=8)
    ax.set_title(f"ADF4351 phase noise — {pn.rms_jitter_s*1e12:.1f} ps RMS jitter "
                 f"(12 kHz–20 MHz)", color=NAVY)
    fig.tight_layout(); fig.savefig(IMG / "phase_noise.png"); plt.close(fig)


def fig_ml_parity():
    """ML surrogate predictions vs the physics model, on a held-out sample."""
    X, Y = ml.make_dataset(n_samples=250, seed=7)         # fresh, unseen data
    bundle = ml.load_surrogate(ROOT / "models" / "pll_surrogate.joblib")
    P = bundle["model"].predict(X)

    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 3.6))
    a.scatter(Y[:, 0], P[:, 0], s=10, alpha=0.5, color=BLUE)
    lo, hi = Y[:, 0].min(), Y[:, 0].max()
    a.plot([lo, hi], [lo, hi], color=BAD, lw=1)
    a.set_xlabel("model worst PM (°)"); a.set_ylabel("ML predicted (°)")
    a.set_title("Worst-case phase margin", color=NAVY)
    b.scatter(Y[:, 1], P[:, 1], s=10, alpha=0.5, color=GOOD)
    lo, hi = Y[:, 1].min(), Y[:, 1].max()
    b.plot([lo, hi], [lo, hi], color=BAD, lw=1)
    b.set_xlabel("model log₁₀ lock time"); b.set_ylabel("ML predicted")
    b.set_title("Worst-case lock time", color=NAVY)
    fig.suptitle("ML surrogate vs physics model (held-out)", color=NAVY, y=1.02)
    fig.tight_layout(); fig.savefig(IMG / "ml_parity.png", bbox_inches="tight"); plt.close(fig)


def main():
    print("Rendering figures to docs/img/ ...")
    fig_bode();         print("  bode.png")
    fig_pvt();          print("  pvt_corners.png")
    fig_phase_noise();  print("  phase_noise.png")
    fig_ml_parity();    print("  ml_parity.png")
    print("done.")


if __name__ == "__main__":
    main()
