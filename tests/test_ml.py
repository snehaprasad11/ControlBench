"""Tests for the Phase 4 ML layer (features, dataset, train, predict)."""

import numpy as np
import pytest

from controlbench.analysis import PlantModel
from controlbench.ml import (
    FEATURE_NAMES, plant_features,
    random_stable_plant, generate_dataset,
    train_models, save_models, load_models, predict,
)
from controlbench.ml.dataset import TARGET_NAMES


def test_features_have_expected_keys_and_are_finite():
    feats = plant_features(PlantModel([1], [1, 0.4, 1]))
    assert list(feats) == FEATURE_NAMES
    assert all(np.isfinite(v) for v in feats.values())


def test_features_finite_even_for_integrator_plant():
    # 1/(s(s+1)) has a pole at the origin -> infinite DC gain; must stay finite.
    feats = plant_features(PlantModel([1], [1, 1, 0]))
    assert all(np.isfinite(v) for v in feats.values())


def test_random_stable_plant_is_stable():
    rng = np.random.default_rng(0)
    for _ in range(50):
        assert random_stable_plant(rng).is_stable


def test_generate_dataset_shape_and_columns():
    df = generate_dataset(40, seed=3)
    assert len(df) == 40
    assert list(df.columns) == FEATURE_NAMES + TARGET_NAMES
    # every labelled winner is one of the five controllers
    assert set(df["best_controller"]).issubset({"P", "PI", "PID", "Lead", "Lag"})


def test_generate_dataset_is_deterministic():
    a = generate_dataset(30, seed=7)
    b = generate_dataset(30, seed=7)
    assert a.equals(b)


def test_train_and_predict_roundtrip(tmp_path):
    df = generate_dataset(120, seed=5)
    models = train_models(df, seed=5)

    # scores dict is well-formed
    assert 0.0 <= models["scores"]["controller_accuracy"] <= 1.0

    # predict returns the expected shape on a fresh plant
    pred = predict(PlantModel([1], [1, 2, 1]), models)
    assert pred["recommended_controller"] in {"P", "PI", "PID", "Lead", "Lag"}
    assert np.isfinite(pred["predicted_settling_time"])
    assert np.isfinite(pred["predicted_overshoot"])

    # save/load roundtrip yields the same predictions (up to float noise)
    save_models(models, tmp_path)
    reloaded = load_models(tmp_path)
    pred2 = predict(PlantModel([1], [1, 2, 1]), reloaded)
    assert pred2["recommended_controller"] == pred["recommended_controller"]
    assert pred2["predicted_settling_time"] == pytest.approx(pred["predicted_settling_time"])
    assert pred2["predicted_overshoot"] == pytest.approx(pred["predicted_overshoot"])
