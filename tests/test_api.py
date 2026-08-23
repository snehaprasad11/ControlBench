"""Tests for the LockBench FastAPI backend."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# A realistic ADF4351 job: 2.4 GHz VCO, 10 MHz phase-detector frequency.
DESIGN = {
    "device_id": "adf4351",
    "f_out_hz": 2.4e9,
    "f_pfd_hz": 10e6,
    "fc_hz": 20e3,
    "phase_margin_deg": 50.0,
    "corner": {"kvco_tol": 0.30, "icp_tol": 0.10},
    "spec": {"min_phase_margin_deg": 45.0},
}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_devices_lists_real_parts():
    r = client.get("/api/devices")
    assert r.status_code == 200
    ids = {d["id"] for d in r.json()}
    assert {"adf4351", "lmx2594", "adf5355"} <= ids
    adf = next(d for d in r.json() if d["id"] == "adf4351")
    assert adf["vendor"] == "Analog Devices"
    assert adf["datasheet"].startswith("http")


def test_design_returns_filter_metrics_and_plots():
    r = client.post("/api/design", json=DESIGN)
    assert r.status_code == 200
    body = r.json()
    # loop filter component values are present and positive
    lf = body["loop_filter"]
    assert lf["r_ohm"] > 0 and lf["c_main_nf"] > 0
    # designed to 20 kHz / 50 deg -> measured back close to target
    assert abs(body["nominal"]["loop_bandwidth_hz"] - 20e3) / 20e3 < 0.25
    assert abs(body["nominal"]["phase_margin_deg"] - 50.0) < 6.0
    # PVT sweep: nominal + 4 box corners
    assert len(body["corners"]) == 5
    assert any(c["is_nominal"] for c in body["corners"])
    # plots are populated
    assert len(body["bode"]["freq_hz"]) == len(body["bode"]["open_mag_db"]) > 0
    assert len(body["step_response"]["x"]) == len(body["step_response"]["y"]) > 0


def test_design_rejects_out_of_range_output():
    bad = {**DESIGN, "f_out_hz": 100e9}     # far above any device's VCO range
    r = client.post("/api/design", json=bad)
    assert r.status_code == 400


def test_design_unknown_device_404():
    r = client.post("/api/design", json={**DESIGN, "device_id": "nope"})
    assert r.status_code == 404


def test_explore_returns_ranked_candidates():
    body_in = {
        "device_id": "adf4351", "f_out_hz": 2.4e9, "f_pfd_hz": 10e6,
        "corner": {"kvco_tol": 0.30, "icp_tol": 0.10},
        "spec": {"min_phase_margin_deg": 45.0, "max_jitter_peaking_db": 3.0},
    }
    r = client.post("/api/explore", json=body_in)
    assert r.status_code == 200
    body = r.json()
    assert body["candidates"]
    # if any pass, the first should be a passing design
    if body["any_pass"]:
        assert body["candidates"][0]["passes"]


def test_recommend_uses_surrogate_when_available():
    body_in = {
        "device_id": "adf4351", "f_out_hz": 2.4e9, "f_pfd_hz": 10e6,
        "spec": {"min_phase_margin_deg": 48.0, "max_jitter_peaking_db": 3.0},
    }
    r = client.post("/api/recommend", json=body_in)
    assert r.status_code == 200
    body = r.json()
    # models are committed, so the surrogate should load and return a recommendation
    assert body["model_available"] is True
    if body["recommended_fc_hz"] is not None:
        assert body["recommended_fc_hz"] > 0
        assert body["predicted_worst_phase_margin_deg"] >= 48.0 - 1.0
