"""
End-to-end comparison: design every controller, measure it, rank the field.

This is the one call the backend (Phase 5) will make per request.
"""

from __future__ import annotations

from .analysis import PlantModel, evaluate, Metrics
from .controllers import design_all, Controller
from .ranking import rank, RankedResult


def compare_controllers(
    plant: PlantModel,
    weights: dict[str, float] | None = None,
) -> tuple[list[RankedResult], dict[str, Controller], dict[str, Metrics]]:
    """
    Design all controllers for `plant`, evaluate each, and rank them.

    Returns
    -------
    ranked       : list[RankedResult]  -- best first
    controllers  : dict[str, Controller]  -- the designed controllers, by name
    metrics      : dict[str, Metrics]  -- the raw metrics, by name
    """
    controllers = design_all(plant)
    metrics = {name: evaluate(plant, c) for name, c in controllers.items()}
    ranked = rank(metrics, weights)
    return ranked, controllers, metrics
