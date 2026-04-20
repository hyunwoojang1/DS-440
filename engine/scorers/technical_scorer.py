"""Technical indicator scorer — per-resolution Polars DataFrame input.

Data insufficiency handling:
- If an indicator column is null, return NaN for that indicator
- Safely handle NaN when normalization history falls below minimum threshold
"""

from __future__ import annotations
import polars as pl

from config.normalization import TECHNICAL_NORM, RSI_NONLINEAR
from engine.normalizers.base import BaseNormalizer
from engine.normalizers.minmax import MinMaxNormalizer
from engine.normalizers.zscore import ZScoreNormalizer
from engine.normalizers.percentile import PercentileRankNormalizer
from .base import BaseScorer

# Minimum number of observations required for normalizer fit
_MIN_FIT_OBSERVATIONS = 10


def _rsi_nonlinear(rsi: float) -> float:
    """RSI V-shape non-linear scoring: 30→100, 70→0, 50→50."""
    if rsi <= 30:
        return 100.0
    if rsi >= 70:
        return 0.0
    if rsi <= 50:
        return 100.0 - (rsi - 30) * 2.5
    return 50.0 - (rsi - 50) * 2.5


def _build_normalizer(indicator_id: str) -> BaseNormalizer:
    cfg = TECHNICAL_NORM[indicator_id]
    if cfg.method == "minmax":
        return MinMaxNormalizer(invert=cfg.invert, fixed_min=cfg.fixed_min, fixed_max=cfg.fixed_max)
    if cfg.method == "zscore":
        return ZScoreNormalizer(invert=cfg.invert, window_years=cfg.window_years)
    return PercentileRankNormalizer(invert=cfg.invert)


class TechnicalScorer(BaseScorer):
    def __init__(self, historical_df: pl.DataFrame) -> None:
        """
        historical_df: Polars DataFrame with a 'date' column + indicator columns.
                       Must be bar data matching the resolution (daily/weekly/monthly).
        """
        self._df = historical_df
        self._normalizers: dict[str, BaseNormalizer] = {}

    def _get_normalizer(self, indicator_id: str, as_of_date: str) -> BaseNormalizer | None:
        if indicator_id not in self._normalizers:
            if indicator_id not in self._df.columns:
                return None
            norm = _build_normalizer(indicator_id)
            hist = (
                self._df
                .filter(pl.col("date").cast(pl.Utf8) <= as_of_date)
                [indicator_id]
                .drop_nulls()
            )
            if len(hist) < _MIN_FIT_OBSERVATIONS:
                return None     # Insufficient data → null handling
            norm.fit(hist)
            self._normalizers[indicator_id] = norm
        return self._normalizers.get(indicator_id)

    def score(self, raw_values: dict[str, float], as_of_date: str) -> dict[str, float]:
        scores: dict[str, float] = {}
        for ind_id, value in raw_values.items():
            if ind_id not in TECHNICAL_NORM:
                continue
            # null/NaN value → insufficient data signal
            if value is None or (value != value):
                scores[ind_id] = float("nan")
                continue
            try:
                if ind_id == "rsi_14" and RSI_NONLINEAR:
                    scores[ind_id] = _rsi_nonlinear(float(value))
                else:
                    norm = self._get_normalizer(ind_id, as_of_date)
                    if norm is None:
                        scores[ind_id] = float("nan")
                    else:
                        scores[ind_id] = norm.transform(float(value))
            except Exception:
                scores[ind_id] = float("nan")
        return scores
