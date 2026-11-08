"""Laplacian sharpness of a grayscale picture (spec 041, FR-026 step 3)."""

from __future__ import annotations

import numpy as np
import pytest
from adapters.image.laplacian import laplacian_sharpness


def test_a_flat_picture_scores_zero() -> None:
    assert laplacian_sharpness(np.full((40, 40), 128.0, dtype=np.float32)) == 0.0


def test_a_checkerboard_is_sharper_than_a_smooth_gradient() -> None:
    checker = np.indices((40, 40)).sum(axis=0) % 2 * 255.0
    gradient = np.tile(np.linspace(0, 255, 40, dtype=np.float32), (40, 1))
    assert laplacian_sharpness(checker.astype(np.float32)) > laplacian_sharpness(gradient)


def test_the_score_does_not_depend_on_size() -> None:
    def pattern(size: int) -> np.ndarray:
        return (np.indices((size, size)).sum(axis=0) % 2 * 255.0).astype(np.float32)

    small = laplacian_sharpness(pattern(40))
    large = laplacian_sharpness(pattern(200))
    assert large == pytest.approx(small, rel=0.01)


def test_a_picture_that_is_not_2d_is_refused() -> None:
    with pytest.raises(ValueError):
        laplacian_sharpness(np.zeros((4, 4, 3), dtype=np.float32))
