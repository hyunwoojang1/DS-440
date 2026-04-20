"""Macro indicator scorer (Polars input)."""

from __future__ import annotations
import polars as pl

from config.normalization import MACRO_NORM
from engine.normalizers.base import BaseNormalizer
from engine.normalizers.minmax import MinMaxNormalizer
from engine.normalizers.zscore import ZScoreNormalizer
from engine.normalizers.percentile import PercentileRankNormalizer
from .base import BaseScorer


def _build_normalizer(indicator_id: str) -> BaseNormalizer:
    cfg = MACRO_NORM[indicator_id]
    if cfg.method == "minmax":
        return MinMaxNormalizer(invert=cfg.invert, fixed_min=cfg.fixed_min, fixed_max=cfg.fixed_max)
    if cfg.method == "zscore":
        return ZScoreNormalizer(invert=cfg.invert, window_years=cfg.window_years)
    return PercentileRankNormalizer(invert=cfg.invert)


class MacroScorer(BaseScorer):
    def __init__(self, historical_df: pl.DataFrame) -> None:
        """
        historical_df: Polars DataFrame with a 'date' column + indicator columns.
                       Pass all data before as_of_date.
        """
        self._df = historical_df
        self._normalizers: dict[str, BaseNormalizer] = {}

    def _get_normalizer(self, indicator_id: str, as_of_date: str) -> BaseNormalizer:
        if indicator_id not in self._normalizers:
            norm = _build_normalizer(indicator_id)
            # Use only data before as_of_date for fit (blocks look-ahead bias)
            hist = (
                self._df
                .filter(pl.col("date").cast(pl.Utf8) <= as_of_date)
                [indicator_id]
                .drop_nulls()
            )
            norm.fit(hist)
            self._normalizers[indicator_id] = norm
        return self._normalizers[indicator_id]

    def score(self, raw_values: dict[str, float], as_of_date: str) -> dict[str, float]:
        scores: dict[str, float] = {}
        for ind_id, value in raw_values.items():
            if ind_id not in MACRO_NORM:
                continue
            if value is None or (value != value):   # None or NaN
                scores[ind_id] = float("nan")
                continue
            try:
                norm = self._get_normalizer(ind_id, as_of_date)
                scores[ind_id] = norm.transform(float(value))
            except Exception:
                scores[ind_id] = float("nan")
        return scores
