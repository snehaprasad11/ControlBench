"""
Model training.

Three models are trained on the synthetic dataset:

  * a **classifier** that predicts which controller will win (best_controller), and
  * two **regressors** that predict the winner's settling_time and overshoot.

Random forests are a good default here: they handle the mixed-scale features, need
no scaling, are robust to outliers (some plants settle very slowly), and expose
feature importances for interpretation.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score, mean_absolute_error

from .features import FEATURE_NAMES

# Regularised forests: capping depth and raising the leaf size keeps the pickled
# models small (~7 MB total vs ~45 MB unregularised) with negligible accuracy loss,
# and actually improves overshoot generalisation.
def _forest_kwargs(seed: int) -> dict:
    return dict(n_estimators=150, max_depth=12, min_samples_leaf=5,
                random_state=seed, n_jobs=-1)


_MODEL_FILES = {
    "classifier": "controller_classifier.joblib",
    "settling": "settling_regressor.joblib",
    "overshoot": "overshoot_regressor.joblib",
}


def train_models(df: pd.DataFrame, test_size: float = 0.2, seed: int = 0) -> dict:
    """
    Train the classifier and the two regressors, returning the fitted models,
    their held-out test scores, and the feature list they expect.
    """
    X = df[FEATURE_NAMES]
    y_cls = df["best_controller"]
    y_settling = df["best_settling_time"]
    y_overshoot = df["best_overshoot"]

    # One split, shared across all three targets so they are evaluated on the same rows.
    # Stratify by controller so the class balance is preserved -- but only when every
    # class has at least two members, otherwise stratification is impossible.
    stratify = y_cls if y_cls.value_counts().min() >= 2 else None
    idx_train, idx_test = train_test_split(
        df.index, test_size=test_size, random_state=seed, stratify=stratify
    )

    clf = RandomForestClassifier(**_forest_kwargs(seed))
    clf.fit(X.loc[idx_train], y_cls.loc[idx_train])

    reg_settling = RandomForestRegressor(**_forest_kwargs(seed))
    reg_settling.fit(X.loc[idx_train], y_settling.loc[idx_train])

    reg_overshoot = RandomForestRegressor(**_forest_kwargs(seed))
    reg_overshoot.fit(X.loc[idx_train], y_overshoot.loc[idx_train])

    scores = {
        "controller_accuracy": float(accuracy_score(
            y_cls.loc[idx_test], clf.predict(X.loc[idx_test]))),
        "settling_r2": float(r2_score(
            y_settling.loc[idx_test], reg_settling.predict(X.loc[idx_test]))),
        "settling_mae": float(mean_absolute_error(
            y_settling.loc[idx_test], reg_settling.predict(X.loc[idx_test]))),
        "overshoot_r2": float(r2_score(
            y_overshoot.loc[idx_test], reg_overshoot.predict(X.loc[idx_test]))),
        "overshoot_mae": float(mean_absolute_error(
            y_overshoot.loc[idx_test], reg_overshoot.predict(X.loc[idx_test]))),
        "n_train": int(len(idx_train)),
        "n_test": int(len(idx_test)),
    }

    return {
        "classifier": clf,
        "settling": reg_settling,
        "overshoot": reg_overshoot,
        "features": FEATURE_NAMES,
        "scores": scores,
    }


def save_models(models: dict, directory: str | Path) -> Path:
    """Persist the three fitted models to `directory`."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for key, filename in _MODEL_FILES.items():
        joblib.dump(models[key], directory / filename)
    return directory


def load_models(directory: str | Path) -> dict:
    """Load models previously saved with `save_models`."""
    directory = Path(directory)
    models = {key: joblib.load(directory / fn) for key, fn in _MODEL_FILES.items()}
    models["features"] = FEATURE_NAMES
    return models
