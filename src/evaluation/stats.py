"""Statistical intervals used for explicitly denominated reported rates."""

from __future__ import annotations

import math


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Return the two-sided Wilson score interval for a binomial proportion."""
    if n < 0 or successes < 0 or successes > n:
        raise ValueError("require 0 <= successes <= n")
    if n == 0:
        return (0.0, 1.0)
    probability = successes / n
    denominator = 1 + z**2 / n
    center = (probability + z**2 / (2 * n)) / denominator
    half = (
        z
        * math.sqrt(
            probability * (1 - probability) / n + z**2 / (4 * n**2)
        )
        / denominator
    )
    return (max(0.0, center - half), min(1.0, center + half))
