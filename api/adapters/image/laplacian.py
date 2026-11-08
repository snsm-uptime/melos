"""Sharpness of a grayscale picture: the variance of its Laplacian (spec 041, FR-026 step 3).

NumPy slicing only, no SciPy or OpenCV. The variance is a per-pixel mean, so the score
does not depend on the picture's size.
"""

from __future__ import annotations

import numpy as np


def laplacian_sharpness(gray: np.ndarray) -> float:
    """The variance of the 3x3 Laplacian response, per pixel. Flat pictures score 0."""
    if gray.ndim != 2:
        raise ValueError("sharpness needs a 2-D grayscale picture")
    values = gray.astype(np.float32, copy=False)
    response = (
        values[:-2, 1:-1]
        + values[2:, 1:-1]
        + values[1:-1, :-2]
        + values[1:-1, 2:]
        - 4.0 * values[1:-1, 1:-1]
    )
    # var() already averages over the pixels, so the score does not depend on the size.
    return float(response.var())
