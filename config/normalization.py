"""Per-indicator normalization strategy mapping (includes per-resolution technical parameters)."""

from dataclasses import dataclass, field
from typing import Literal

NormMethod = Literal["minmax", "zscore", "percentile"]


@dataclass(frozen=True)
class NormConfig:
    method: NormMethod
    invert: bool = False
    window_years: int = 10
    fixed_min: float | None = None
    fixed_max: float | None = None


@dataclass(frozen=True)
class TechIndicatorParams:
    """Per-resolution technical indicator parameters."""
    rsi_length: int
    macd_fast: int
    macd_slow: int
    macd_signal: int
    sma_fast: int       # SMA ratio numerator
    sma_slow: int       # SMA ratio denominator
    bb_length: int
    stoch_k: int
    stoch_d: int
    obv_slope_window: int
    atr_length: int
    roc_length: int
    min_bars: int       # Minimum bar count required for indicator computation at this resolution


# ── Per-resolution technical indicator parameters ─────────────────────────────
TECH_PARAMS: dict[str, TechIndicatorParams] = {
    "daily": TechIndicatorParams(
        rsi_length=14,
        macd_fast=12, macd_slow=26, macd_signal=9,
        sma_fast=50,  sma_slow=200,
        bb_length=20,
        stoch_k=14,   stoch_d=3,
        obv_slope_window=20,
        atr_length=14,
        roc_length=10,
        min_bars=200,   # SMA200 computation baseline
    ),
    "weekly": TechIndicatorParams(
        rsi_length=14,
        macd_fast=12, macd_slow=26, macd_signal=9,
        sma_fast=20,  sma_slow=100,
        bb_length=20,
        stoch_k=14,   stoch_d=3,
        obv_slope_window=20,
        atr_length=14,
        roc_length=10,
        min_bars=100,   # SMA100 computation baseline
    ),
    "monthly": TechIndicatorParams(
        rsi_length=14,
        macd_fast=6,  macd_slow=12, macd_signal=9,
        sma_fast=10,  sma_slow=40,
        bb_length=20,
        stoch_k=14,   stoch_d=3,
        obv_slope_window=12,
        atr_length=12,
        roc_length=6,
        min_bars=40,    # SMA40 computation baseline
    ),
}

# ── Macro indicator normalization config ──────────────────────────────────────
MACRO_NORM: dict[str, NormConfig] = {
    "FEDFUNDS":           NormConfig("zscore",     invert=True,  window_years=10),
    "DGS10":              NormConfig("zscore",     invert=True,  window_years=10),
    "DGS2":               NormConfig("zscore",     invert=True,  window_years=10),
    "YIELD_CURVE_SPREAD": NormConfig("minmax",     invert=False, fixed_min=-3.0, fixed_max=4.0),
    "CPIAUCSL":           NormConfig("minmax",     invert=True,  fixed_min=0.0,  fixed_max=10.0),
    "PCEPILFE":           NormConfig("minmax",     invert=True,  fixed_min=0.0,  fixed_max=8.0),
    "UNRATE":             NormConfig("zscore",     invert=True,  window_years=10),
    "ICSA":               NormConfig("zscore",     invert=True,  window_years=10),
    "M2SL":               NormConfig("zscore",     invert=False, window_years=10),
    "CREDIT_SPREAD":      NormConfig("minmax",     invert=True,  fixed_min=0.0,  fixed_max=5.0),
}

# ── Fundamental indicator normalization config ────────────────────────────────
FUNDAMENTAL_NORM: dict[str, NormConfig] = {
    "pbr":             NormConfig("percentile", invert=True,  window_years=5),
    "eps_change_rate": NormConfig("zscore",     invert=False, window_years=5),
    "roe":             NormConfig("percentile", invert=False, window_years=5),
    "fcf_yield":       NormConfig("percentile", invert=False, window_years=5),
    "de_ratio":        NormConfig("percentile", invert=True,  window_years=5),
    "revenue_growth":  NormConfig("zscore",     invert=False, window_years=5),
    "earnings_yield":  NormConfig("percentile", invert=False, window_years=5),
}

# ── Technical indicator normalization config (resolution-agnostic — see TECH_PARAMS for parameters) ──
TECHNICAL_NORM: dict[str, NormConfig] = {
    "rsi_14":         NormConfig("minmax",  invert=False, fixed_min=0.0,  fixed_max=100.0),
    "macd_histogram": NormConfig("zscore",  invert=False, window_years=2),
    "sma_ratio":      NormConfig("minmax",  invert=False, fixed_min=0.85, fixed_max=1.15),
    "stoch_k":        NormConfig("minmax",  invert=False, fixed_min=0.0,  fixed_max=100.0),
    "bb_pct_b":       NormConfig("minmax",  invert=False, fixed_min=0.0,  fixed_max=1.0),
    "obv_slope":      NormConfig("zscore",  invert=False, window_years=1),
    "atr_norm":       NormConfig("zscore",  invert=True,  window_years=2),
    "roc":            NormConfig("zscore",  invert=False, window_years=2),
}

# RSI V-shape non-linear scoring (oversold=high score, overbought=low score)
RSI_NONLINEAR = True

# ── GICS sector code mapping ──────────────────────────────────────────────────
GICS_SECTOR_NAMES: dict[str, str] = {
    "10": "Energy",
    "15": "Materials",
    "20": "Industrials",
    "25": "Consumer Discretionary",
    "30": "Consumer Staples",
    "35": "Health Care",
    "40": "Financials",
    "45": "Information Technology",
    "50": "Communication Services",
    "55": "Utilities",
    "60": "Real Estate",
}

# ── Per-sector fundamental indicator weights ───────────────────────────────────
# Rationale: Barra USE4, AQR QMJ, Novy-Marx(2013), Peters&Taylor(2017), Ehsani et al.(2023)
# Keys: GICS sector code (string)
# Values: per-indicator weights (sum = 1.0)
# Financials: D/E·FCF removed (debt is an operating tool), PBR is core
# Utilities/RE: PBR·D/E removed, earnings_yield·FCF emphasized
# IT/Comm: PBR weight minimized (distorted by intangibles), growth·profitability emphasized
SECTOR_FUNDAMENTAL_WEIGHTS: dict[str, dict[str, float]] = {
    "45": {  # Information Technology
        "roe": 0.20, "eps_change_rate": 0.25, "revenue_growth": 0.25,
        "fcf_yield": 0.15, "pbr": 0.10, "de_ratio": 0.05, "earnings_yield": 0.00,
    },
    "50": {  # Communication Services
        "roe": 0.20, "eps_change_rate": 0.20, "revenue_growth": 0.25,
        "fcf_yield": 0.20, "pbr": 0.10, "de_ratio": 0.05, "earnings_yield": 0.00,
    },
    "25": {  # Consumer Discretionary
        "roe": 0.20, "eps_change_rate": 0.20, "revenue_growth": 0.20,
        "fcf_yield": 0.15, "pbr": 0.10, "de_ratio": 0.10, "earnings_yield": 0.05,
    },
    "30": {  # Consumer Staples
        "roe": 0.20, "eps_change_rate": 0.15, "revenue_growth": 0.15,
        "fcf_yield": 0.20, "pbr": 0.10, "de_ratio": 0.10, "earnings_yield": 0.10,
    },
    "35": {  # Health Care
        "roe": 0.20, "eps_change_rate": 0.25, "revenue_growth": 0.20,
        "fcf_yield": 0.20, "pbr": 0.05, "de_ratio": 0.05, "earnings_yield": 0.05,
    },
    "20": {  # Industrials
        "roe": 0.25, "eps_change_rate": 0.20, "revenue_growth": 0.15,
        "fcf_yield": 0.20, "pbr": 0.10, "de_ratio": 0.10, "earnings_yield": 0.00,
    },
    "10": {  # Energy
        "roe": 0.20, "eps_change_rate": 0.10, "revenue_growth": 0.15,
        "fcf_yield": 0.25, "pbr": 0.10, "de_ratio": 0.15, "earnings_yield": 0.05,
    },
    "15": {  # Materials
        "roe": 0.20, "eps_change_rate": 0.10, "revenue_growth": 0.15,
        "fcf_yield": 0.25, "pbr": 0.10, "de_ratio": 0.15, "earnings_yield": 0.05,
    },
    "40": {  # Financials — D/E·FCF fully removed, P/B is core
        "roe": 0.35, "eps_change_rate": 0.20, "revenue_growth": 0.15,
        "fcf_yield": 0.00, "pbr": 0.30, "de_ratio": 0.00, "earnings_yield": 0.00,
    },
    "55": {  # Utilities — PBR·D/E removed, earnings_yield·FCF focus
        "roe": 0.20, "eps_change_rate": 0.10, "revenue_growth": 0.10,
        "fcf_yield": 0.30, "pbr": 0.00, "de_ratio": 0.00, "earnings_yield": 0.30,
    },
    "60": {  # Real Estate — PBR·D/E removed, FCF(≈FFO proxy)·earnings_yield focus
        "roe": 0.20, "eps_change_rate": 0.10, "revenue_growth": 0.10,
        "fcf_yield": 0.35, "pbr": 0.00, "de_ratio": 0.00, "earnings_yield": 0.25,
    },
}

# Fallback for unknown sector
DEFAULT_FUNDAMENTAL_WEIGHTS: dict[str, float] = {
    "roe": 0.20, "eps_change_rate": 0.20, "revenue_growth": 0.20,
    "fcf_yield": 0.15, "pbr": 0.10, "de_ratio": 0.10, "earnings_yield": 0.05,
}
