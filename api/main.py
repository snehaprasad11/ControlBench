"""
LockBench REST API.

Charge-pump PLL loop-filter design, PVT-robustness analysis and ML inverse design,
anchored on a library of real synthesizer ICs.

Endpoints (all under /api):
    GET  /api/health     -> liveness + whether the ML surrogate is loaded
    GET  /api/devices    -> the real device library (datasheet-anchored)
    POST /api/design     -> design a loop filter; return filter, metrics, PVT sweep, plots
    POST /api/explore    -> search the design space for PVT-robust designs, ranked
    POST /api/recommend  -> ML inverse design: suggest a design point from target specs

Run locally:
    uvicorn api.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import control as ct
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from controlbench import __version__
from controlbench.pll import (
    load_devices, get_device, Device,
    design_pll, divider_for_output, evaluate,
    PLLModel, PLLMetrics,
    CornerSpec, PLLSpec, robust_evaluate, explore_robust_design,
    phase_noise, reference_spur_dbc,
)
from controlbench.pll import ml

from .schemas import (
    DesignInput, ExploreInput, RecommendInput,
    DeviceOut, LoopFilterOut, MetricsOut, CornerMetricsOut, WorstCaseOut,
    Series, BodeOut, PhaseNoiseOut, DesignResponse, CandidateOut, ExploreResponse, RecommendResponse,
)

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "pll_surrogate.joblib"
STEP_SAMPLES = 240
BODE_SAMPLES = 400

app = FastAPI(
    title="LockBench API",
    version=__version__,
    description="Design, PVT-robustness-check and ML-recommend charge-pump PLL loop "
                "filters for real synthesizer ICs.",
)

_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the ML surrogate once at startup (optional; /recommend reports if missing).
try:
    _SURROGATE = ml.load_surrogate(MODEL_PATH)
except Exception:
    _SURROGATE = None


# ------------------------------------------------------------------ helpers

def _finite(x) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _device(device_id: str) -> Device:
    try:
        return get_device(device_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _device_out(dev: Device) -> DeviceOut:
    return DeviceOut(**dev.summary())


def _make_n(dev: Device, f_out_hz: float, f_pfd_hz: float) -> float:
    if f_pfd_hz > dev.pfd_max_hz:
        raise HTTPException(
            status_code=400,
            detail=f"f_pfd {f_pfd_hz/1e6:.3g} MHz exceeds {dev.name} max PFD "
                   f"{dev.pfd_max_hz/1e6:.3g} MHz.")
    if not (dev.vco_min_hz <= f_out_hz <= dev.vco_max_hz):
        raise HTTPException(
            status_code=400,
            detail=f"Output {f_out_hz/1e9:.4g} GHz is outside {dev.name} VCO range "
                   f"{dev.vco_min_hz/1e9:.3g}-{dev.vco_max_hz/1e9:.3g} GHz.")
    n = divider_for_output(dev, f_out_hz, f_pfd_hz)
    if not (dev.n_min <= n <= dev.n_max):
        raise HTTPException(
            status_code=400,
            detail=f"Implied divider N={n:.1f} is outside {dev.name} range "
                   f"{dev.n_min}-{dev.n_max}. Adjust f_out or f_pfd.")
    return n


def _corner(inp) -> CornerSpec:
    return CornerSpec(kvco_tol=inp.kvco_tol, icp_tol=inp.icp_tol, comp_tol=inp.comp_tol)


def _spec(inp) -> PLLSpec:
    return PLLSpec(
        min_phase_margin_deg=inp.min_phase_margin_deg,
        max_lock_time_s=(inp.max_lock_time_us * 1e-6) if inp.max_lock_time_us else None,
        max_jitter_peaking_db=inp.max_jitter_peaking_db,
        min_bandwidth_hz=(inp.min_bandwidth_khz * 1e3) if inp.min_bandwidth_khz else None,
        max_bandwidth_hz=(inp.max_bandwidth_khz * 1e3) if inp.max_bandwidth_khz else None,
    )


def _metrics_out(m: PLLMetrics) -> MetricsOut:
    return MetricsOut(
        loop_bandwidth_hz=_finite(m.loop_bandwidth_hz),
        phase_margin_deg=_finite(m.phase_margin_deg),
        gain_margin_db=_finite(m.gain_margin_db),
        lock_time_s=_finite(m.lock_time_s),
        jitter_peaking_db=_finite(m.jitter_peaking_db),
        stable=bool(m.stable),
    )


def _worst_out(w: dict) -> WorstCaseOut:
    return WorstCaseOut(
        all_stable=bool(w["all_stable"]),
        min_phase_margin_deg=_finite(w["min_phase_margin_deg"]),
        min_gain_margin_db=_finite(w["min_gain_margin_db"]),
        max_lock_time_s=_finite(w["max_lock_time_s"]),
        max_jitter_peaking_db=_finite(w["max_jitter_peaking_db"]),
        min_bandwidth_hz=_finite(w["min_bandwidth_hz"]),
        max_bandwidth_hz=_finite(w["max_bandwidth_hz"]),
    )


def _loop_filter_out(pll: PLLModel) -> LoopFilterOut:
    lf = pll.loop_filter
    return LoopFilterOut(
        order=lf.order,
        r_ohm=lf.r,
        c_main_nf=lf.c_main * 1e9,
        c_shunt_nf=lf.c_shunt * 1e9,
        zero_hz=lf.zero_hz,
        pole3_hz=_finite(lf.pole3_hz),
    )


def _bode(pll: PLLModel, fc_hint_hz: float) -> BodeOut:
    """Open-loop Bode (magnitude + phase) and closed-loop magnitude vs frequency."""
    f = np.logspace(np.log10(max(fc_hint_hz / 500.0, 1.0)),
                    np.log10(fc_hint_hz * 500.0), BODE_SAMPLES)
    w = 2.0 * np.pi * f
    L = np.asarray(ct.frequency_response(pll.open_loop(), w).frdata).ravel()
    H = np.asarray(ct.frequency_response(pll.closed_loop(), w).frdata).ravel()
    open_mag_db = 20.0 * np.log10(np.abs(L))
    open_phase_deg = np.degrees(np.unwrap(np.angle(L)))
    closed_mag_db = 20.0 * np.log10(np.abs(H))
    return BodeOut(
        freq_hz=[float(v) for v in f],
        open_mag_db=[float(v) for v in open_mag_db],
        open_phase_deg=[float(v) for v in open_phase_deg],
        closed_mag_db=[float(v) for v in closed_mag_db],
    )


def _phase_noise(pll: PLLModel, f_out_hz: float, f_pfd_hz: float) -> PhaseNoiseOut:
    """Phase-noise profile, integrated RMS jitter, and a reference-spur estimate."""
    pn = phase_noise(pll, f_out_hz, f_pfd_hz)
    spur = reference_spur_dbc(pll, f_pfd_hz)
    return PhaseNoiseOut(
        offset_hz=pn.offset_hz,
        total_dbc=pn.total_dbc,
        inband_dbc=pn.inband_dbc,
        vco_dbc=pn.vco_dbc,
        rms_jitter_s=pn.rms_jitter_s,
        jitter_band_hz=list(pn.jitter_band_hz),
        reference_spur_dbc=spur,
    )


def _step(pll: PLLModel, lock_time_s: float | None) -> Series:
    """Normalised phase-step (lock) transient of the closed loop."""
    H = pll.closed_loop()
    if lock_time_s and math.isfinite(lock_time_s) and lock_time_s > 0:
        horizon = lock_time_s * 2.0
    else:
        horizon = 1e-4
    tvec = np.linspace(0.0, horizon, STEP_SAMPLES)
    try:
        t, y = ct.step_response(H, T=tvec)
        y = np.asarray(y, float).ravel()
        yf = complex(ct.dcgain(H)).real
        if np.isfinite(yf) and abs(yf) > 1e-12:
            y = y / yf
        y = np.nan_to_num(np.clip(y, -5.0, 5.0))
        return Series(x=[float(v) for v in t], y=[float(v) for v in y])
    except Exception:
        return Series(x=[], y=[])


# ------------------------------------------------------------------ routes

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "ml_model_loaded": _SURROGATE is not None}


@app.get("/api/devices", response_model=list[DeviceOut])
def devices() -> list[DeviceOut]:
    """The real, datasheet-anchored device library."""
    return [_device_out(d) for d in load_devices()]


@app.post("/api/design", response_model=DesignResponse)
def design(inp: DesignInput) -> DesignResponse:
    """Design a loop filter for a device + targets, then sweep it across PVT."""
    dev = _device(inp.device_id)
    n = _make_n(dev, inp.f_out_hz, inp.f_pfd_hz)
    icp_a = inp.icp_ma * 1e-3 if inp.icp_ma else None
    try:
        pll = design_pll(dev, n=n, fc_hz=inp.fc_hz,
                         phase_margin_deg=inp.phase_margin_deg, icp_a=icp_a)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Design failed: {e}")

    report = robust_evaluate(pll, _spec(inp.spec), _corner(inp.corner))
    corners = [
        CornerMetricsOut(
            name=cr.corner.name,
            is_nominal=cr.corner.is_nominal,
            kvco_mult=cr.corner.kvco_mult,
            icp_mult=cr.corner.icp_mult,
            metrics=_metrics_out(cr.metrics),
        )
        for cr in report.corners
    ]
    return DesignResponse(
        device=_device_out(dev),
        n=n,
        icp_ma=pll.icp_a * 1e3,
        kvco_mhz_per_v=pll.kvco_rad_per_v / (2 * np.pi * 1e6),
        loop_filter=_loop_filter_out(pll),
        nominal=_metrics_out(report.nominal),
        worst=_worst_out(report.worst),
        passes=report.passes,
        violations=report.violations,
        corners=corners,
        step_response=_step(pll, report.nominal.lock_time_s),
        bode=_bode(pll, inp.fc_hz),
        phase_noise=_phase_noise(pll, inp.f_out_hz, inp.f_pfd_hz),
    )


@app.post("/api/explore", response_model=ExploreResponse)
def explore(inp: ExploreInput) -> ExploreResponse:
    """Search (bandwidth, phase margin, Icp) for PVT-robust designs, ranked best-first."""
    dev = _device(inp.device_id)
    n = _make_n(dev, inp.f_out_hz, inp.f_pfd_hz)
    cands = explore_robust_design(dev, n=n, spec=_spec(inp.spec),
                                  corner_spec=_corner(inp.corner), f_pfd_hz=inp.f_pfd_hz)
    out = [
        CandidateOut(
            fc_hz=c.fc_hz,
            phase_margin_deg=c.phase_margin_deg,
            icp_ma=c.icp_a * 1e3,
            passes=c.report.passes,
            robustness_margin_deg=c.robustness_margin_deg,
            worst=_worst_out(c.report.worst),
        )
        for c in cands[:8]
    ]
    return ExploreResponse(device=_device_out(dev), n=n,
                           any_pass=any(c.passes for c in out), candidates=out)


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(inp: RecommendInput) -> RecommendResponse:
    """ML inverse design: instantly suggest a design point from target specs."""
    dev = _device(inp.device_id)
    n = _make_n(dev, inp.f_out_hz, inp.f_pfd_hz)
    if _SURROGATE is None:
        return RecommendResponse(
            model_available=False, device=_device_out(dev), n=n,
            note="ML surrogate not built. Run `python scripts/build_pll_ml.py`.")

    rec = ml.recommend_design(_SURROGATE, dev, n, _spec(inp.spec), inp.f_pfd_hz)
    if rec is None:
        return RecommendResponse(
            model_available=True, device=_device_out(dev), n=n,
            note="No design in the search grid is predicted to meet these specs. "
                 "Relax the phase-margin / peaking / lock-time targets.")
    return RecommendResponse(
        model_available=True, device=_device_out(dev), n=n,
        recommended_fc_hz=rec.fc_hz,
        recommended_phase_margin_deg=rec.phase_margin_deg,
        recommended_icp_ma=rec.icp_a * 1e3,
        predicted_worst_phase_margin_deg=rec.predicted["worst_phase_margin_deg"],
        predicted_worst_lock_time_s=rec.predicted["worst_lock_time_s"],
        predicted_worst_jitter_peaking_db=rec.predicted["worst_jitter_peaking_db"],
        note="Predicted from the ML surrogate; press Design to verify against the model.",
    )


# ------------------------------------------------------------------ frontend
# Serve the built React app from the same origin as the API, so the whole thing
# is one deployable service at one URL. The API routes above are matched first;
# this catch-all mount serves index.html and the static assets for everything else.
# (Only mounted when a build exists — e.g. in the Docker image or after `npm run build`.)
_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
