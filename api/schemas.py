"""Request/response models for the ControlBench API (pydantic v2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --------------------------------------------------------------- requests

class PlantInput(BaseModel):
    """A plant transfer function as numerator/denominator coefficients (descending)."""
    num: list[float] = Field(..., examples=[[1.0]])
    den: list[float] = Field(..., examples=[[1.0, 3.0, 3.0, 1.0]])


class CompareInput(PlantInput):
    """A plant plus optional custom ranking weights."""
    weights: dict[str, float] | None = Field(
        default=None,
        description="Optional metric weights, e.g. {'overshoot': 0.5, 'settling_time': 0.5}.",
    )


# --------------------------------------------------------------- responses

class ComplexNumber(BaseModel):
    re: float
    im: float


class PlantAnalysis(BaseModel):
    order: int
    poles: list[ComplexNumber]
    zeros: list[ComplexNumber]
    stable: bool
    damping_ratio: float
    natural_frequency: float


class MetricsOut(BaseModel):
    # Non-finite values (e.g. an infinite gain margin, or an unstable design's
    # settling time) are serialised as null.
    rise_time: float | None
    settling_time: float | None
    overshoot: float | None
    steady_state_error: float | None
    gain_margin_db: float | None
    phase_margin_deg: float | None
    stable: bool


class StepSeries(BaseModel):
    time: list[float]
    output: list[float]


class ControllerResult(BaseModel):
    name: str
    method: str
    params: dict[str, float]
    score: float
    metrics: MetricsOut
    step_response: StepSeries


class CompareResponse(BaseModel):
    plant: PlantAnalysis
    recommended: str
    results: list[ControllerResult]


class PredictResponse(BaseModel):
    recommended_controller: str
    predicted_settling_time: float
    predicted_overshoot: float
    model_available: bool = True
