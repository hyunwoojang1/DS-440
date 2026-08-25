"""Percentile Rank normalization: relative rank within history → [0, 100]."""

from __future__ import annotations
import numpy as np
from .base import BaseNormalizer, _to_numpy


class PercentileRankNormalizer(BaseNormalizer):
    def __init__(self, invert: bool = False) -> None:
        super().__init__(invert)
        self._sorted: np.ndarray = np.array([])

    def fit(self, historical) -> "PercentileRankNormalizer":
        arr = _to_numpy(historical)
        if len(arr) == 0:
            raise ValueError("Data passed to fit() is empty.")
        self._sorted = np.sort(arr)
        self._fitted = True
        return self

    def _transform_value(self, value: float) -> float:
        n = len(self._sorted)
        rank = int(np.searchsorted(self._sorted, value, side="right"))
        return float(rank / n * 100.0)
