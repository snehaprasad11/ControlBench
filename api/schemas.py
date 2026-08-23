"""Pydantic request/response models for the LockBench PLL API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ inputs

class CornerSpecIn(BaseModel):
    kvco_tol: float = Field(0.30, ge=0, le=0.9, description="Fractional Kvco variation (0.30 = +/-30%)")
    icp_tol: float = Field(0.10, ge=0, le=0.9, description="Fractional Icp variation")
    comp_tol: float = Field(0.0, ge=0, le=0.5, description="Fractional R/C component tolerance")


class SpecIn(BaseModel):
    min_phase_margin_deg: float = Field(45.0, gt=0, lt=90)
    max_lock_time_us: float | None = Field(None, gt=0)
    max_jitter_peaking_db: float | None = Field(None, ge=0)
    min_bandwidth_khz: float | None = Field(None, gt=0)
    max_bandwidth_khz: float | None = Field(None, gt=0)


class DesignInput(BaseModel):
    device_id: str
    f_out_hz: float = Field(..., gt=0, description="Desired VCO/output frequency (Hz)")
    f_pfd_hz: float = Field(..., gt=0, description="Phase-detector (reference compare) frequency (Hz)")
    fc_hz: float = Field(..., gt=0, description="Target loop bandwidth (Hz)")
    phase_margin_deg: float = Field(50.0, gt=0, lt=90)
    icp_ma: float | None = Field(None, gt=0, description="Charge-pump current (mA); default = device default")
    corner: CornerSpecIn = CornerSpecIn()
    spec: SpecIn = SpecIn()


class ExploreInput(BaseModel):
    device_id: str
    f_out_hz: float = Field(..., gt=0)
    f_pfd_hz: float = Field(..., gt=0)
    corner: CornerSpecIn = CornerSpecIn()
    spec: SpecIn = SpecIn()


class RecommendInput(BaseModel):
    device_id: str
    f_out_hz: float = Field(..., gt=0)
    f_pfd_hz: float = Field(..., gt=0)
    spec: SpecIn = SpecIn()


# ------------------------------------------------------------------ outputs

class DeviceOut(BaseModel):
    id: str
    name: str
    vendor: str
    category: str
    vco_min_hz: float
    vco_max_hz: float
    rf_out_min_hz: float
    rf_out_max_hz: float
    kvco_mhz_per_v: float
    icp_options_ma: list[float]
    icp_default_ma: float
    pfd_max_hz: float
    n_min: int
    n_max: int
    datasheet: str
    source_notes: str


class LoopFilterOut(BaseModel):
    order: int
    r_ohm: float
    c_main_nf: float
    c_shunt_nf: float
    zero_hz: float
    pole3_hz: float | None


class MetricsOut(BaseModel):
    loop_bandwidth_hz: float | None
    phase_margin_deg: float | None
    gain_margin_db: float | None
    lock_time_s: float | None
    jitter_peaking_db: float | None
    stable: bool


class CornerMetricsOut(BaseModel):
    name: str
    is_nominal: bool
    kvco_mult: float
    icp_mult: float
    metrics: MetricsOut


class WorstCaseOut(BaseModel):
    all_stable: bool
    min_phase_margin_deg: float | None
    min_gain_margin_db: float | None
    max_lock_time_s: float | None
    max_jitter_peaking_db: float | None
    min_bandwidth_hz: float | None
    max_bandwidth_hz: float | None


class Series(BaseModel):
    x: list[float]
    y: list[float]


class BodeOut(BaseModel):
    freq_hz: list[float]
    open_mag_db: list[float]
    open_phase_deg: list[float]
    closed_mag_db: list[float]


class PhaseNoiseOut(BaseModel):
    offset_hz: list[float]
    total_dbc: list[float]
    inband_dbc: list[float]
    vco_dbc: list[float]
    rms_jitter_s: float
    jitter_band_hz: list[float]
    reference_spur_dbc: float


class DesignResponse(BaseModel):
    device: DeviceOut
    n: float
    icp_ma: float
    kvco_mhz_per_v: float
    loop_filter: LoopFilterOut
    nominal: MetricsOut
    worst: WorstCaseOut
    passes: bool
    violations: list[str]
    corners: list[CornerMetricsOut]
    step_response: Series          # phase-step lock transient (normalised)
    bode: BodeOut
    phase_noise: PhaseNoiseOut


class CandidateOut(BaseModel):
    fc_hz: float
    phase_margin_deg: float
    icp_ma: float
    passes: bool
    robustness_margin_deg: float
    worst: WorstCaseOut


class ExploreResponse(BaseModel):
    device: DeviceOut
    n: float
    any_pass: bool
    candidates: list[CandidateOut]


class RecommendResponse(BaseModel):
    model_available: bool
    device: DeviceOut
    n: float
    recommended_fc_hz: float | None = None
    recommended_phase_margin_deg: float | None = None
    recommended_icp_ma: float | None = None
    predicted_worst_phase_margin_deg: float | None = None
    predicted_worst_lock_time_s: float | None = None
    predicted_worst_jitter_peaking_db: float | None = None
    note: str = ""
