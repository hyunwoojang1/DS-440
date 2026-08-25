"""Fundamental data snapshot model."""

from dataclasses import dataclass, field


@dataclass
class FundamentalSnapshot:
    as_of_date: str
    universe: str = "SP500"
    values: dict[str, float] = field(default_factory=dict)  # Market median values
    source_dates: dict[str, str] = field(default_factory=dict)
