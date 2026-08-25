"""Fundamental scorer — within-GICS-sector z-score based.

Design principles (based on Barra USE4 / AQR QMJ / Ehsani et al. 2023):
1. Within-sector z-score: eliminates growth/value style bias
2. Sector-specific indicator weights: Financials (PBR core), IT (growth·profitability focus),
   Utilities (FCF·earnings yield), etc.
3. Point-in-time: only data before as_of_date used (look-ahead bias blocked)
4. Insufficient data handling: indicator absent → NaN → weight redistribution
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl

from config.normalization import (
    SECTOR_FUNDAMENTAL_WEIGHTS,
    DEFAULT_FUNDAMENTAL_WEIGHTS,
    GICS_SECTOR_NAMES,
    FUNDAMENTAL_NORM,
)
from .base import BaseScorer

# Minimum company count required for sector z-score
_MIN_SECTOR_SIZE = 10
# z-score clipping range → [0, 100] conversion
_Z_CLIP = 3.0


class FundamentalScorer(BaseScorer):
    def __init__(
        self,
        sector_latest_df: pl.DataFrame,
        sector_code: str,
        historical_df: pl.DataFrame | None = None,  # legacy parameter — ignored
    ) -> None:
        """
        Args:
            sector_latest_df: Point-in-time latest values for all companies in the sector
                              (return value of WRDSFetcher.get_sector_latest())
            sector_code:      GICS sector code (e.g., "45")
            historical_df:    Legacy parameter — ignored
        """
        self._sector_df = sector_latest_df
        self._sector_code = sector_code
        self._weights = SECTOR_FUNDAMENTAL_WEIGHTS.get(sector_code, DEFAULT_FUNDAMENTAL_WEIGHTS)
        self._sector_name = GICS_SECTOR_NAMES.get(sector_code, f"Unknown({sector_code})")

        # Per-indicator distribution cache for the sector {metric: (mean, std)}
        self._dist_cache: dict[str, tuple[float, float]] = {}

    # ── Public interface ───────────────────────────────────────────────────────

    def score(self, raw_values: dict[str, float], as_of_date: str = "") -> dict[str, float]:
        """Raw fundamental values for the ticker → within-sector z-score based [0,100] score dict."""
        scores: dict[str, float] = {}

        for metric, weight in self._weights.items():
            if weight == 0.0:
                continue  # Indicator not used in this sector

            value = raw_values.get(metric)
            if value is None or not math.isfinite(value):
                scores[metric] = float("nan")
                continue

            try:
                scores[metric] = self._zscore_to_100(metric, value)
            except Exception:
                scores[metric] = float("nan")

        return scores

    def composite_score(self, raw_values: dict[str, float], as_of_date: str = "") -> float:
        """Returns a single composite score [0,100] after applying sector weights."""
        indicator_scores = self.score(raw_values, as_of_date)
        return _weighted_mean(indicator_scores, self._weights)

    @property
    def sector_name(self) -> str:
        return self._sector_name

    @property
    def sector_size(self) -> int:
        """Number of companies in the sector (z-score population size)."""
        return len(self._sector_df) if not self._sector_df.is_empty() else 0

    # ── Internal implementation ────────────────────────────────────────────────

    def _get_distribution(self, metric: str) -> tuple[float, float] | None:
        """Indicator distribution within sector (mean, std) — with caching."""
        if metric in self._dist_cache:
            return self._dist_cache[metric]

        if self._sector_df.is_empty() or metric not in self._sector_df.columns:
            return None

        if self.sector_size < _MIN_SECTOR_SIZE:
            return None  # Insufficient sector sample

        vals = self._sector_df[metric].drop_nulls()
        # Winsorize extremes (clip to 1%–99% range) → prevents outliers from distorting the distribution
        if len(vals) < _MIN_SECTOR_SIZE:
            return None

        arr = vals.to_numpy().astype(float)
        arr = arr[np.isfinite(arr)]
        if len(arr) < _MIN_SECTOR_SIZE:
            return None

        p1, p99 = np.percentile(arr, [1, 99])
        arr_w = np.clip(arr, p1, p99)

        mean = float(arr_w.mean())
        std  = float(arr_w.std())
        if std < 1e-9:
            return None  # No variance → meaningless z-score

        self._dist_cache[metric] = (mean, std)
        return mean, std

    def _zscore_to_100(self, metric: str, value: float) -> float:
        """Converts a value to within-sector z-score → [0,100]."""
        dist = self._get_distribution(metric)
        if dist is None:
            return float("nan")

        mean, std = dist
        z = (value - mean) / std
        z_clipped = float(np.clip(z, -_Z_CLIP, _Z_CLIP))
        score = (z_clipped + _Z_CLIP) / (2 * _Z_CLIP) * 100.0

        # Direction inversion (higher = worse indicators: pbr, de_ratio)
        norm_cfg = FUNDAMENTAL_NORM.get(metric)
        if norm_cfg and norm_cfg.invert:
            score = 100.0 - score

        return float(score)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _weighted_mean(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Skips NaN indicators and proportionally redistributes remaining weights to compute mean."""
    total_w = 0.0
    total_s = 0.0
    for metric, w in weights.items():
        if w == 0.0:
            continue
        v = scores.get(metric)
        if v is None or not math.isfinite(v):
            continue
        total_s += v * w
        total_w += w
    return total_s / total_w if total_w > 0.0 else float("nan")
