"""
Machine-learning layer: predict the recommended controller and its key metrics
directly from a plant's transfer function, without running the full comparison.
"""

from .features import FEATURE_NAMES, plant_features
from .dataset import random_stable_plant, generate_dataset, save_dataset, load_dataset
from .train import train_models, save_models, load_models
from .predict import predict

__all__ = [
    "FEATURE_NAMES", "plant_features",
    "random_stable_plant", "generate_dataset", "save_dataset", "load_dataset",
    "train_models", "save_models", "load_models",
    "predict",
]
