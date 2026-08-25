"""WRDS Compustat table/field registry."""

# ── Table paths ───────────────────────────────────────────────────────────────
FUNDA_TABLE   = "comp.funda"            # Annual financial statements
COMPANY_TABLE = "comp.company"          # Company header (includes gsector, tic)
FUNDQ_TABLE   = "comp.fundq"            # Quarterly financial statements
SECD_TABLE    = "comp.g_secd"           # Daily securities data
CRSP_DSF      = "crsp.dsf"             # CRSP daily stock file
LINK_TABLE    = "crsp.ccmxpf_lnkhist"  # PERMNO ↔ GVKEY link table

# ── Common identifier fields (comp.funda) ─────────────────────────────────────
KEY_FIELDS = ["f.gvkey", "f.datadate", "f.fyear", "f.indfmt", "f.consol", "f.popsrc", "f.datafmt", "f.tic"]

# ── Sector fields (comp.company JOIN) — tic is in comp.funda so included in KEY_FIELDS ──
COMPANY_FIELDS = ["c.gsector"]   # GICS sector code

# ── Financial indicator fields (comp.funda) ───────────────────────────────────
FINANCIAL_FIELDS = [
    "f.prcc_f",   # Fiscal year-end stock price
    "f.csho",     # Shares outstanding (millions)
    "f.ceq",      # Common equity (book value)
    "f.ni",       # Net income
    "f.epsfx",    # Diluted EPS
    "f.oancf",    # Operating cash flow
    "f.capx",     # Capital expenditure
    "f.mkvalt",   # Market capitalization
    "f.dltt",     # Long-term debt
    "f.dlc",      # Short-term debt
    "f.sale",     # Net sales
]

# ── Derived indicator computation definitions ─────────────────────────────────
# Structure: "indicator name": ("numerator expression", "denominator expression")
# Actual computation: numerator / denominator
# _lag4 = value 4 quarters ago (for YoY comparison)
#
DERIVED_FIELDS: dict[str, tuple[str, str]] = {

    # PBR (Price-to-Book Ratio) — lower means more undervalued
    # Computation: stock price / book value per share = prcc_f / (ceq / csho)
    # Interpretation: how many times book value the market assigns to the company
    "pbr": (
        "prcc_f",        # Numerator: fiscal year-end stock price
        "ceq / csho",    # Denominator: common equity ÷ shares outstanding = book value per share (BPS)
    ),

    # ROE (Return on Equity) — higher means more capital efficient
    # Computation: net income / common equity
    # Interpretation: how much profit generated per unit of shareholder capital invested
    "roe": (
        "ni",            # Numerator: net income
        "ceq",           # Denominator: common equity
    ),

    # EPS Change Rate YoY (earnings per share growth) — higher means stronger earnings growth
    # Computation: (current EPS - EPS 4 quarters ago) / |EPS 4 quarters ago|
    # Interpretation: how much EPS increased/decreased vs. one year ago
    "eps_change_rate": (
        "epsfx - epsfx_lag4",   # Numerator: current diluted EPS - diluted EPS 4 quarters ago
        "abs(epsfx_lag4)",       # Denominator: absolute value of EPS 4 quarters ago (sign-agnostic ratio)
    ),

    # FCF Yield (free cash flow yield) — higher means stronger cash generation
    # Computation: (operating cash flow - capital expenditure) / market cap
    # Interpretation: ratio of actual free cash flow generated relative to market cap
    "fcf_yield": (
        "oancf - capx",  # Numerator: operating cash flow - capital expenditure = free cash flow (FCF)
        "mkvalt",        # Denominator: market capitalization (Market Value of Total Assets)
    ),

    # D/E Ratio (debt-to-equity ratio) — lower means more financially stable
    # Computation: (long-term debt + short-term debt) / common equity
    # Interpretation: how many units of debt are used per unit of equity capital
    "de_ratio": (
        "dltt + dlc",    # Numerator: long-term debt + short-term debt (debt in current liabilities)
        "ceq",           # Denominator: common equity
    ),

    # Revenue Growth Rate YoY — higher means stronger top-line growth
    # Computation: (current sales - sales 4 quarters ago) / sales 4 quarters ago
    # Interpretation: how much net sales increased/decreased vs. one year ago
    "revenue_growth": (
        "sale - sale_lag4",  # Numerator: current sales - sales 4 quarters ago
        "sale_lag4",         # Denominator: sales 4 quarters ago (baseline)
    ),

    # Earnings Yield — higher means more undervalued (inverse of P/E)
    # Computation: diluted EPS / stock price = 1 / P/E
    # Interpretation: how much earnings are attributable per unit of stock price. P/E 15 → Earnings Yield 6.7%
    "earnings_yield": (
        "epsfx",         # Numerator: diluted EPS
        "prcc_f",        # Denominator: fiscal year-end stock price
    ),
}

# ── Filter conditions (Compustat standard filters) ───────────────────────────
STANDARD_FILTERS = {
    "indfmt":  "INDL",
    "consol":  "C",
    "popsrc":  "D",
    "datafmt": "STD",
}
