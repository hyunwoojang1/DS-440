"""Technical data snapshot model."""

from dataclasses import dataclass, field


@dataclass
class TechnicalSnapshot:
    ticker: str
    as_of_date: str
    values: dict[str, float] = field(default_factory=dict)
