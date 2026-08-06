"""
ControlBench REST API.

Endpoints (all under /api):
    POST /api/analyze   -> characterise a plant (poles, zeros, stability, ...)
    POST /api/compare   -> design + rank all controllers, with step responses
    POST /api/predict   -> instant ML prediction of the recommended controller
    GET  /api/health    -> liveness + whether the ML model is loaded

Run locally:
    uvicorn api.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import control as ct
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from controlbench import __version__
from controlbench.analysis import PlantModel, InvalidPlantError
from controlbench.controllers import closed_loop
from controlbench.compare import compare_controllers
from controlbench.ml import load_models, predict as ml_predict

from .schemas import (
    PlantInput, CompareInput,
    PlantAnalysis, ComplexNumber, MetricsOut, StepSeries,
    ControllerResult, CompareResponse, PredictResponse,
)

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
STEP_SAMPLES = 300

app = FastAPI(
    title="ControlBench API",
    version=__version__,
    description="Compare, rank and predict classical controllers for a plant transfer function.",
)

# Allow the React (Vite) dev server to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the trained ML models once at startup (optional; /predict reports if missing).
try:
    _MODELS = load_models(MODELS_DIR)
except Exception:
    _MODELS = None


# ------------------------------------------------------------------ helpers

def _make_plant(inp: PlantInput) -> PlantModel:
    try:
        return PlantModel(inp.num, inp.den)
    except InvalidPlantError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _finite(x) -> float | None:
    """Map a float to JSON-safe form: non-finite (inf/nan) -> None."""
    x = float(x)
    return x if math.isfinite(x) else None


def _complex_list(arr) -> list[ComplexNumber]:
    return [ComplexNumber(re=float(z.real), im=float(z.imag)) for z in arr]


def _analysis(plant: PlantModel) -> PlantAnalysis:
    return PlantAnalysis(
        order=plant.order,
        poles=_complex_list(plant.poles),
        zeros=_complex_list(plant.zeros),
        stable=plant.is_stable,
        damping_ratio=float(plant.damping_ratio),
        natural_frequency=float(plant.natural_frequency),
    )


def _metrics_out(m) -> MetricsOut:
    return MetricsOut(
        rise_time=_finite(m.rise_time),
        settling_time=_finite(m.settling_time),
        overshoot=_finite(m.overshoot),
        steady_state_error=_finite(m.steady_state_error),
        gain_margin_db=_finite(m.gain_margin_db),
        phase_margin_deg=_finite(m.phase_margin_deg),
        stable=bool(m.stable),
    )


def _horizon(sys) -> float:
    """A step-response horizon long enough to show settling, from the slowest pole."""
    poles = ct.poles(sys)
    stable = poles[np.real(poles) < 0]
    if stable.size == 0:
        return 20.0
    slowest = float(np.min(np.abs(np.real(stable))))
    return float(np.clip(10.0 / slowest, 5.0, 1e4)) if slowest > 0 else 1000.0


def _step_series(plant: PlantModel, controllers, metrics) -> dict[str, StepSeries]:
    """Step responses for every controller's closed loop on a shared time axis."""
    loops = {name: closed_loop(plant, c) for name, c in controllers.items()}
    stable_horizons = [_horizon(loops[n]) for n, m in metrics.items() if m.stable]
    horizon = max(stable_horizons) if stable_horizons else 20.0
    tvec = np.linspace(0.0, horizon, STEP_SAMPLES)

    series: dict[str, StepSeries] = {}
    for name, loop in loops.items():
        try:
            t, y = ct.step_response(loop, T=tvec)
            y = np.asarray(y, float).ravel()
            # Clip diverging (unstable) responses so the payload stays finite/bounded.
            y = np.nan_to_num(np.clip(y, -1e6, 1e6), nan=0.0)
            series[name] = StepSeries(time=[float(v) for v in t],
                                      output=[float(v) for v in y])
        except Exception:
            series[name] = StepSeries(time=[], output=[])
    return series


# ------------------------------------------------------------------ routes

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "ml_model_loaded": _MODELS is not None}


@app.post("/api/analyze", response_model=PlantAnalysis)
def analyze(inp: PlantInput) -> PlantAnalysis:
    """Characterise a plant: poles, zeros, order, stability, damping, natural frequency."""
    return _analysis(_make_plant(inp))


@app.post("/api/compare", response_model=CompareResponse)
def compare(inp: CompareInput) -> CompareResponse:
    """Design all five controllers, rank them, and return metrics + step responses."""
    plant = _make_plant(inp)
    try:
        ranked, controllers, metrics = compare_controllers(plant, inp.weights)
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail=f"Comparison failed: {e}")

    series = _step_series(plant, controllers, metrics)
    results = [
        ControllerResult(
            name=r.name,
            method=controllers[r.name].method,
            params={k: float(v) for k, v in controllers[r.name].params.items()},
            score=float(r.score),
            metrics=_metrics_out(r.metrics),
            step_response=series[r.name],
        )
        for r in ranked
    ]
    return CompareResponse(plant=_analysis(plant), recommended=ranked[0].name, results=results)


@app.post("/api/predict", response_model=PredictResponse)
def predict(inp: PlantInput) -> PredictResponse:
    """Instant ML prediction of the recommended controller and its key metrics."""
    if _MODELS is None:
        raise HTTPException(
            status_code=503,
            detail="ML model not available. Build it with `python scripts/build_ml.py`.",
        )
    plant = _make_plant(inp)
    pred = ml_predict(plant, _MODELS)
    return PredictResponse(
        recommended_controller=pred["recommended_controller"],
        predicted_settling_time=float(pred["predicted_settling_time"]),
        predicted_overshoot=float(pred["predicted_overshoot"]),
        model_available=True,
    )
