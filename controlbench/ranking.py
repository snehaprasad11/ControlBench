"""
Ranking engine — turn six raw metrics per controller into one comparable score.

The metrics live on different scales and point in different directions (a small
settling time is good; a large phase margin is good). To combine them we:

  1. normalise each metric across the candidates to a 0..1 "goodness" score
     (1 = best in this comparison, 0 = worst),
  2. take a weighted sum of those scores, and
  3. sort descending, so the recommended controller is first.

Unstable designs are sent straight to the bottom with a score of 0 -- a controller
that does not stabilise the plant cannot be "better" on any trade-off.

Weights are exposed so a user can bias the recommendation toward what they care
about (e.g. more weight on overshoot for a safety-critical system).
"""

from __future__ import annotations

from dataclasses import dataclass

from .analysis.metrics import Metrics

# Each metric: (higher_is_better, cap). The cap clips unbounded "good" directions
# (an infinite gain/phase margin) to a finite value before normalising.
_METRIC_SPECS = {
    "rise_time":          (False, None),
    "settling_time":      (False, None),
    "overshoot":          (False, None),
    "steady_state_error": (False, None),
    "gain_margin_db":     (True, 40.0),
    "phase_margin_deg":   (True, 90.0),
}

DEFAULT_WEIGHTS = {
    "settling_time":      0.25,
    "overshoot":          0.25,
    "rise_time":          0.15,
    "steady_state_error": 0.15,
    "gain_margin_db":     0.10,
    "phase_margin_deg":   0.10,
}


@dataclass(frozen=True)
class RankedResult:
    """One controller's place on the leaderboard."""

    name: str
    score: float                 # composite 0..1 (higher is better)
    metrics: Metrics
    breakdown: dict              # per-metric normalised scores


def rank(metrics_by_name: dict[str, Metrics],
         weights: dict[str, float] | None = None) -> list[RankedResult]:
    """Rank controllers best-first from their metrics."""
    weights = _normalise_weights(weights or DEFAULT_WEIGHTS)

    # Normalisation ranges come from the stable candidates only; unstable ones
    # would otherwise poison the min/max with +inf.
    stable = {n: m for n, m in metrics_by_name.items() if m.stable}
    ranges = {metric: _range(stable, metric) for metric in _METRIC_SPECS}

    results: list[RankedResult] = []
    for name, m in metrics_by_name.items():
        if not m.stable:
            results.append(RankedResult(name, 0.0, m, {}))
            continue
        breakdown = {
            metric: _score(getattr(m, metric), metric, *ranges[metric])
            for metric in _METRIC_SPECS
        }
        composite = sum(weights[k] * breakdown[k] for k in weights)
        results.append(RankedResult(name, float(composite), m, breakdown))

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def recommend(metrics_by_name: dict[str, Metrics],
              weights: dict[str, float] | None = None) -> RankedResult:
    """Return just the top-ranked controller."""
    return rank(metrics_by_name, weights)[0]


# ---------------------------------------------------------------- internals

def _clip(value: float, metric: str) -> float:
    """Apply a metric's cap (used for unbounded 'higher is better' margins)."""
    _higher, cap = _METRIC_SPECS[metric]
    if cap is not None:
        value = min(value, cap)
    return value


def _range(stable: dict[str, Metrics], metric: str) -> tuple[float, float]:
    """Min/max of a metric across stable candidates (after capping)."""
    vals = [_clip(getattr(m, metric), metric) for m in stable.values()]
    vals = [v for v in vals if v != float("inf")]
    if not vals:
        return 0.0, 0.0
    return min(vals), max(vals)


def _score(value: float, metric: str, lo: float, hi: float) -> float:
    """Normalise one metric value to a 0..1 goodness score."""
    higher_is_better, _cap = _METRIC_SPECS[metric]
    value = _clip(value, metric)
    if value == float("inf"):
        # inf on a "lower is better" metric is the worst possible outcome.
        return 1.0 if higher_is_better else 0.0
    if hi == lo:
        return 1.0                       # everyone tied -> everyone gets full marks
    t = (value - lo) / (hi - lo)
    return t if higher_is_better else 1.0 - t


def _normalise_weights(weights: dict[str, float]) -> dict[str, float]:
    """Scale weights to sum to 1 so scores stay in 0..1 regardless of input."""
    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("Weights must sum to a positive value.")
    return {k: v / total for k, v in weights.items()}
