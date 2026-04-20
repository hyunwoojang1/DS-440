"""FRED series ID constant registry."""

# Interest rates
FEDFUNDS = "FEDFUNDS"       # Federal Funds Rate
DGS10 = "DGS10"             # 10-Year Treasury Yield
DGS2 = "DGS2"               # 2-Year Treasury Yield

# Inflation
CPIAUCSL = "CPIAUCSL"       # Consumer Price Index (CPI)
PCEPILFE = "PCEPILFE"       # Core PCE Price Index

# Employment
UNRATE = "UNRATE"           # Unemployment Rate
ICSA = "ICSA"               # Initial Jobless Claims

# Liquidity
M2SL = "M2SL"               # M2 Money Supply

# Credit
BAA = "BAA"                 # Moody's BAA Corporate Bond Yield
AAA = "AAA"                 # Moody's AAA Corporate Bond Yield

# Derived indicators (require computation)
YIELD_CURVE_SPREAD = "YIELD_CURVE_SPREAD"   # DGS10 - DGS2
CREDIT_SPREAD = "CREDIT_SPREAD"             # BAA - AAA

# Full fetch series (excluding derived)
FETCH_SERIES: list[str] = [
    FEDFUNDS, DGS10, DGS2,
    CPIAUCSL, PCEPILFE,
    UNRATE, ICSA,
    M2SL,
    BAA, AAA,
]

# Derived indicator definitions (key: derived ID, value: (series_a, series_b, operation))
DERIVED_SERIES: dict[str, tuple[str, str, str]] = {
    YIELD_CURVE_SPREAD: (DGS10, DGS2, "subtract"),
    CREDIT_SPREAD: (BAA, AAA, "subtract"),
}
