"""Data fetcher base interface and DataResolution enum."""

from abc import ABC, abstractmethod
from enum import Enum

import polars as pl


class DataResolution(str, Enum):
    """Data resolution (bar unit per time horizon)."""
    DAILY   = "daily"    # Short-term: daily bars
    WEEKLY  = "weekly"   # Mid-term:   weekly bars
    MONTHLY = "monthly"  # Long-term:  monthly bars


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(
        self,
        identifiers: list[str],
        start_date: str,
        end_date: str,
    ) -> pl.DataFrame:
        """Returns a Polars DataFrame with a 'date' column + per-indicator columns."""
        ...

    @abstractmethod
    def validate_connection(self) -> bool:
        """Check whether the data source is reachable."""
        ...
