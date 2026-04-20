"""WRDS Compustat data fetcher (Polars output).

For within-sector z-score-based fundamental scoring:
- comp.funda + comp.company JOIN → includes gsector, tic
- fetch()                    : full market data (population for sector distribution)
- get_ticker_fundamentals()  : latest fundamental values for a specific ticker
- get_sector_latest()        : latest values per company in sector (z-score denominator)
"""

from __future__ import annotations

import warnings

import pandas as pd
import polars as pl

from config.settings import WRDS_USERNAME
from config import wrds_fields as wf
from data.cache.disk_cache import DiskCache
from .base import BaseFetcher

FUND_METRICS = ["pbr", "roe", "fcf_yield", "de_ratio",
                "earnings_yield", "eps_change_rate", "revenue_growth"]


class WRDSFetcher(BaseFetcher):
    def __init__(self, cache: DiskCache | None = None) -> None:
        self._cache = cache
        self._db = None

    def _get_db(self):
        if self._db is None:
            import wrds
            self._db = wrds.Connection(wrds_username=WRDS_USERNAME)
        return self._db

    # ── Public interface ───────────────────────────────────────────────────────

    def fetch(
        self,
        identifiers: list[str],
        start_date: str,
        end_date: str,
    ) -> pl.DataFrame:
        """Fetches full market fundamental data (includes gsector, tic).

        Used as the population for sector z-score computation.
        """
        if not WRDS_USERNAME:
            return pl.DataFrame()

        cache_key = f"wrds_funda_{start_date}_{end_date}"
        if self._cache and (cached := self._cache.get(cache_key)) is not None:
            return cached

        try:
            fields = ", ".join(wf.KEY_FIELDS + wf.COMPANY_FIELDS + wf.FINANCIAL_FIELDS)
            filters = " AND ".join(f"f.{k} = '{v}'" for k, v in wf.STANDARD_FILTERS.items())
            query = f"""
                SELECT {fields}
                FROM {wf.FUNDA_TABLE} f
                LEFT JOIN {wf.COMPANY_TABLE} c ON f.gvkey = c.gvkey
                WHERE {filters}
                  AND f.datadate >= '{start_date}'
                  AND f.datadate <= '{end_date}'
                ORDER BY f.gvkey, f.datadate
            """
            db = self._get_db()
            pd_df = db.raw_sql(query, date_cols=["datadate"])
            # Strip table prefix from column names (f.gvkey → gvkey)
            pd_df.columns = [c.split(".")[-1] for c in pd_df.columns]
            pd_df = _compute_derived(pd_df)

            result = pl.from_pandas(pd_df)
            if self._cache:
                self._cache.set(cache_key, result)
            return result

        except Exception as e:
            warnings.warn(f"WRDS fetch failed — fundamental scores skipped: {e}")
            return pl.DataFrame()

    def get_ticker_fundamentals(
        self,
        ticker: str,
        all_data: pl.DataFrame,
        as_of_date: str,
    ) -> tuple[dict[str, float], str]:
        """Returns the ticker's latest fundamental values and GICS sector code.

        Returns:
            (raw_values, gsector_code)
            raw_values:   indicator name → float dict
            gsector_code: GICS sector code string (e.g., "45")
        """
        if all_data.is_empty():
            return {}, ""

        # Ticker filter + data before as_of_date
        ticker_df = (
            all_data
            .filter(pl.col("tic") == ticker)
            .filter(pl.col("datadate").cast(pl.Utf8) <= as_of_date)
            .sort("datadate")
        )
        if ticker_df.is_empty():
            return {}, ""

        latest = ticker_df.tail(1)
        gsector = str(latest["gsector"][0] or "")

        raw: dict[str, float] = {}
        for metric in FUND_METRICS:
            if metric in latest.columns:
                val = latest[metric][0]
                try:
                    fval = float(val)  # type: ignore[arg-type]
                    import math
                    if not math.isnan(fval) and not math.isinf(fval):
                        raw[metric] = fval
                except (TypeError, ValueError):
                    pass

        return raw, gsector

    def get_sector_latest(
        self,
        gsector: str,
        all_data: pl.DataFrame,
        as_of_date: str,
    ) -> pl.DataFrame:
        """Returns the point-in-time latest values for all companies in the sector (z-score denominator).

        Selects the most recent fiscal year value before as_of_date for each company.
        """
        if all_data.is_empty() or not gsector:
            return pl.DataFrame()

        sector_hist = (
            all_data
            .filter(pl.col("gsector").cast(pl.Utf8) == gsector)
            .filter(pl.col("datadate").cast(pl.Utf8) <= as_of_date)
        )
        if sector_hist.is_empty():
            return pl.DataFrame()

        # Select the most recent observation per company
        sector_latest = (
            sector_hist
            .sort("datadate")
            .group_by("gvkey")
            .agg([pl.last(m) for m in FUND_METRICS if m in sector_hist.columns])
        )
        return sector_latest

    def validate_connection(self) -> bool:
        try:
            self._get_db().raw_sql("SELECT 1")
            return True
        except Exception:
            return False

    # ── Backward compatibility ─────────────────────────────────────────────────
    def aggregate_market(self, df: pl.DataFrame, as_of_date: str) -> dict[str, float]:
        """(Legacy) Returns market median values — replaced by sector z-score approach."""
        if df.is_empty():
            return {}
        pd_df = df.to_pandas()
        pd_df = pd_df[pd_df["datadate"].astype(str) <= as_of_date]
        latest = pd_df.sort_values("datadate").groupby("gvkey").last()
        return {c: float(latest[c].median()) for c in FUND_METRICS if c in latest.columns}


# ── Derived indicator computation (module-level function) ─────────────────────

def _compute_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if {"prcc_f", "ceq", "csho"}.issubset(df.columns):
        book_ps = df["ceq"] / df["csho"].replace(0, float("nan"))
        df["pbr"] = df["prcc_f"] / book_ps.replace(0, float("nan"))

    if {"ni", "ceq"}.issubset(df.columns):
        df["roe"] = df["ni"] / df["ceq"].replace(0, float("nan"))

    if {"oancf", "capx", "mkvalt"}.issubset(df.columns):
        df["fcf_yield"] = (df["oancf"] - df["capx"]) / df["mkvalt"].replace(0, float("nan"))

    if {"dltt", "dlc", "ceq"}.issubset(df.columns):
        df["de_ratio"] = (df["dltt"] + df["dlc"]) / df["ceq"].replace(0, float("nan"))

    if {"epsfx", "prcc_f"}.issubset(df.columns):
        df["earnings_yield"] = df["epsfx"] / df["prcc_f"].replace(0, float("nan"))

    if "epsfx" in df.columns:
        df = df.sort_values(["gvkey", "datadate"])
        df["eps_change_rate"] = df.groupby("gvkey")["epsfx"].pct_change(4)

    if "sale" in df.columns:
        df["revenue_growth"] = df.groupby("gvkey")["sale"].pct_change(4)

    return df
