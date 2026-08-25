"""Normalizer base interface — supports both numpy and Polars."""

from __future__ import annotations
from abc import ABC, abstractmethod

import numpy as np
import polars as pl


def _to_numpy(data: "pl.Series | np.ndarray | list") -> np.ndarray:
    """Converts various inputs to NaN-free float numpy arrays."""
    if isinstance(data, pl.Series):
        arr = data.drop_nulls().cast(pl.Float64).to_numpy()
    elif isinstance(data, np.ndarray):
        arr = data[~np.isnan(data.astype(float))]
    else:
        arr = np.array(data, dtype=float)
        arr = arr[~np.isnan(arr)]
    return arr.astype(float)


class BaseNormalizer(ABC):
    """fit() accepts only past data before as_of_date; transform() applies to any value."""

    def __init__(self, invert: bool = False) -> None:
        self.invert = invert
        self._fitted = False

    @abstractmethod
    def fit(self, historical: "pl.Series | np.ndarray | list") -> "BaseNormalizer":
        """Learn parameters from historical data. Pass only data before as_of_date."""
        ...

    @abstractmethod
    def _transform_value(self, value: float) -> float:
        """Converts a single float value to [0, 100] (before inversion)."""
        ...

    def transform(self, value: float) -> float:
        if not self._fitted:
            raise RuntimeError("Call fit() before transform().")
        if np.isnan(value):
            return float("nan")
        score = self._transform_value(float(value))
        return 100.0 - score if self.invert else score

    def transform_series(self, series: "pl.Series | np.ndarray") -> np.ndarray:
        """Transforms an entire series and returns it as a numpy array."""
        if isinstance(series, pl.Series):
            arr = series.cast(pl.Float64).to_numpy()
        else:
            arr = np.asarray(series, dtype=float)
        return np.array([self.transform(v) for v in arr])

    def fit_transform(self, historical: "pl.Series | np.ndarray") -> np.ndarray:
        return self.fit(historical).transform_series(historical)
