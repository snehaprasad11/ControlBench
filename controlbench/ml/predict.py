"""
Inference — predict the recommended controller and its key metrics for a plant,
in milliseconds, without running the full comparison.
"""

from __future__ import annotations

import pandas as pd

from .features import plant_features


def predict(plant, models: dict) -> dict:
    """
    Predict for a single plant using trained models.

    Returns a dict with the predicted recommended controller and the expected
    settling time and overshoot of that controller.
    """
    features = plant_features(plant)
    X = pd.DataFrame([features])[models["features"]]

    return {
        "recommended_controller": str(models["classifier"].predict(X)[0]),
        "predicted_settling_time": float(models["settling"].predict(X)[0]),
        "predicted_overshoot": float(models["overshoot"].predict(X)[0]),
    }
