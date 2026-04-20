"""Environment variable-based central settings loader."""

from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


def _get(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f"Required environment variable missing: {key}. Please check your .env file.")
    return value


def _get_optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _get_float(key: str, default: float) -> float:
    return float(os.environ.get(key, str(default)))


def _get_int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


# ── API credentials ───────────────────────────────────────────────────────────
FRED_API_KEY: str = _get("FRED_API_KEY")
# WRDS requires institutional subscription — fundamental scores skipped if absent
WRDS_USERNAME: str = _get_optional("WRDS_USERNAME", "")
WRDS_PASSWORD: str = _get_optional("WRDS_PASSWORD", "")

# ── Price data source ─────────────────────────────────────────────────────────
PRICE_DATA_SOURCE: str = _get_optional("PRICE_DATA_SOURCE", "yfinance")
PRICE_DATA_API_KEY: str = _get_optional("PRICE_DATA_API_KEY", "")

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_DIR: Path = Path(_get_optional("CACHE_DIR", "./data/.cache"))
CACHE_TTL_HOURS_FRED: int = _get_int("CACHE_TTL_HOURS_FRED", 24)
CACHE_TTL_HOURS_WRDS: int = _get_int("CACHE_TTL_HOURS_WRDS", 168)
CACHE_TTL_HOURS_TECHNICAL: int = _get_int("CACHE_TTL_HOURS_TECHNICAL", 4)

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR: Path = Path(_get_optional("OUTPUT_DIR", "./output"))
OUTPUT_FORMATS: list[str] = _get_optional("OUTPUT_FORMAT", "json,html").split(",")

# ── Normalization ─────────────────────────────────────────────────────────────
NORMALIZATION_WINDOW_YEARS: int = _get_int("NORMALIZATION_WINDOW_YEARS", 10)

# ── Signal thresholds ─────────────────────────────────────────────────────────
SIGNAL_THRESHOLD_STRONG_BUY: float = _get_float("SIGNAL_THRESHOLD_STRONG_BUY", 70.0)
SIGNAL_THRESHOLD_BUY: float = _get_float("SIGNAL_THRESHOLD_BUY", 55.0)
SIGNAL_THRESHOLD_NEUTRAL: float = _get_float("SIGNAL_THRESHOLD_NEUTRAL", 45.0)
SIGNAL_THRESHOLD_SELL: float = _get_float("SIGNAL_THRESHOLD_SELL", 30.0)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = _get_optional("LOG_LEVEL", "INFO")
LOG_FORMAT: str = _get_optional("LOG_FORMAT", "text")
