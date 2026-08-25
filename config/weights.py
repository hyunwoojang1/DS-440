"""Weight matrix registry by time horizon.

v2.0 changes:
- Short=daily, Mid=weekly, Long=monthly resolution separation with weight rebalancing
- Long-term technical weight: 0.05 → 0.25 (monthly RSI/MACD/SMA are valid long-term signals)
- Mid-term technical weight: 0.35 → 0.40 (weekly bars have less noise than daily)
"""

from typing import Literal

Horizon = Literal["short", "mid", "long"]

# ── Cross-group weights (sum = 1.0) ──────────────────────────────────────────
# Short (daily):  short-term price momentum dominant → Tech 70%
# Mid  (weekly):  weekly technical signal weight increased → Tech 40%
# Long (monthly): monthly technical indicators meaningful, raised to Tech 25%,
#                 Macro+Fund still dominant at 75%
HORIZON_GROUP_WEIGHTS: dict[Horizon, dict[str, float]] = {
    "short": {"macro": 0.20, "fundamental": 0.10, "technical": 0.70},
    "mid":   {"macro": 0.30, "fundamental": 0.30, "technical": 0.40},
    "long":  {"macro": 0.40, "fundamental": 0.35, "technical": 0.25},
}

# ── Per-indicator weights within Macro group (sum = 1.0) ─────────────────────
MACRO_INDICATOR_WEIGHTS: dict[Horizon, dict[str, float]] = {
    "short": {
        "YIELD_CURVE_SPREAD": 0.15,
        "FEDFUNDS":           0.15,
        "CPIAUCSL":           0.10,
        "PCEPILFE":           0.10,
        "CREDIT_SPREAD":      0.20,
        "UNRATE":             0.10,
        "M2SL":               0.05,
        "ICSA":               0.15,
    },
    "mid": {
        "YIELD_CURVE_SPREAD": 0.20,
        "FEDFUNDS":           0.20,
        "CPIAUCSL":           0.15,
        "PCEPILFE":           0.10,
        "CREDIT_SPREAD":      0.15,
        "UNRATE":             0.10,
        "M2SL":               0.05,
        "ICSA":               0.05,
    },
    "long": {
        "YIELD_CURVE_SPREAD": 0.25,
        "FEDFUNDS":           0.20,
        "CPIAUCSL":           0.15,
        "PCEPILFE":           0.10,
        "CREDIT_SPREAD":      0.15,
        "UNRATE":             0.10,
        "M2SL":               0.05,
        "ICSA":               0.00,
    },
}

# ── Per-indicator weights within Fundamental group (sum = 1.0) ───────────────
FUNDAMENTAL_INDICATOR_WEIGHTS: dict[Horizon, dict[str, float]] = {
    "short": {
        "eps_change_rate": 0.30,
        "roe":             0.15,
        "fcf_yield":       0.15,
        "pbr":             0.10,
        "revenue_growth":  0.15,
        "de_ratio":        0.10,
        "earnings_yield":  0.05,
    },
    "mid": {
        "eps_change_rate": 0.25,
        "roe":             0.20,
        "fcf_yield":       0.20,
        "pbr":             0.15,
        "revenue_growth":  0.10,
        "de_ratio":        0.05,
        "earnings_yield":  0.05,
    },
    "long": {
        "eps_change_rate": 0.15,
        "roe":             0.25,
        "fcf_yield":       0.25,
        "pbr":             0.20,
        "revenue_growth":  0.10,
        "de_ratio":        0.05,
        "earnings_yield":  0.00,
    },
}

# ── Per-indicator weights within Technical group (sum = 1.0) ─────────────────
#
# Short (daily):   oversold/overbought + short-term momentum focus
# Mid  (weekly):   SMA trend weight increased (weekly SMA20/100 are key indicators)
# Long (monthly):  trend (SMA10/40) + MACD + OBV focus
#                  monthly Stochastic/Bollinger %B excluded due to noise
TECHNICAL_INDICATOR_WEIGHTS: dict[Horizon, dict[str, float]] = {
    "short": {
        "rsi_14":         0.20,
        "macd_histogram": 0.20,
        "sma_ratio":      0.10,
        "stoch_k":        0.15,
        "bb_pct_b":       0.15,
        "obv_slope":      0.10,
        "atr_norm":       0.05,
        "roc":            0.05,
    },
    "mid": {
        "rsi_14":         0.15,
        "macd_histogram": 0.20,
        "sma_ratio":      0.25,   # weekly SMA20/100 weight increased
        "stoch_k":        0.10,
        "bb_pct_b":       0.10,
        "obv_slope":      0.15,   # weekly OBV slope weight increased
        "atr_norm":       0.00,   # volatility removed on weekly bars
        "roc":            0.05,
    },
    "long": {
        # trend/momentum indicators are meaningful on monthly bars
        "rsi_14":         0.15,   # monthly RSI: structural overbought/oversold assessment
        "macd_histogram": 0.20,   # monthly MACD: long-term momentum turning points
        "sma_ratio":      0.30,   # monthly SMA10/40: core of long-term trend
        "stoch_k":        0.00,   # monthly Stochastic is noisy
        "bb_pct_b":       0.00,   # monthly Bollinger has weak significance
        "obv_slope":      0.20,   # monthly OBV: institutional accumulation/distribution tracking
        "atr_norm":       0.05,   # monthly volatility (minor contribution)
        "roc":            0.10,   # 6-month ROC
    },
}

# Version tag (included in report metadata)
WEIGHT_VERSION = "v2.0.0"
