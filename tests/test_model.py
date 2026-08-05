"""Tests for the Phase 1 analysis engine (PlantModel)."""

import numpy as np
import pytest

from controlbench.analysis import PlantModel, InvalidPlantError


def test_second_order_poles_and_order():
    plant = PlantModel([1], [1, 2, 1])  # 1/(s+1)^2
    assert plant.order == 2
    assert np.allclose(sorted(plant.poles.real), [-1, -1])
    assert plant.is_stable


def test_damping_and_natural_frequency():
    # 1/(s^2 + 0.4 s + 1): wn = 1, 2*zeta*wn = 0.4 -> zeta = 0.2
    plant = PlantModel([1], [1, 0.4, 1])
    assert plant.natural_frequency == pytest.approx(1.0, abs=1e-6)
    assert plant.damping_ratio == pytest.approx(0.2, abs=1e-6)


def test_unstable_detection():
    plant = PlantModel([1], [1, -1, 1])  # poles in right-half plane
    assert not plant.is_stable
    assert plant.damping_ratio < 0


def test_zeros_are_numerator_roots():
    plant = PlantModel([1, 3], [1, 3, 2])  # zero at -3
    assert np.allclose(plant.zeros.real, [-3.0])


def test_leading_zeros_are_stripped():
    plant = PlantModel([0, 1], [0, 1, 2])  # really 1/(s+2)
    assert plant.order == 1
    assert np.allclose(plant.poles.real, [-2.0])


def test_improper_transfer_function_rejected():
    with pytest.raises(InvalidPlantError):
        PlantModel([1, 0, 0], [1, 1])  # s^2/(s+1)


def test_zero_denominator_rejected():
    with pytest.raises(InvalidPlantError):
        PlantModel([1], [0, 0, 0])


def test_non_finite_rejected():
    with pytest.raises(InvalidPlantError):
        PlantModel([1], [1, float("nan"), 1])
