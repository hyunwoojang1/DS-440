"""Math utilities."""

from __future__ import annotations

import numpy as np


def clip_score(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(max(low, min(high, value)))


def rolling_linear_slope(values: np.ndarray, window: int) -> np.ndarray:
    """Linear slope within a rolling window. Processed as numpy arrays for pandas-ta internal computation."""
    n = len(values)
    result = np.full(n, np.nan)
    for i in range(window - 1, n):
        chunk = values[i - window + 1 : i + 1]
        if len(chunk) >= 2:
            result[i] = float(np.polyfit(range(len(chunk)), chunk, 1)[0])
    return result


def redistribute_weights(
    weights: dict[str, float],
    missing_keys: list[str],
) -> dict[str, float]:
    """Proportionally redistributes the weights of missing indicators to the remaining ones."""
    available = {k: v for k, v in weights.items() if k not in missing_keys}
    total = sum(available.values())
    if total == 0:
        return available
    return {k: v / total for k, v in available.items()}
