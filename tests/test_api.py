"""Tests for the FastAPI backend."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

PLANT = {"num": [1], "den": [1, 3, 3, 1]}          # 1/(s+1)^3
SECOND_ORDER = {"num": [1], "den": [1, 2, 1]}       # infinite gain margin


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_returns_structure():
    r = client.post("/api/analyze", json=PLANT)
    assert r.status_code == 200
    body = r.json()
    assert body["order"] == 3
    assert body["stable"] is True
    assert len(body["poles"]) == 3
    assert set(body["poles"][0]) == {"re", "im"}


def test_analyze_rejects_improper_plant():
    r = client.post("/api/analyze", json={"num": [1, 0, 0], "den": [1, 1]})
    assert r.status_code == 400


def test_compare_returns_ranked_results_with_step_responses():
    r = client.post("/api/compare", json=PLANT)
    assert r.status_code == 200
    body = r.json()
    assert body["recommended"] == body["results"][0]["name"]
    assert {res["name"] for res in body["results"]} == {"P", "PI", "PID", "Lead", "Lag"}
    # scores are sorted descending
    scores = [res["score"] for res in body["results"]]
    assert scores == sorted(scores, reverse=True)
    # each result carries metrics and a non-empty step response
    top = body["results"][0]
    assert "settling_time" in top["metrics"]
    assert len(top["step_response"]["time"]) == len(top["step_response"]["output"]) > 0


def test_compare_serialises_infinite_margin_as_null():
    # 2nd-order plant -> phase never hits -180 -> infinite gain margin -> null in JSON
    r = client.post("/api/compare", json=SECOND_ORDER)
    assert r.status_code == 200
    gms = [res["metrics"]["gain_margin_db"] for res in r.json()["results"]]
    assert any(g is None for g in gms)


def test_compare_custom_weights_change_ranking():
    overshoot_focus = {**PLANT, "weights": {"overshoot": 1.0, "settling_time": 0.0}}
    r = client.post("/api/compare", json=overshoot_focus)
    assert r.status_code == 200
    # the winner under an overshoot-only weighting should have (near) zero overshoot
    top = r.json()["results"][0]
    assert top["metrics"]["overshoot"] in (0.0, None) or top["metrics"]["overshoot"] < 5.0


def test_predict_returns_a_controller():
    r = client.post("/api/predict", json=PLANT)
    # models are committed, so prediction should work
    assert r.status_code == 200
    assert r.json()["recommended_controller"] in {"P", "PI", "PID", "Lead", "Lag"}
